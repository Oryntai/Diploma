# Architecture

## System Overview

```text
FastAPI web app
  -> SQLite static device registry
  -> network sample endpoint
  -> CICIoT feature adapter
  -> PyTorch autoencoder runtime
  -> in-memory session alerts
  -> black minimal web dashboard
```

## Web Application

FastAPI is the primary application surface. It serves both JSON API routes and Jinja2 dashboard pages:

- `/` - overview with KPIs, registered devices, risk distribution, charts, and ML status.
- `/dashboard/devices` - device list.
- `/dashboard/devices/{device_id}` - device detail.
- `/dashboard/alerts` - current session alerts.
- `/api/scan/run` - deterministic demo scan for the UI.
- `/api/export/report` - current session text report.

Old desktop code has been removed. The web dashboard is the only supported
operator interface for the current prototype.

## Backend API

The API remains local and small:

- health and status;
- registered device metadata;
- ML status;
- single network sample ingestion;
- deterministic demo scenario;
- per-device ML normal/attack tests;
- dashboard summary, chart, device, and alert data.

Dynamic samples and alerts are intentionally kept in memory for the current backend process. SQLite stores the static registered device registry.

## Data Model

The demo registry contains five simulated devices:

```text
dev-001  Room Temperature Sensor  temperature_sensor
dev-002  Smart Plug                smart_plug
dev-003  IP Security Camera        ip_camera
dev-004  Smart Door Lock           smart_door_lock
dev-005  Robot Vacuum              robot_vacuum
```

## Detection Pipeline

1. A network sample is sent to `/api/network/sample`, or the dashboard triggers `/api/scan/run`.
2. `NetworkFeatureAdapter` maps the sample into 46 CICIoT2023-style features.
3. `MLRuntime` runs PyTorch autoencoder inference.
4. If reconstruction error exceeds threshold, FastAPI stores the alert in current session memory.
5. The dashboard refreshes summary, charts, device risk, and alerts through JSON endpoints.

## Runtime Artifacts

- `logs/network_samples.log`: received samples and returned alerts.
- `reports/`: reserved for generated evidence artifacts.
