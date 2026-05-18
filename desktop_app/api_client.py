from __future__ import annotations

from time import perf_counter
from typing import Any

import httpx

from .diagnostics import log_event


class ApiClient:
    def __init__(
        self,
        base_url: str,
        timeout: float = 5.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=timeout,
            transport=transport,
        )

    def close(self) -> None:
        self._client.close()

    def health(self) -> dict[str, Any]:
        return self._request("GET", "/health")

    def system_status(self) -> dict[str, Any]:
        return self._request("GET", "/api/system/status")

    def registered_devices(self) -> list[dict[str, Any]]:
        return self._request("GET", "/api/registered-devices")

    def ml_status(self) -> dict[str, Any]:
        return self._request("GET", "/api/ml/status")

    def clear_data(self) -> dict[str, Any]:
        return self._request("POST", "/api/data/clear", timeout=20.0)

    def send_network_sample(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", "/api/network/sample", json=payload, timeout=45.0)

    def run_demo_scenario(self) -> dict[str, Any]:
        return self._request("POST", "/api/demo/scenario", timeout=60.0)

    def run_device_tests(self) -> dict[str, Any]:
        return self._request("POST", "/api/demo/device-tests", timeout=90.0)

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> Any:
        started = perf_counter()
        try:
            response = self._client.request(method, path, json=json, timeout=timeout)
            response.raise_for_status()
            log_event(
                "api_request",
                method=method,
                path=path,
                status=response.status_code,
                ms=int((perf_counter() - started) * 1000),
            )
            return response.json()
        except Exception as exc:
            log_event(
                "api_request_error",
                method=method,
                path=path,
                ms=int((perf_counter() - started) * 1000),
                error=str(exc),
            )
            raise
