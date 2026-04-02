"""
IoT Security Simulator — Desktop GUI
Sends telemetry & attack payloads to the FastAPI backend.
"""
from __future__ import annotations

import json
import threading
import time
import tkinter as tk
from datetime import UTC, datetime
from tkinter import ttk
from urllib.error import URLError
from urllib.request import Request, urlopen

# ── colours ──────────────────────────────────────────────────────────
BG        = "#1e1e2e"
BG_CARD   = "#272739"
BG_INPUT  = "#2e2e42"
FG        = "#cdd6f4"
FG_DIM    = "#7f849c"
ACCENT    = "#89b4fa"
GREEN     = "#a6e3a1"
RED       = "#f38ba8"
YELLOW    = "#f9e2af"
ORANGE    = "#fab387"

BACKEND   = "http://127.0.0.1:8000"
INGEST    = f"{BACKEND}/api/ingest/telemetry"
ML_PREDICT = f"{BACKEND}/api/ml/predict"

# ── helpers ──────────────────────────────────────────────────────────

def _post(url: str, body: dict) -> dict:
    req = Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(req, timeout=5) as resp:
        return json.loads(resp.read())


def _get(url: str) -> dict:
    req = Request(url, method="GET")
    with urlopen(req, timeout=3) as resp:
        return json.loads(resp.read())


# ── main window ──────────────────────────────────────────────────────

class SimulatorApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("IoT Security Simulator")
        self.configure(bg=BG)
        self.geometry("820x720")
        self.resizable(False, False)

        # ── header ───────────────────────────────────────────────────
        header = tk.Frame(self, bg=BG)
        header.pack(fill="x", padx=20, pady=(18, 4))
        tk.Label(header, text="IoT Security Simulator", font=("Segoe UI", 18, "bold"), bg=BG, fg=FG).pack(side="left")
        self._status_dot = tk.Label(header, text="\u25cf", font=("Segoe UI", 13), bg=BG, fg=FG_DIM)
        self._status_dot.pack(side="right")
        self._status_lbl = tk.Label(header, text="checking…", font=("Segoe UI", 10), bg=BG, fg=FG_DIM)
        self._status_lbl.pack(side="right", padx=(0, 4))

        # ── telemetry card ───────────────────────────────────────────
        self._build_telemetry_card()

        # ── ML attacks card ──────────────────────────────────────────
        self._build_ml_card()

        # ── rule attacks card ────────────────────────────────────────
        self._build_rule_card()

        # ── log ──────────────────────────────────────────────────────
        self._build_log()

        # ── kick off health check ────────────────────────────────────
        self._check_backend()

    # ────────────────────────── telemetry ─────────────────────────────
    def _build_telemetry_card(self) -> None:
        card = tk.LabelFrame(self, text="  Normal Telemetry  ", font=("Segoe UI", 11, "bold"),
                             bg=BG_CARD, fg=ACCENT, bd=0, highlightthickness=1,
                             highlightcolor=ACCENT, highlightbackground=BG_INPUT,
                             padx=14, pady=10)
        card.pack(fill="x", padx=20, pady=(10, 4))

        row = tk.Frame(card, bg=BG_CARD)
        row.pack(fill="x")

        # device type
        tk.Label(row, text="Device", font=("Segoe UI", 10), bg=BG_CARD, fg=FG).pack(side="left")
        self._device_type = ttk.Combobox(row, values=["temperature_sensor", "smart_plug", "ip_camera", "smart_door_lock"],
                                         state="readonly", width=16)
        self._device_type.set("temperature_sensor")
        self._device_type.pack(side="left", padx=(6, 16))

        # temperature
        tk.Label(row, text="Temp °C", font=("Segoe UI", 10), bg=BG_CARD, fg=FG).pack(side="left")
        self._temp_var = tk.StringVar(value="23.5")
        tk.Entry(row, textvariable=self._temp_var, width=6, bg=BG_INPUT, fg=FG,
                 insertbackground=FG, bd=0, font=("Segoe UI", 10)).pack(side="left", padx=(6, 16))

        # battery
        tk.Label(row, text="Battery %", font=("Segoe UI", 10), bg=BG_CARD, fg=FG).pack(side="left")
        self._batt_var = tk.StringVar(value="85")
        tk.Entry(row, textvariable=self._batt_var, width=4, bg=BG_INPUT, fg=FG,
                 insertbackground=FG, bd=0, font=("Segoe UI", 10)).pack(side="left", padx=(6, 16))

        btn = tk.Button(row, text="Send", font=("Segoe UI", 10, "bold"), bg=GREEN, fg="#1e1e2e",
                        activebackground="#81d491", bd=0, padx=14, pady=2, cursor="hand2",
                        command=self._send_telemetry)
        btn.pack(side="right")

    # ────────────────────────── ML attacks ────────────────────────────
    def _build_ml_card(self) -> None:
        card = tk.LabelFrame(self, text="  ML-Detected Attacks  ", font=("Segoe UI", 11, "bold"),
                             bg=BG_CARD, fg=RED, bd=0, highlightthickness=1,
                             highlightcolor=RED, highlightbackground=BG_INPUT,
                             padx=14, pady=10)
        card.pack(fill="x", padx=20, pady=(8, 4))

        attacks = [
            ("SYN Flood",     "syn_flood",    "Floods SYN packets — high rate, no ACKs"),
            ("Port Scan",     "port_scan",    "Mass RST/SYN flags — probing open ports"),
            ("ARP Spoofing",  "arp_spoofing", "Forged ARP traffic — MITM attempt"),
            ("DNS Tunnel",    "dns_tunnel",   "Oversized DNS/UDP payloads — data exfil"),
            ("DDoS",          "DDoS",         "Extreme packet rate from many sources"),
        ]

        for i, (label, key, hint) in enumerate(attacks):
            row = tk.Frame(card, bg=BG_CARD)
            row.pack(fill="x", pady=2)
            tk.Label(row, text=f"\u26a0  {label}", font=("Segoe UI", 10), bg=BG_CARD, fg=ORANGE, width=16, anchor="w").pack(side="left")
            tk.Label(row, text=hint, font=("Segoe UI", 9), bg=BG_CARD, fg=FG_DIM).pack(side="left", padx=(4, 0))
            btn = tk.Button(row, text="Attack", font=("Segoe UI", 9, "bold"), bg=RED, fg="#1e1e2e",
                            activebackground="#e06080", bd=0, padx=10, cursor="hand2",
                            command=lambda k=key, l=label: self._send_ml_attack(k, l))
            btn.pack(side="right")

    # ────────────────────── rule-based attacks ────────────────────────
    def _build_rule_card(self) -> None:
        card = tk.LabelFrame(self, text="  Rule-Based Scenarios  ", font=("Segoe UI", 11, "bold"),
                             bg=BG_CARD, fg=YELLOW, bd=0, highlightthickness=1,
                             highlightcolor=YELLOW, highlightbackground=BG_INPUT,
                             padx=14, pady=10)
        card.pack(fill="x", padx=20, pady=(8, 4))

        row = tk.Frame(card, bg=BG_CARD)
        row.pack(fill="x")

        scenarios = [
            ("Impossible Value", self._attack_impossible),
            ("Message Flood",    self._attack_flood),
            ("Firmware Swap",    self._attack_firmware),
        ]
        for label, cmd in scenarios:
            btn = tk.Button(row, text=label, font=("Segoe UI", 9, "bold"), bg=YELLOW, fg="#1e1e2e",
                            activebackground="#e0cc70", bd=0, padx=12, pady=3, cursor="hand2", command=cmd)
            btn.pack(side="left", padx=(0, 8))

    # ────────────────────────── log area ──────────────────────────────
    def _build_log(self) -> None:
        lbl = tk.Label(self, text="Log", font=("Segoe UI", 10, "bold"), bg=BG, fg=FG_DIM, anchor="w")
        lbl.pack(fill="x", padx=22, pady=(10, 0))
        self._log = tk.Text(self, height=10, bg=BG_INPUT, fg=FG, font=("Consolas", 9),
                            bd=0, insertbackground=FG, wrap="word", state="disabled")
        self._log.pack(fill="both", expand=True, padx=20, pady=(2, 16))
        self._log.tag_configure("ok",   foreground=GREEN)
        self._log.tag_configure("err",  foreground=RED)
        self._log.tag_configure("warn", foreground=YELLOW)
        self._log.tag_configure("info", foreground=ACCENT)

    # ────────────────────────── logging ───────────────────────────────
    def _log_msg(self, text: str, tag: str = "info") -> None:
        ts = datetime.now().strftime("%H:%M:%S")
        self._log.configure(state="normal")
        self._log.insert("end", f"[{ts}] {text}\n", tag)
        self._log.see("end")
        self._log.configure(state="disabled")

    # ────────────────────── backend health ────────────────────────────
    def _check_backend(self) -> None:
        def _ping() -> None:
            try:
                _get(f"{BACKEND}/health")
                self._status_lbl.configure(text="Backend online", fg=GREEN)
                self._status_dot.configure(fg=GREEN)
            except Exception:
                self._status_lbl.configure(text="Backend offline", fg=RED)
                self._status_dot.configure(fg=RED)
            self.after(5000, self._check_backend)
        threading.Thread(target=_ping, daemon=True).start()

    # ────────────────────── send telemetry ────────────────────────────
    def _send_telemetry(self) -> None:
        def _work() -> None:
            try:
                temp = float(self._temp_var.get())
            except ValueError:
                self._log_msg("Invalid temperature value", "err")
                return
            try:
                batt = int(self._batt_var.get())
            except ValueError:
                self._log_msg("Invalid battery value", "err")
                return

            dev_type = self._device_type.get()
            device_id = f"{dev_type.replace('_', '-')}-gui-001"
            payload = {
                "device_id": device_id,
                "device_type": dev_type,
                "timestamp": datetime.now(UTC).isoformat(),
                "temperature": temp,
                "battery": batt,
                "firmware_version": "1.0.2",
                "mode": "normal",
            }
            try:
                resp = _post(INGEST, payload)
                alerts = resp.get("alerts_created", 0)
                if alerts > 0:
                    self._log_msg(f"Sent {dev_type} telemetry  \u2192  {alerts} alert(s) triggered!", "warn")
                else:
                    self._log_msg(f"Sent {dev_type} telemetry  \u2192  OK, no alerts", "ok")
            except URLError:
                self._log_msg("Failed to connect to backend", "err")
            except Exception as e:
                self._log_msg(f"Error: {e}", "err")

        threading.Thread(target=_work, daemon=True).start()

    # ────────────────────── ML attack ─────────────────────────────────
    def _send_ml_attack(self, attack_type: str, label: str) -> None:
        def _work() -> None:
            self._log_msg(f"Launching ML attack: {label}…", "info")

            # Step 1 — send abnormal telemetry so the ingest pipeline runs ML
            device_id = f"ml-attack-{attack_type.replace('_', '-')}"
            payload = {
                "device_id": device_id,
                "device_type": "ip_camera",
                "timestamp": datetime.now(UTC).isoformat(),
                "fps": 2,
                "resolution": "360p",
                "stream_active": False,
                "bandwidth_kbps": 13000.0,
                "battery": 5,
                "firmware_version": "1.0.2",
                "mode": "abnormal",
            }
            try:
                resp = _post(INGEST, payload)
                alerts = resp.get("alerts_created", 0)
                if alerts > 0:
                    self._log_msg(f"\u2714 {label}: {alerts} alert(s) created  [device: {device_id}]", "warn")
                else:
                    self._log_msg(f"\u2714 {label}: telemetry sent, 0 alerts (ML may not have flagged)", "ok")
            except URLError:
                self._log_msg("Backend unreachable", "err")
                return
            except Exception as e:
                self._log_msg(f"Error: {e}", "err")
                return

            # Step 2 — also hit /api/ml/predict directly so the user sees raw scores
            try:
                from traffic_features_gen import generate_attack_features
                features = generate_attack_features(attack_type)
                result = _post(ML_PREDICT, {"features": features})
                pred = result.get("prediction", 0)
                thresh = result.get("threshold", 0)
                lbl = result.get("label", "?")
                risk = result.get("risk_level", "?")
                tag = "warn" if lbl == "anomaly" else "ok"
                self._log_msg(
                    f"  ML predict \u2192 error={pred:.6f}  threshold={thresh:.6f}  "
                    f"label={lbl}  risk={risk}",
                    tag,
                )
            except ImportError:
                pass  # traffic_features_gen not available, skip direct predict
            except Exception as e:
                self._log_msg(f"  ML predict call failed: {e}", "err")

        threading.Thread(target=_work, daemon=True).start()

    # ──────────────────── rule-based attacks ──────────────────────────
    def _attack_impossible(self) -> None:
        def _work() -> None:
            self._log_msg("Sending impossible temperature (500 °C)…", "info")
            payload = {
                "device_id": "temp-gui-impossible",
                "device_type": "temperature_sensor",
                "timestamp": datetime.now(UTC).isoformat(),
                "temperature": 500.0,
                "battery": 75,
                "firmware_version": "1.0.2",
                "mode": "normal",
            }
            try:
                resp = _post(INGEST, payload)
                self._log_msg(f"\u2714 Impossible value: {resp.get('alerts_created', 0)} alert(s)", "warn")
            except Exception as e:
                self._log_msg(f"Error: {e}", "err")
        threading.Thread(target=_work, daemon=True).start()

    def _attack_flood(self) -> None:
        def _work() -> None:
            count = 25
            self._log_msg(f"Flooding {count} messages…", "info")
            for i in range(count):
                payload = {
                    "device_id": "flood-gui-sensor",
                    "device_type": "temperature_sensor",
                    "timestamp": datetime.now(UTC).isoformat(),
                    "temperature": 22.0 + (i % 5) * 0.1,
                    "battery": 80,
                    "firmware_version": "1.0.2",
                    "mode": "normal",
                }
                try:
                    _post(INGEST, payload)
                except Exception:
                    pass
                time.sleep(0.04)
            self._log_msg(f"\u2714 Flood complete: {count} messages sent", "warn")
        threading.Thread(target=_work, daemon=True).start()

    def _attack_firmware(self) -> None:
        def _work() -> None:
            self._log_msg("Sending firmware mismatch…", "info")
            base = {
                "device_id": "lock-gui-firmware",
                "device_type": "smart_door_lock",
                "timestamp": datetime.now(UTC).isoformat(),
                "lock_state": "locked",
                "access_attempts": 0,
                "battery": 95,
                "firmware_version": "1.0.2",
                "mode": "normal",
            }
            try:
                _post(INGEST, base)
                base["firmware_version"] = "9.9.9-hacked"
                base["timestamp"] = datetime.now(UTC).isoformat()
                resp = _post(INGEST, base)
                self._log_msg(f"\u2714 Firmware swap: {resp.get('alerts_created', 0)} alert(s)", "warn")
            except Exception as e:
                self._log_msg(f"Error: {e}", "err")
        threading.Thread(target=_work, daemon=True).start()


if __name__ == "__main__":
    app = SimulatorApp()
    app.mainloop()
