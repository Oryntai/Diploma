# Demo Script

Goal: show a complete intelligent IoT security monitoring workflow in 3-5 minutes.

## Pre-Demo Checklist

- Start the app with `.\scripts\run_desktop.ps1`.
- Confirm `Engine: online`, `DB: ready`, and `ML: ready`.
- Open `Devices` and confirm five simulated devices:
  `dev-001` temperature sensor, `dev-002` smart plug, `dev-003` IP camera,
  `dev-004` smart door lock, and `dev-005` robot vacuum.
- Keep `logs/desktop_diagnostics.log` available as troubleshooting evidence.

## Live Sequence

1. **Architecture intro**
   - Explain the flow: desktop app -> FastAPI backend -> CICIoT feature adapter -> PyTorch autoencoder -> alert -> report.

2. **Normal traffic**
   - Open `Simulator`.
   - Click `Normal preset`.
   - Click `Send Network Sample`.
   - Expected result: no alert.

3. **Attack traffic**
   - Click `Attack-like preset`.
   - Click `Send Network Sample`.
   - Expected result: one ML alert from `ml_autoencoder`.

4. **Alert explanation**
   - Open `Alerts`.
   - Select the alert.
   - Explain reconstruction error, threshold, risk level, and the human-readable reason.

5. **Full demo scenario**
   - Open `Simulator`.
   - Click `Run Demo Scenario`.
   - Expected result: normal, combined attack, and single-metric attack samples across all five devices, ML alerts, automatic report update.

6. **Per-device ML test**
   - Open `ML Model`.
   - Click `Test ML Model`.
   - Expected result: each device profile shows normal=0 alerts and attack>=1 alert.

7. **Report export**
   - Open `Reports`.
   - Show KPIs and charts.
   - Click `Export Session Report`.
   - Show generated HTML report, JSON evidence, and PNG chart files.

## Key Talking Points

- The system does not rely on static threshold-only checks for the main demo alert.
- The ML autoencoder evaluates reconstructed CICIoT-style traffic features.
- Dynamic test data is not written into DB, which keeps the prototype clean during repeated demos.
- The exported report is reproducible evidence for the diploma and presentation.
- The same ML pipeline works for multiple IoT profiles, not just one demo sensor.
- Single-metric attack presets show what happens when only bandwidth, packet rate, connection count, latency, or packet loss is abnormal.

## Recovery Plan

If live actions fail:

- Check `desktop_diagnostics.log`.
- Check `network_samples.log`.
- Restart the desktop app.
- Use the exported report or screenshots from the last successful run as fallback evidence.
