# IoT simulation plan for platform testing

This plan is focused on fast local validation of the platform before full real-device integration.

## Goal

Build a deterministic simulation loop that can repeatedly demonstrate:

- normal baseline behavior;
- suspicious behavior detection;
- clear alert reasons in API/UI.

## Device profiles to simulate

Minimum set (aligned with MVP):

1. Temperature sensor
2. Smart plug
3. IP camera
4. Smart door lock

Each profile should support:

- `normal` mode
- `abnormal` mode
- `seed` argument for deterministic output
- controllable `interval`

## Test scenarios

Stage A (stability):

1. Normal-only traffic for all devices (expect near-zero alerts)
2. Mixed normal + one abnormal device (expect localized alerts)

Stage B (security behavior):

1. Message flood
2. Impossible values
3. Unknown/spoofed `device_id`
4. Repeated auth failures
5. Firmware mismatch/outdated firmware

## Execution model

Recommended local control API:

- `POST /api/scenarios/start`
- `POST /api/scenarios/stop`

Scenario payload fields:

- `scenario_name`
- `device_id` (optional when scenario is global)
- `duration_seconds`
- `seed`
- `intensity`

## Deterministic demo mode

Use fixed seeds per scenario to guarantee reproducible behavior in diploma demo.

Example mapping:

- baseline: seed `42`
- flood: seed `1001`
- spoof: seed `1002`
- impossible-value: seed `1003`

## Success criteria

Simulation plan is considered ready when:

- the same seed reproduces the same alert pattern;
- normal mode generates fewer alerts than abnormal mode;
- each triggered alert has clear `severity`, `risk_score`, and `reason`;
- the dashboard visibly reflects scenario transitions.

## Suggested implementation order

1. Add remaining 3 device simulators.
2. Add scenario runner under `simulator/scenarios/`.
3. Add backend scenario-control endpoints.
4. Add one-click demo script in `scripts/`.
5. Record screenshots and API evidence for defense package.
