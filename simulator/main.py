from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request

from devices import DEVICE_CLASSES


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Emit deterministic telemetry for one temperature sensor.",
    )
    parser.add_argument(
        "--device-type",
        choices=list(DEVICE_CLASSES.keys()),
        default="temperature_sensor",
        help="Type of IoT device to simulate.",
    )
    parser.add_argument(
        "--device-id",
        default=None,
        help="Device identifier (auto-generated from device type if omitted).",
    )
    parser.add_argument(
        "--mode",
        choices=("normal", "abnormal"),
        default="normal",
        help="Behavior mode for the simulated device.",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=5.0,
        help="Seconds between payloads when running continuously.",
    )
    parser.add_argument(
        "--firmware-version",
        default="1.0.2",
        help="Firmware version included in telemetry payloads.",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=0,
        help="Deterministic random seed for repeatable payload values.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Emit one payload and exit.",
    )
    parser.add_argument(
        "--ingest-url",
        default=None,
        help=(
            "Optional backend ingest endpoint, for example "
            "http://127.0.0.1:8000/api/ingest/telemetry"
        ),
    )
    parser.add_argument(
        "--mqtt-host",
        default=None,
        help="MQTT broker host (e.g. 127.0.0.1). Enables MQTT publish.",
    )
    parser.add_argument(
        "--mqtt-port",
        type=int,
        default=1883,
        help="MQTT broker port (default 1883).",
    )
    return parser.parse_args()


def publish_to_mqtt(
    host: str, port: int, payload: dict[str, str | int | float]
) -> None:
    try:
        import paho.mqtt.client as mqtt
    except ImportError:
        raise RuntimeError("paho-mqtt is required for MQTT publish: pip install paho-mqtt")

    device_type = payload.get("device_type", "unknown")
    device_id = payload.get("device_id", "unknown")
    topic = f"iot/devices/{device_type}/{device_id}/telemetry"

    client = mqtt.Client()
    client.connect(host, port, keepalive=10)
    client.publish(topic, json.dumps(payload), qos=1)
    client.disconnect()


def publish_to_ingest(ingest_url: str, payload: dict[str, str | int | float]) -> None:
    request = urllib.request.Request(
        ingest_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=5):
            return
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Failed to send telemetry to ingest endpoint: {ingest_url}"
        ) from exc


def emit_payload(
    device: object,
    ingest_url: str | None = None,
    mqtt_host: str | None = None,
    mqtt_port: int = 1883,
) -> None:
    payload = device.next_payload()
    print(json.dumps(payload))
    if ingest_url:
        publish_to_ingest(ingest_url, payload)
    if mqtt_host:
        publish_to_mqtt(mqtt_host, mqtt_port, payload)


def main() -> int:
    args = parse_args()
    device_id = args.device_id or f"{args.device_type.replace('_', '-')}-001"
    device_cls = DEVICE_CLASSES[args.device_type]
    device = device_cls(
        device_id=device_id,
        mode=args.mode,
        seed=args.seed,
        interval_seconds=args.interval,
        firmware_version=args.firmware_version,
    )

    emit_kwargs = {
        "ingest_url": args.ingest_url,
        "mqtt_host": args.mqtt_host,
        "mqtt_port": args.mqtt_port,
    }

    if args.once:
        try:
            emit_payload(device, **emit_kwargs)
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        return 0

    while True:
        try:
            emit_payload(device, **emit_kwargs)
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
