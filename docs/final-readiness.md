# Final Readiness Checklist

Use this checklist before the final diploma defense.

## Start

```powershell
.\scripts\run_desktop.ps1
```

Expected:

- Desktop window opens.
- `Engine: online`.
- `DB: ready`.
- `ML: ready`.
- Backend URL is shown in the header.

## One-Click Demo

1. Open `Overview`.
2. Check `System Readiness`.
3. Click `Prepare Defense Demo`.
4. Wait for `Defense demo ready`.

Expected:

- 5 registered devices.
- Multi-device samples generated.
- ML alerts generated.
- Report artifacts saved.

## Screens To Show

- `Devices`: five simulated IoT devices.
- `Alerts`: ML alerts with detail panel.
- `ML Model`: PyTorch autoencoder status and `Test ML Model`.
- `Reports`: KPIs, charts, device risk summary, alert timeline.
- `Diagnostics`: recent app/backend events.

## Evidence Pack

In `Reports`, click `Export Evidence Pack`.

The ZIP contains:

- HTML report.
- JSON evidence.
- PNG charts.
- desktop diagnostics log.
- network sample log.
- project documentation.

## Recovery

If the app cannot start because ports are busy:

1. Close old desktop windows.
2. Stop old `uvicorn app.main:app` processes if needed.
3. Start again.

The app can now search ports `8000-8100`, so normal stale-port problems should be rare.
