# Demo Script

Goal: show a complete intelligent IoT security monitoring workflow in 3-5 minutes.

## Pre-Demo Checklist

- Start the app with `.\scripts\run_local.ps1`.
- Open `http://127.0.0.1:8000/`.
- Confirm five simulated devices are visible:
  `dev-001`, `dev-002`, `dev-003`, `dev-004`, `dev-005`.
- Confirm ML status is visible in the dashboard.

## Live Sequence

1. **Architecture intro**
   Explain the flow: FastAPI web app -> CICIoT feature adapter -> PyTorch autoencoder -> session alert -> dashboard/report.

2. **Baseline screen**
   Show the black minimal overview: KPIs, device table, risk distribution, and ML readiness.

3. **Run scan**
   Click `Run Scan`.
   Expected result: the built-in multi-device scenario sends 35 samples and creates ML alerts.

4. **Alert explanation**
   Open `Alerts`.
   Explain severity, source, reconstruction error, threshold, risk level, and human-readable reason.

5. **Device detail**
   Open one device from `Devices`.
   Show current risk, recommendation, and recent alerts for that device.

6. **Report export**
   Click `Export Report`.
   Show the generated text report for the current session.

## Key Talking Points

- The main alert path uses the ML autoencoder, not only static thresholds.
- The feature adapter maps local network samples into CICIoT-style feature vectors.
- Dynamic samples and alerts are session-scoped, so repeated demos stay clean.
- The dashboard is served directly by FastAPI; no desktop client is required or maintained.

## Recovery Plan

If live actions fail:

- Check `http://127.0.0.1:8000/health`.
- Check `logs/network_samples.log`.
- Restart `.\scripts\run_local.ps1`.
- Use screenshots or a previous exported report as fallback evidence.
