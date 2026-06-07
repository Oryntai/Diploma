from __future__ import annotations

import json
import threading
import tkinter as tk
import webbrowser
from tkinter import ttk
from typing import Any, Callable

from .api_client import FastApiSimulatorClient, SimulatorApiError
from .presets import (
    DEVICE_TYPES,
    PRESETS,
    PROTOCOLS,
    DeviceTrafficStream,
    build_custom_network_sample_for_type,
    build_network_sample_for_type,
    build_random_network_sample_for_type,
)

DEFAULT_BACKEND_URL = "http://127.0.0.1:8000"


class DesktopSimulator(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("IoT Device Simulator")
        self.geometry("980x680")
        self.minsize(820, 560)

        self.backend_url = tk.StringVar(value=DEFAULT_BACKEND_URL)
        self.device_type = tk.StringVar(value=next(iter(DEVICE_TYPES)))
        self.preset_name = tk.StringVar(value="normal")
        self.stream_interval_seconds = tk.StringVar(value="2.0")
        self.status_text = tk.StringVar(value="Ready")
        self.custom_values: dict[str, tk.StringVar] = {
            "protocol": tk.StringVar(value="HTTP"),
            "bytes_per_second": tk.StringVar(value="512.0"),
            "packets_per_second": tk.StringVar(value="0.2"),
            "connection_count": tk.StringVar(value="1"),
            "latency_ms": tk.StringVar(value="12.0"),
            "packet_loss_percent": tk.StringVar(value="0.0"),
        }
        self.random_stream_running = False
        self.traffic_stream = DeviceTrafficStream(self.device_type.get())

        self._build_layout()
        self._load_preset_into_custom()

    def _build_layout(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(3, weight=1)

        top = ttk.Frame(self, padding=12)
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(1, weight=1)

        ttk.Label(top, text="FastAPI URL").grid(row=0, column=0, sticky="w")
        ttk.Entry(top, textvariable=self.backend_url).grid(row=0, column=1, sticky="ew", padx=8)
        ttk.Button(top, text="Health", command=self._check_health).grid(row=0, column=2, padx=4)
        ttk.Button(top, text="Open Dashboard", command=self._open_dashboard).grid(row=0, column=3, padx=4)

        controls = ttk.Frame(self, padding=(12, 0, 12, 12))
        controls.grid(row=1, column=0, sticky="ew")
        controls.columnconfigure(1, weight=1)
        controls.columnconfigure(3, weight=1)

        ttk.Label(controls, text="Device Type").grid(row=0, column=0, sticky="w")
        device_box = ttk.Combobox(
            controls,
            textvariable=self.device_type,
            values=list(DEVICE_TYPES),
            state="readonly",
        )
        device_box.grid(row=0, column=1, sticky="ew", padx=8)
        device_box.bind("<<ComboboxSelected>>", lambda _event: self._reset_device_stream())

        ttk.Label(controls, text="Preset").grid(row=0, column=2, sticky="w")
        preset_box = ttk.Combobox(
            controls,
            textvariable=self.preset_name,
            values=list(PRESETS),
            state="readonly",
        )
        preset_box.grid(row=0, column=3, sticky="ew", padx=8)
        preset_box.bind("<<ComboboxSelected>>", lambda _event: self._load_preset_into_custom())

        ttk.Button(controls, text="Send Preset", command=self._send_preset_sample).grid(row=0, column=4, padx=4)
        ttk.Button(controls, text="Send Random Sample", command=self._send_random_sample).grid(row=0, column=5, padx=4)

        ttk.Label(controls, text="Interval, sec").grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(controls, textvariable=self.stream_interval_seconds, width=8).grid(
            row=1,
            column=1,
            sticky="w",
            padx=8,
            pady=(8, 0),
        )
        ttk.Button(controls, text="Start Device Stream", command=self._start_random_stream).grid(
            row=1,
            column=2,
            padx=4,
            pady=(8, 0),
        )
        ttk.Button(controls, text="Stop", command=self._stop_random_stream).grid(
            row=1,
            column=3,
            sticky="w",
            padx=4,
            pady=(8, 0),
        )
        ttk.Button(controls, text="Run Mixed Scenario", command=self._run_backend_scenario).grid(
            row=1,
            column=4,
            columnspan=2,
            sticky="e",
            padx=4,
            pady=(8, 0),
        )

        custom = ttk.LabelFrame(self, text="Custom Sample", padding=(12, 6, 12, 12))
        custom.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 12))
        for col in range(7):
            custom.columnconfigure(col, weight=1)

        field_specs = [
            ("Protocol", "protocol", 9),
            ("Bytes/s", "bytes_per_second", 12),
            ("Packets/s", "packets_per_second", 12),
            ("Connections", "connection_count", 10),
            ("Latency ms", "latency_ms", 10),
            ("Loss %", "packet_loss_percent", 10),
        ]
        for col, (label, key, width) in enumerate(field_specs):
            ttk.Label(custom, text=label).grid(row=0, column=col, sticky="w", padx=(0, 8))
            if key == "protocol":
                protocol_box = ttk.Combobox(
                    custom,
                    textvariable=self.custom_values[key],
                    values=list(PROTOCOLS),
                    state="readonly",
                    width=width,
                )
                protocol_box.grid(row=1, column=col, sticky="ew", padx=(0, 8))
                protocol_box.bind(
                    "<<ComboboxSelected>>",
                    lambda _event: self._refresh_payload_preview(),
                )
            else:
                entry = ttk.Entry(custom, textvariable=self.custom_values[key], width=width)
                entry.grid(row=1, column=col, sticky="ew", padx=(0, 8))
                entry.bind("<FocusOut>", lambda _event: self._refresh_payload_preview())
                entry.bind("<Return>", lambda _event: self._refresh_payload_preview())

        ttk.Button(custom, text="Send Custom", command=self._send_custom_sample).grid(
            row=1,
            column=6,
            sticky="ew",
        )

        panes = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        panes.grid(row=3, column=0, sticky="nsew", padx=12, pady=(0, 12))

        payload_frame = ttk.LabelFrame(panes, text="Payload")
        response_frame = ttk.LabelFrame(panes, text="Backend Response")
        panes.add(payload_frame, weight=1)
        panes.add(response_frame, weight=1)

        payload_frame.rowconfigure(0, weight=1)
        payload_frame.columnconfigure(0, weight=1)
        response_frame.rowconfigure(0, weight=1)
        response_frame.columnconfigure(0, weight=1)

        self.payload_view = tk.Text(payload_frame, wrap="word", height=18)
        self.payload_view.grid(row=0, column=0, sticky="nsew")
        self.response_view = tk.Text(response_frame, wrap="word", height=18)
        self.response_view.grid(row=0, column=0, sticky="nsew")

        status = ttk.Frame(self, padding=(12, 0, 12, 12))
        status.grid(row=4, column=0, sticky="ew")
        status.columnconfigure(0, weight=1)
        ttk.Label(status, textvariable=self.status_text).grid(row=0, column=0, sticky="w")

    def _client(self) -> FastApiSimulatorClient:
        return FastApiSimulatorClient(self.backend_url.get().strip() or DEFAULT_BACKEND_URL)

    def _refresh_payload_preview(self) -> None:
        try:
            payload = self._build_custom_payload()
            self._write_text(self.payload_view, payload)
        except ValueError as exc:
            self._write_text(self.payload_view, {"error": str(exc)})

    def _send_preset_sample(self) -> None:
        try:
            payload = build_network_sample_for_type(
                self.device_type.get(),
                self.preset_name.get(),
            )
        except ValueError as exc:
            self._set_response({"error": str(exc)})
            return

        self._write_text(self.payload_view, payload)
        self._run_background(
            "Sending sample...",
            lambda: self._client().send_network_sample(payload),
            self._set_response,
        )

    def _send_custom_sample(self) -> None:
        try:
            payload = self._build_custom_payload()
            self._write_text(self.payload_view, payload)
        except ValueError as exc:
            self._set_response({"error": str(exc)})
            return

        self._run_background(
            "Sending custom sample...",
            lambda: self._client().send_network_sample(payload),
            self._set_response,
        )

    def _send_random_sample(self, *, schedule_next: bool = False) -> None:
        try:
            if schedule_next:
                payload = self.traffic_stream.next_sample()
            else:
                payload = build_random_network_sample_for_type(self.device_type.get())
        except ValueError as exc:
            self._set_response({"error": str(exc)})
            return

        self._load_payload_into_custom(payload)
        self._write_text(self.payload_view, payload)
        self._run_background(
            "Sending random sample...",
            lambda: self._client().send_network_sample(payload),
            lambda result: self._handle_random_response(result, schedule_next),
        )

    def _start_random_stream(self) -> None:
        if self.random_stream_running:
            self.status_text.set("Device stream is already running")
            return
        self.traffic_stream = DeviceTrafficStream(self.device_type.get())
        self.random_stream_running = True
        self._send_random_sample(schedule_next=True)

    def _stop_random_stream(self) -> None:
        self.random_stream_running = False
        self.status_text.set("Device stream stopped")

    def _check_health(self) -> None:
        self._run_background(
            "Checking backend...",
            lambda: self._client().health(),
            self._set_response,
        )

    def _run_backend_scenario(self) -> None:
        self._run_background(
            "Running mixed demo scenario...",
            lambda: self._client().run_demo_scenario(),
            self._set_response,
        )

    def _open_dashboard(self) -> None:
        webbrowser.open(self.backend_url.get().strip() or DEFAULT_BACKEND_URL)

    def _load_preset_into_custom(self) -> None:
        try:
            preset = PRESETS[self.preset_name.get()]
        except KeyError:
            self._refresh_payload_preview()
            return
        self._load_payload_into_custom(preset)
        self._refresh_payload_preview()

    def _reset_device_stream(self) -> None:
        self.traffic_stream = DeviceTrafficStream(self.device_type.get())
        self._refresh_payload_preview()

    def _load_payload_into_custom(self, payload: dict[str, Any]) -> None:
        for key, variable in self.custom_values.items():
            if key in payload:
                variable.set(str(payload[key]))

    def _build_custom_payload(self) -> dict[str, Any]:
        return build_custom_network_sample_for_type(
            self.device_type.get(),
            {key: variable.get() for key, variable in self.custom_values.items()},
        )

    def _handle_random_response(self, payload: dict[str, Any], schedule_next: bool) -> None:
        self._set_response(payload)
        if schedule_next and self.random_stream_running:
            self.after(
                self._stream_interval_ms(),
                lambda: self._send_random_sample(schedule_next=True),
            )

    def _stream_interval_ms(self) -> int:
        try:
            seconds = float(self.stream_interval_seconds.get())
        except ValueError:
            seconds = 2.0
            self.stream_interval_seconds.set("2.0")
        seconds = min(max(seconds, 0.5), 60.0)
        return int(seconds * 1000)

    def _run_background(
        self,
        status: str,
        operation: Callable[[], dict[str, Any]],
        on_success: Callable[[dict[str, Any]], None],
    ) -> None:
        self.status_text.set(status)

        def worker() -> None:
            try:
                result = operation()
            except SimulatorApiError as exc:
                self.after(0, lambda: self._set_response({"error": str(exc)}))
                return
            self.after(0, lambda: on_success(result))

        threading.Thread(target=worker, daemon=True).start()

    def _set_response(self, payload: dict[str, Any]) -> None:
        self._write_text(self.response_view, payload)
        if "error" in payload:
            self.status_text.set("Error")
            return
        alerts = payload.get("alerts")
        if isinstance(alerts, list):
            self.status_text.set(f"Accepted: {len(alerts)} alerts returned")
        else:
            self.status_text.set("Completed")

    @staticmethod
    def _write_text(widget: tk.Text, payload: dict[str, Any]) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, json.dumps(payload, indent=2, ensure_ascii=False))
        widget.configure(state="disabled")


def main() -> None:
    app = DesktopSimulator()
    app.mainloop()


if __name__ == "__main__":
    main()
