from __future__ import annotations

import argparse
import json
import time

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
    return parser.parse_args()


def emit_payload(device: TemperatureSensor) -> None:
    payload = device.next_payload()
    print(json.dumps(payload))


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
        emit_payload(device)
        return 0

    while True:
        emit_payload(device)
        time.sleep(args.interval)


if __name__ == "__main__":
    raise SystemExit(main())
