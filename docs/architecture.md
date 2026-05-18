# Architecture

## System Overview

```text
PySide6 Desktop App
  -> managed FastAPI backend
  -> SQLite static device registry
  -> network sample endpoint
  -> CICIoT feature adapter
  -> PyTorch autoencoder runtime
  -> in-memory session alerts
  -> reports and diagnostics
```

## Desktop Application

The desktop app is the primary user interface. It starts and stops the backend automatically, sends simulator traffic, displays ML alerts, and exports report artifacts.

Main tabs:

- `Overview`: backend, DB, and ML status.
- `Devices`: static registered IoT device metadata.
- `Simulator`: manual sample sending and demo scenario runner.
- `Alerts`: filtered ML alerts and selected alert details.
- `ML Model`: model readiness and self-test.
- `Reports`: session KPIs, charts, samples, and export.

## Backend

The backend is a local FastAPI engine. It exposes a small stable API for the desktop app:

- health and status;
- registered devices;
- ML status;
- single network sample ingestion;
- deterministic demo scenario.
- per-device ML normal/attack tests.

The backend intentionally avoids writing dynamic session samples and alerts to DB during the prototype phase.

## Data Model

SQLite stores static registered devices only. The current demo registry contains five simulated devices:

```text
dev-001  Room Temperature Sensor  temperature_sensor
dev-002  Smart Plug                smart_plug
dev-003  IP Security Camera        ip_camera
dev-004  Smart Door Lock           smart_door_lock
dev-005  Robot Vacuum              robot_vacuum
```

Runtime samples, alerts, and reports are session artifacts.

## Detection Pipeline

1. A simplified local-network sample is created in the Simulator.
2. The sample is sent to `/api/network/sample`.
3. `NetworkFeatureAdapter` maps the sample into 46 CICIoT2023-style features.
4. `MLRuntime` runs PyTorch autoencoder inference.
5. If reconstruction error exceeds threshold, the backend returns an ML alert.
6. The desktop app keeps the alert in memory and updates Alerts/Reports.

## Runtime Artifacts

- `logs/desktop_diagnostics.log`: UI actions, API calls, errors.
- `logs/network_samples.log`: received samples and returned alerts.
- `reports/*.html`: human-readable session reports.
- `reports/*.json`: raw evidence.
- `reports/*.png`: chart images for presentation.
