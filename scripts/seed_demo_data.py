from __future__ import annotations

import argparse
import json
import urllib.request


def _post(base_url: str, path: str) -> dict:
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}{path}",
        data=b"{}",
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Reset and seed demo data.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--no-reset", action="store_true")
    args = parser.parse_args()

    if not args.no_reset:
        print(json.dumps(_post(args.base_url, "/api/demo/reset"), indent=2))
    print(json.dumps(_post(args.base_url, "/api/demo/seed"), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
