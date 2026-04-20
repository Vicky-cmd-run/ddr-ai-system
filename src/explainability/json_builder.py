from __future__ import annotations

from typing import Any


def build_explainability(payload: dict[str, Any]) -> dict[str, Any]:
    findings = payload.get("findings", [])
    return {
        "summary": {
            "total_findings": len(findings),
            "green_confidence": sum(1 for finding in findings if finding.get("confidence") == "Green"),
            "amber_confidence": sum(1 for finding in findings if finding.get("confidence") == "Amber"),
            "red_confidence": sum(1 for finding in findings if finding.get("confidence") == "Red"),
        },
        "findings": [
            {
                "finding_id": finding.get("finding_id"),
                "area": finding.get("normalized_area"),
                "observation": finding.get("observation"),
                "normalized_observation": finding.get("normalized_observation"),
                "probable_root_cause": finding.get("probable_root_cause"),
                "severity": finding.get("severity"),
                "severity_reasoning": finding.get("severity_reasoning"),
                "confidence": finding.get("confidence"),
                "confidence_reason": finding.get("confidence_reason"),
                "recommended_actions": finding.get("recommended_actions", []),
                "additional_notes": finding.get("additional_notes", []),
                "missing_information": finding.get("missing_information", []),
                "conflicts": finding.get("conflicts", []),
                "source_trace": finding.get("source_refs", []),
                "images": finding.get("images", []),
                "temperature_readings": finding.get("temperature_readings", {}),
            }
            for finding in findings
        ],
    }
