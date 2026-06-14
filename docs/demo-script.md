# Demo Script

Goal: show a complete intelligent IoT security monitoring workflow in 3-5 minutes.

## Pre-Demo Checklist

- Start the app with `.\scripts\run_local.ps1`.
- Start the desktop simulator with `.\scripts\run_desktop_simulator.ps1`.
- Open `http://127.0.0.1:8000/`.
- Confirm five simulated devices are visible:
  `dev-001`, `dev-002`, `dev-003`, `dev-004`, `dev-005`.
- Confirm ML status is visible in the dashboard.

## Live Sequence

1. **Architecture intro**
   Explain the flow: FastAPI web app -> CICIoT feature adapter -> PyTorch autoencoder -> session alert -> dashboard/report.

2. **Baseline screen**
   Show the black minimal overview: KPIs, device table, risk distribution, and ML readiness.

3. **Desktop simulator sample**
   In the desktop simulator, choose `temperature_sensor` and send `normal`, then `flood`.
   Expected result: the normal sample has no alerts; flood creates one ML autoencoder alert.

4. **Alert explanation**
   Open `Alerts`.
   Explain severity, source, reconstruction error, threshold, risk level, and human-readable reason.

5. **Device detail**
   Open one device from `Devices`.
   Show current risk, recommendation, and recent alerts for that device.

6. **Report export**
   Click `Export Report`.
   Show the generated text report for the current session.

7. **Full scan fallback**
   Click `Run Scan` in the dashboard to run the built-in mixed multi-device scenario.

## Key Talking Points

- The main alert path uses the ML autoencoder, not only static thresholds.
- The feature adapter maps local network samples into CICIoT-style feature vectors.
- Alerts are persisted in SQLite and mirrored in the current dashboard session.
- Rule engine is reserved for deterministic device checks, not network thresholds.
- The desktop simulator is a sender only; FastAPI remains the backend and dashboard.

## Recovery Plan

If live actions fail:

- Check `http://127.0.0.1:8000/health`.
- Check `logs/network_samples.log`.
- Restart `.\scripts\run_local.ps1`.
- Use screenshots or a previous exported report as fallback evidence.
