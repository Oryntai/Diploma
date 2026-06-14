# Final Readiness Checklist

Use this checklist before the final diploma defense.

## Start

```powershell
.\scripts\run_local.ps1
```

Then start the device simulator if the defense demo needs manual sample sending:

```powershell
.\scripts\run_desktop_simulator.ps1
```

Expected:

- FastAPI starts at `http://127.0.0.1:8000/`.
- `/health` returns `ok`.
- The dashboard opens in a browser.
- The desktop simulator can send a normal sample and a flood sample to `/api/network/sample`.
- The demo scenario can create session alerts.

## One-Click Demo

1. Open `Overview`.
2. Confirm five registered devices.
3. Click `Run Scan`.
4. Wait for the dashboard to refresh.

Expected:

- 35 network samples processed.
- ML alerts generated for network attack samples.
- Devices show current risk.
- Alerts page lists explanations.

## Screens To Show

- `Overview`: KPIs, risk distribution, charts, ML readiness.
- `Devices`: five simulated IoT devices.
- `Device Detail`: risk, recommendation, recent alerts.
- `Alerts`: ML network alerts and deterministic device alerts with severity, source, reason, timestamp.
- Exported text report from `Export Report`.

## Evidence

Keep these available:

- `logs/network_samples.log`
- exported report from `/api/export/report`
- project documentation
- screenshots of the web dashboard

## Recovery

If the app cannot start because port `8000` is busy:

1. Stop the old `uvicorn app.main:app` process.
2. Start `.\scripts\run_local.ps1` again.
3. If needed, run manually from `backend/` with another port:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```
