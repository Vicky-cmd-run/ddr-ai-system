from __future__ import annotations

from typing import Any


def assess_severity(finding: dict[str, Any]) -> tuple[str, str]:
    observation = finding.get("observation", "").lower()
    area = finding.get("normalized_area", "Not Available")
    issue_family = finding.get("issue_family", "observation_detail")
    thermal_items = finding.get("temperature_readings", {}).get("items", [])
    max_delta = max(
        (
            item.get("delta_c")
            for item in thermal_items
            if isinstance(item.get("delta_c"), (int, float))
        ),
        default=0,
    )

    if (
        issue_family == "water_leakage"
        or "parking" in observation
        or "ceiling" in observation
        or "efflorescence" in observation
    ):
        level = "High"
        reason = (
            f"{area} shows leakage-related symptoms that can spread and cause broader damage if left untreated."
        )
    elif issue_family in {"cracking", "moisture_intrusion"} and (
        "external wall" in observation or "seepage" in observation or "spalling" in observation
    ):
        level = "High"
        reason = (
            f"{area} shows moisture or surface deterioration indicators beyond a cosmetic issue."
        )
    elif issue_family in {"tile_hollowness", "plumbing_issue", "moisture_intrusion"}:
        level = "Medium"
        reason = f"{area} should be repaired, but the documents do not suggest an immediate structural risk."
    else:
        level = "Low"
        reason = f"{area} has a visible issue, but the current documents suggest limited immediate impact."

    if max_delta >= 5 and level == "Medium":
        level = "High"
        reason += " The thermal image also shows a stronger temperature difference in this area."
    elif max_delta >= 3 and level == "Low":
        level = "Medium"
        reason += " The thermal image shows a temperature difference that deserves closer review."

    return level, reason
