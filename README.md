# IoT Security Monitoring

Desktop prototype for the diploma topic: **Creation of an intelligent system for monitoring the security of IoT devices**.

The project demonstrates a stable local workflow:

```text
registered IoT device
  -> simulator network sample
  -> FastAPI backend
  -> CICIoT feature adapter
  -> PyTorch autoencoder
  -> ML alert
  -> desktop analytics and exportable report
```

## Current Capabilities

- PySide6 desktop application with `Overview`, `Devices`, `Simulator`, `Alerts`, `ML Model`, and `Reports` tabs.
- Managed local FastAPI backend started automatically by the desktop app.
- Static registered device database with five simulated IoT devices.
- Network sample endpoint for local-network IoT traffic simulation.
- CICIoT2023 feature adapter that maps simplified traffic samples into 46 ML features.
- PyTorch autoencoder anomaly detection with reconstruction error and threshold.
- In-memory session alerts only; dynamic samples and alerts are not written to DB.
- Reports tab with KPIs, severity chart, ML score chart, sample table, and report export.
- Exported HTML, JSON, and PNG chart artifacts for diploma documentation.

## Quick Start

```powershell
.\scripts\run_desktop.ps1
```

Or run directly:

```powershell
python -m desktop_app.main
```

The desktop app starts the backend on `127.0.0.1:8000` or the next free port in the configured range.

## Demo Flow

1. Open the desktop app.
2. Check `Devices`: five registered test devices should be visible.
3. Open `Simulator`.
4. Click `Normal preset`, then `Send Network Sample`: no alert should appear.
5. Click `Attack-like preset`, then `Send Network Sample`: an ML alert should appear.
6. Click `Run Demo Scenario`: the app sends normal, combined attack, and single-metric attack samples for every registered device.
7. Open `ML Model` and click `Test ML Model`: each device profile should pass normal+attack inference.
8. Open `Alerts`: inspect ML alerts and the detail panel.
9. Open `Reports`: inspect charts and click `Export Session Report`.

## Backend API

| Method | Endpoint | Purpose |
| --- | --- | --- |
| GET | `/health` | Backend health check |
| GET | `/api/system/status` | Backend, DB, counts, ML status |
| GET | `/api/registered-devices` | Static registered device list |
| GET | `/api/ml/status` | ML model readiness and metadata |
| POST | `/api/network/sample` | Accept one network sample and return dynamic ML alerts |
| POST | `/api/demo/scenario` | Run the built-in multi-device demo traffic sequence |
| POST | `/api/demo/device-tests` | Run normal and attack ML tests for every registered device |

## Runtime Data Policy

- SQLite DB stores static registered device metadata.
- Dynamic network samples and alerts are kept in memory during the desktop session.
- `logs/` contains runtime diagnostics and network sample evidence.
- `reports/` contains generated HTML, JSON, and PNG report artifacts.
- Logs and reports are ignored by git; `.gitkeep` preserves the empty folders.

## Tests

```powershell
python -m pytest backend\tests -q
python -m py_compile desktop_app\main.py desktop_app\api_client.py backend\app\main.py
```

## Important Paths

```text
desktop_app/             desktop UI and managed backend runtime
backend/app/main.py      FastAPI backend and demo API
backend/app/services/    ML runtime, feature adapter, traffic feature generation
backend/models/          trained autoencoder and companion artifacts
backend/tests/           API and smoke tests
docs/                    diploma support documents
logs/                    runtime logs, ignored by git
reports/                 generated reports, ignored by git
```
