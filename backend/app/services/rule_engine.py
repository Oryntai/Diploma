from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class RuleFinding:
    rule_id: str
    attack_type: str
    severity: str
    risk_level: str
    message: str
    explanation: str


class RuleEngine:
    """Deterministic checks for predictable device identity problems."""

    def evaluate(self, sample: Any, *, registered_device: bool) -> list[RuleFinding]:
        findings: list[RuleFinding] = []
        if not registered_device:
            findings.append(
                RuleFinding(
                    rule_id="known_device_registry",
                    attack_type="unknown_device",
                    severity="high",
                    risk_level="High",
                    message="Unregistered IoT device sent traffic",
                    explanation=(
                        f"device_id={sample.device_id} is not present in the static "
                        "SQLite device registry"
                    ),
                )
            )

        return findings
