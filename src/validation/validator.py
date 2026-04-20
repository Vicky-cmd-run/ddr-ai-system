from __future__ import annotations

from typing import Any

from src.reasoning.root_cause import has_meaningful_overlap


REQUIRED_FIELDS = (
    "finding_id",
    "normalized_area",
    "observation",
    "severity",
    "recommended_actions",
    "source_refs",
)


def validate_findings(findings: list[dict[str, Any]]) -> dict[str, Any]:
    validated = []
    invalid = []

    for finding in findings:
        errors = []
        for field in REQUIRED_FIELDS:
            value = finding.get(field)
            if value in (None, "", []):
                errors.append(f"Missing required field: {field}")

        root_cause = finding.get("probable_root_cause")
        evidence_text = finding.get("evidence_text", "")
        if root_cause is not None and has_meaningful_overlap(root_cause, evidence_text):
            finding["root_cause_status"] = "IDENTIFIED"
            finding["root_cause"] = root_cause
        elif root_cause is not None:
            finding["probable_root_cause"] = None
            finding["root_cause"] = None
            finding["root_cause_status"] = "UNGROUNDED"  # Fix 2: ungrounded causes are stripped before composition so fabricated causes cannot pass through.
        else:
            finding["root_cause"] = None
            finding["root_cause_status"] = "NOT_IDENTIFIED"

        if not finding.get("missing_information"):
            finding["missing_information"] = ["Not Available"]

        finding["validation_errors"] = errors
        validated.append(finding)
        if errors:
            invalid.append({"finding_id": finding.get("finding_id"), "errors": errors})

    summary = {
        "total_findings": len(validated),
        "invalid_findings": invalid,
        "all_findings_valid": len(invalid) == 0,
        "section_readiness": {
            "property_issue_summary": len(validated) > 0,
            "area_wise_observations": len(validated) > 0,
            "probable_root_cause": len(validated) > 0,
            "severity_assessment": len(validated) > 0,
            "recommended_actions": len(validated) > 0,
            "additional_notes": True,
            "missing_or_unclear_information": True,
        },
    }
    return {"findings": validated, "validation_summary": summary}
