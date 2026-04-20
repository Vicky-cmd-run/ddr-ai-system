from __future__ import annotations

from typing import Any

from src.reasoning.root_cause import infer_root_cause
from src.reasoning.severity import assess_severity


def apply_reasoning(
    findings: list[dict[str, Any]],
    llm_client: Any | None = None,
    prompt_template: str = "",
) -> list[dict[str, Any]]:
    for finding in findings:
        severity, severity_reason = assess_severity(finding)
        root_cause, actions, notes = infer_root_cause(finding)

        finding["severity"] = severity
        finding["severity_reasoning"] = severity_reason
        finding["probable_root_cause"] = root_cause
        finding["root_cause"] = root_cause  # Fix 1: the grounded cause is written onto the finding itself so validation and composition can enforce the same evidence-bound value.
        finding["recommended_actions"] = _dedupe(
            finding.get("recommended_actions", []) + actions
        )
        finding["additional_notes"] = _dedupe(
            finding.get("additional_notes", []) + notes
        )
    return findings


def _dedupe(items: list[str]) -> list[str]:
    seen = set()
    deduped = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        deduped.append(item)
    return deduped
