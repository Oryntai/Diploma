from __future__ import annotations

import json
import urllib.error
import urllib.request
from typing import Any


class SimulatorApiError(RuntimeError):
    pass


def build_url(base_url: str, path: str) -> str:
    return f"{base_url.rstrip('/')}/{path.lstrip('/')}"


class FastApiSimulatorClient:
    def __init__(self, base_url: str, timeout: float = 10.0) -> None:
        self.base_url = base_url
        self.timeout = timeout

    def health(self) -> dict[str, Any]:
        return self._request_json("GET", "/health")

    def send_network_sample(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request_json("POST", "/api/network/sample", payload)

    def run_demo_scenario(self) -> dict[str, Any]:
        return self._request_json("POST", "/api/demo/scenario")

    def _request_json(
        self,
        method: str,
        path: str,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")

        request = urllib.request.Request(
            build_url(self.base_url, path),
            data=data,
            headers={"Content-Type": "application/json"},
            method=method,
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise SimulatorApiError(f"HTTP {exc.code}: {body}") from exc
        except urllib.error.URLError as exc:
            raise SimulatorApiError(f"Backend is not reachable: {exc}") from exc

        try:
            decoded = json.loads(body)
        except json.JSONDecodeError as exc:
            raise SimulatorApiError(f"Backend returned non-JSON response: {body}") from exc
        if not isinstance(decoded, dict):
            raise SimulatorApiError("Backend returned JSON that is not an object.")
        return decoded

