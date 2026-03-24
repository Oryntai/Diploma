from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.request

from devices.temperature import TemperatureSensor


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Emit deterministic telemetry for one temperature sensor.",
    )
    parser.add_argument(
        "--device-id",
        default="temp-001",
        help="Device identifier included in telemetry payloads.",
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
    return parser.parse_args()


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


def emit_payload(device: TemperatureSensor, ingest_url: str | None = None) -> None:
    payload = device.next_payload()
    print(json.dumps(payload))
    if ingest_url:
        publish_to_ingest(ingest_url, payload)


def main() -> int:
    args = parse_args()
    device = TemperatureSensor(
        device_id=args.device_id,
        mode=args.mode,
        seed=args.seed,
        interval_seconds=args.interval,
        firmware_version=args.firmware_version,
    )

    if args.once:
        try:
            emit_payload(device, ingest_url=args.ingest_url)
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        return 0

    while True:
        try:
            emit_payload(device, ingest_url=args.ingest_url)
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 1
        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
