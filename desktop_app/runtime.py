from __future__ import annotations

import os
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

import httpx


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def find_free_port(start: int = 8000, end: int = 8100) -> int:
    for port in range(start, end + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            probe.settimeout(0.2)
            if probe.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError(f"No free local port found in range {start}-{end}.")


def wait_for_health(base_url: str, timeout_seconds: float = 20.0) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            response = httpx.get(f"{base_url.rstrip('/')}/health", timeout=1.0)
            if response.status_code == 200:
                return True
        except httpx.HTTPError:
            pass
        time.sleep(0.25)
    return False


@dataclass
class BackendRuntime:
    port: int | None = None
    process: subprocess.Popen | None = None
    owns_process: bool = False

    @property
    def base_url(self) -> str:
        if self.port is None:
            raise RuntimeError("Backend runtime has not been started.")
        return f"http://127.0.0.1:{self.port}"

    def start(self) -> str:
        if self.process is not None and self.port is not None:
            return self.base_url

        self.port = find_free_port()
        root = project_root()
        backend_dir = root / "backend"
        env = os.environ.copy()
        env["PYTHONPATH"] = str(backend_dir)

        creationflags = 0
        if os.name == "nt":
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

        self.process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(self.port),
            ],
            cwd=str(backend_dir),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=creationflags,
        )
        self.owns_process = True

        if not wait_for_health(self.base_url):
            self.stop()
            raise RuntimeError("Backend did not become healthy in time.")

        return self.base_url

    def stop(self) -> None:
        if self.process is None or not self.owns_process:
            return
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
        self.process = None
        self.owns_process = False
