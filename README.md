# IoT Security Monitoring

Prototype of an intelligent monitoring platform for Internet of Things devices.
The project is built for the diploma topic: **Creation of an intelligent system
for monitoring the security of IoT devices**.

The core idea is a hybrid security monitor. Predictable problems are handled by
deterministic checks and scenario logic, while unknown or complex traffic
patterns are evaluated by a machine learning anomaly detector.

```text
registered IoT device
  -> desktop device simulator or demo endpoint
  -> simulated network sample
  -> FastAPI backend
  -> deterministic device identity checks
  -> CICIoT2023 feature adapter
  -> PyTorch autoencoder
  -> alert and risk scoring
  -> web dashboard and report
```

## Project Annotation

IoT deployments usually contain devices that run continuously, communicate with
external services, and cannot be reliably watched by manual administration or
hand-written rules alone. This MVP demonstrates a local monitoring platform that
combines deterministic checks with reconstruction-based anomaly detection.

The prototype uses a FastAPI backend, SQLite device registry, simulated IoT
traffic, a CICIoT2023-aligned feature adapter, a PyTorch autoencoder, alert/risk
scoring, and a server-rendered dashboard. The autoencoder consumes 46
flow-based network features and marks traffic as abnormal when reconstruction
error exceeds the validation threshold.

The experimental part uses CICIoT2023 as the primary dataset. The autoencoder
was trained for 50 epochs and compared with an Isolation Forest baseline. Final
reported results:

| Metric | Value |
| --- | ---: |
| Precision | 0.9988 |
| Recall | 0.9864 |
| F1-score | 0.9925 |

Current boundary: runtime validation is based on simulated telemetry. Physical
hardware validation, especially with the Xiaomi Mi Robot Vacuum-Mop P, remains
future work.

## Current MVP

- FastAPI web application with JSON API endpoints and Jinja2 dashboard pages.
- Web dashboard for overview, devices, device details, alerts, scan demo, and
  text report export.
- Lightweight desktop device simulator that sends preset network samples to
  the FastAPI backend.
- Static SQLite registry with five simulated IoT devices.
- Deterministic rule engine for device identity and metadata checks.
- CICIoT2023 feature adapter that maps simplified samples into 46 ML features.
- PyTorch autoencoder anomaly detection using reconstruction error and a
  validation threshold.
- Network anomaly alerts come from the ML autoencoder; deterministic device
  checks are reported as rule-engine alerts.
- Runtime network sample evidence in `logs/network_samples.log`.

Old monolithic desktop code has been removed. The supported desktop component is
now a small device simulator; the main operator interface is the FastAPI web
dashboard.

## Quick Start

```powershell
.\scripts\run_local.ps1
```

Manual launch:

```powershell
python -m pip install -r backend\requirements.txt
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open:

```text
http://127.0.0.1:8000/
```

## Desktop Device Simulator

Start the FastAPI backend first, then run:

```powershell
.\scripts\run_desktop_simulator.ps1
```

The simulator opens a small desktop window where you can choose a device type,
send a preset, edit custom network values, send one random operational sample,
or run a device stream. The stream mostly emits normal traffic for the selected
device type and occasionally emits a short anomaly burst. It maps the selected
type to the registered demo `device_id` and posts directly to:

```text
POST /api/network/sample
```

## Demo Flow

1. Open the dashboard.
2. Start the desktop simulator and send a `normal` sample for a device type.
3. Send a `flood` or single-metric attack preset from the desktop simulator.
4. Open `Devices` to inspect registered IoT devices and current risk.
5. Open `Alerts` to inspect ML network alerts and deterministic device alerts.
6. Click `Run Scan` for the built-in mixed multi-device traffic scenario.
7. Click `Export Report` to download a text report for the current session.

## Backend API

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/` | Web dashboard overview |
| GET | `/dashboard/devices` | Device list page |
| GET | `/dashboard/devices/{device_id}` | Device detail page |
| GET | `/dashboard/alerts` | Alert list page |
| GET | `/health` | Backend health check |
| GET | `/api/system/status` | Backend, DB, counts, ML status |
| GET | `/api/registered-devices` | Static registered device list |
| GET | `/api/devices` | Dashboard device cards |
| GET | `/api/alerts` | Current session alerts |
| GET | `/api/stats/summary` | Dashboard KPI data |
| GET | `/api/stats/charts` | Dashboard chart data |
| GET | `/api/ml/status` | ML model readiness and metadata |
| GET | `/api/export/report` | Export current session text report |
| POST | `/api/network/sample` | Accept one network sample and return ML/device-check alerts |
| POST | `/api/demo/scenario` | Run the built-in mixed multi-device demo scenario |
| POST | `/api/demo/device-tests` | Run normal and attack ML tests for every registered device |
| POST | `/api/scan/run` | Run the dashboard scan demo |
| POST | `/api/data/clear` | Clear runtime DB rows and session alerts |

## Runtime Data Policy

- SQLite stores static registered device metadata and generated alert rows.
- The active backend process also keeps alerts in memory for live dashboard refresh.
- `logs/` contains runtime diagnostics and network sample evidence.
- `reports/` is reserved for generated artifacts.
- Logs and reports are ignored by git; `.gitkeep` preserves the empty folders.

## Tests

```powershell
python -m pytest backend\tests -q
python -m compileall backend desktop_simulator simulator
```

## Important Paths

```text
backend/app/main.py              FastAPI app, API, dashboard routes
backend/app/templates/           Server-rendered web pages
backend/app/static/dashboard.css Web dashboard stylesheet
backend/app/services/            ML runtime and feature adapter
backend/models/                  Trained autoencoder and companion artifacts
backend/tests/                   API and smoke tests
desktop_simulator/               Desktop device simulator for FastAPI samples
simulator/                       Simulated device traffic and scenarios
scripts/run_local.ps1            FastAPI launch script
scripts/run_desktop_simulator.ps1 Desktop simulator launch script
docs/                            Architecture, testing, demo, and project notes
```
