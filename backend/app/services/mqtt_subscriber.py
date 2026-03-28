"""MQTT subscriber that listens to IoT telemetry topics and ingests into the backend.

Connects to a Mosquitto broker, subscribes to ``iot/devices/#``, parses
incoming JSON payloads and routes them through the same ingest pipeline
as the HTTP ``POST /api/ingest/telemetry`` endpoint.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import threading
from datetime import UTC, datetime

logger = logging.getLogger("mqtt_subscriber")

MQTT_HOST = os.getenv("MQTT_HOST", "127.0.0.1")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "iot/devices/#")
MQTT_ENABLED = os.getenv("MQTT_ENABLED", "true").lower() in ("1", "true", "yes")


def _try_import_paho():
    """Import paho-mqtt; return None if not installed."""
    try:
        import paho.mqtt.client as mqtt
        return mqtt
    except ImportError:
        return None


class MQTTSubscriber:
    """Background MQTT listener that forwards messages to the ingest pipeline."""

    def __init__(self, ingest_callback):
        """
        Args:
            ingest_callback: callable(payload_dict) that processes a telemetry
                payload dict the same way as the HTTP ingest route.
        """
        self._ingest = ingest_callback
        self._client = None
        self._thread: threading.Thread | None = None

    def start(self) -> bool:
        """Start the MQTT subscriber in a background thread.

        Returns True if started, False if MQTT is disabled or paho is missing.
        """
        if not MQTT_ENABLED:
            logger.info("MQTT subscriber disabled (MQTT_ENABLED=%s)", os.getenv("MQTT_ENABLED"))
            return False

        mqtt = _try_import_paho()
        if mqtt is None:
            logger.warning("paho-mqtt not installed — MQTT subscriber skipped")
            return False

        def on_connect(client, userdata, flags, rc, *args):
            if rc == 0:
                logger.info("MQTT connected to %s:%s", MQTT_HOST, MQTT_PORT)
                client.subscribe(MQTT_TOPIC)
                logger.info("MQTT subscribed to '%s'", MQTT_TOPIC)
            else:
                logger.error("MQTT connection failed, rc=%s", rc)

        def on_message(client, userdata, msg):
            try:
                raw = msg.payload.decode("utf-8")
                data = json.loads(raw)
            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                logger.warning("MQTT bad payload on %s: %s", msg.topic, exc)
                return

            if "device_id" not in data or "device_type" not in data:
                logger.warning("MQTT payload missing required fields on %s", msg.topic)
                return

            if "timestamp" not in data:
                data["timestamp"] = datetime.now(UTC).isoformat()

            data["topic"] = msg.topic

            try:
                self._ingest(data)
                logger.debug("MQTT ingested %s from %s", data.get("device_id"), msg.topic)
            except Exception:
                logger.exception("MQTT ingest error for topic %s", msg.topic)

        try:
            self._client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        except (AttributeError, TypeError):
            self._client = mqtt.Client()

        self._client.on_connect = on_connect
        self._client.on_message = on_message

        def _run():
            try:
                self._client.connect(MQTT_HOST, MQTT_PORT, keepalive=60)
                self._client.loop_forever()
            except Exception:
                logger.exception("MQTT loop crashed")

        self._thread = threading.Thread(target=_run, daemon=True, name="mqtt-subscriber")
        self._thread.start()
        logger.info("MQTT subscriber thread started")
        return True

    def stop(self) -> None:
        if self._client is not None:
            self._client.disconnect()
            logger.info("MQTT subscriber disconnected")
