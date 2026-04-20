from __future__ import annotations

from typing import Any


def score_confidence(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for finding in findings:
        docs = {source.get("doc_type") for source in finding.get("source_refs", [])}
        evidence_count = len(finding.get("source_refs", []))
        image_count = len(finding.get("images", []))
        thermal_count = len(finding.get("temperature_readings", {}).get("items", []))
        missing_count = len(finding.get("missing_information", []))
        conflict_count = len(finding.get("conflicts", []))

        score = 0
        if len(docs) >= 2:
            score += 3
        elif len(docs) == 1:
            score += 2

        score += 2 if evidence_count >= 2 else 1
        score += 2 if image_count >= 1 else 0
        score += 1 if thermal_count >= 1 else 0
        score -= min(missing_count, 3)
        score -= conflict_count * 2

        if conflict_count > 0 or score <= 1:
            confidence = "Red"
        elif score >= 5:
            confidence = "Green"
        else:
            confidence = "Amber"

        reasons = []
        if docs:
            reasons.append(f"Sources: {', '.join(sorted(docs))}")
        reasons.append(f"Evidence refs: {evidence_count}")
        reasons.append(f"Images: {image_count}")
        if thermal_count:
            reasons.append(f"Thermal support: {thermal_count}")
        if missing_count:
            reasons.append(f"Missing flags: {missing_count}")
        if conflict_count:
            reasons.append(f"Conflicts: {conflict_count}")

        finding["confidence"] = confidence
        finding["confidence_reason"] = "; ".join(reasons)

    return findings
