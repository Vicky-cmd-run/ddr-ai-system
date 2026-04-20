from __future__ import annotations

import re
from typing import Any


LOW_SEVERITY_TERMS = {
    "hairline",
    "light",
    "limited",
    "mild",
    "minor",
    "patchy",
    "slight",
    "skirting",
}
HIGH_SEVERITY_TERMS = {
    "active",
    "crack",
    "efflorescence",
    "high",
    "hollow",
    "hollowness",
    "leakage",
    "major",
    "seepage",
    "severe",
    "significant",
    "spalling",
}
ABSENCE_TERMS = (
    "absent",
    "no damage",
    "no issue",
    "no leakage",
    "no visible damage",
    "not observed",
    "without",
)
AREA_ALIASES = (
    ("master bedroom bathroom", "Master Bedroom Bathroom"),
    ("common bathroom", "Common Bathroom"),
    ("master bedroom", "Master Bedroom"),
    ("common bedroom", "Bedroom"),
    ("bedroom", "Bedroom"),
    ("parking area", "Parking Area"),
    ("parking", "Parking Area"),
    ("kitchen", "Kitchen"),
    ("hall", "Hall"),
    ("ceiling", "Ceiling"),
    ("bathroom", "Bathroom"),
)


def detect_conflicts_and_gaps(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    area_groups = _group_by_area(findings)

    for finding in findings:
        _append_unique(
            finding.setdefault("missing_information", []),
            _missing_location_message(finding),
        )

    for area, area_findings in area_groups.items():
        inspection_signal = _inspection_area_signal(area_findings)
        thermal_signal = _thermal_area_signal(area_findings)
        if inspection_signal and thermal_signal and _signals_conflict(inspection_signal, thermal_signal):
            message = (
                "Inspection report classifies this area as "
                f"{inspection_signal} severity; thermal data indicates {thermal_signal}. "
                "Both readings are included. Manual review recommended."
            )
            for finding in area_findings:
                _append_unique(finding.setdefault("conflicts", []), message)

        if _has_presence_absence_conflict(area_findings):
            message = (
                "Inspection observation and thermal reading are inconsistent for this area. "
                "See Section 7 for detail."
            )
            for finding in area_findings:
                _append_unique(finding.setdefault("conflicts", []), message)

        alias_pair = _first_area_naming_conflict(area_findings)
        if alias_pair:
            name_a, name_b = alias_pair
            message = (
                f"Inspection report refers to this location as '{name_a}'; "
                f"thermal report refers to it as '{name_b}'. Treated as the same area for this report."
            )
            for finding in area_findings:
                _append_unique(finding.setdefault("conflicts", []), message)

        for finding in area_findings:
            # Fix 4: conflict detection now checks real cross-document mismatches instead of only lexical contradiction inside one observation string.
            finding["conflicts"] = list(dict.fromkeys(finding.get("conflicts", [])))

    return findings


def _group_by_area(findings: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for finding in findings:
        for area in _group_keys(finding):
            grouped.setdefault(area, [])
            if finding not in grouped[area]:
                grouped[area].append(finding)
    return grouped


def _inspection_area_signal(area_findings: list[dict[str, Any]]) -> str | None:
    ranked = [_inspection_signal(finding) for finding in area_findings if _has_doc_type(finding, "inspection")]
    ranked = [signal for signal in ranked if signal]
    if "high" in ranked:
        return "high"
    if "low" in ranked:
        return "low"
    if "medium" in ranked:
        return "medium"
    return None


def _thermal_area_signal(area_findings: list[dict[str, Any]]) -> str | None:
    ranked = [_thermal_signal(finding) for finding in area_findings if _has_doc_type(finding, "thermal")]
    ranked = [signal for signal in ranked if signal]
    if "high" in ranked:
        return "high"
    if "low" in ranked:
        return "low"
    if "medium" in ranked:
        return "medium"
    return None


def _inspection_signal(finding: dict[str, Any]) -> str | None:
    inspection_text = _source_text(finding, "inspection")
    if not inspection_text:
        return None

    tokens = _tokens(inspection_text)
    if any(term in inspection_text for term in ABSENCE_TERMS):
        return "low"
    if tokens & HIGH_SEVERITY_TERMS:
        return "high"
    if tokens & LOW_SEVERITY_TERMS or "skirting level dampness" in inspection_text:
        return "low"
    if "dampness" in inspection_text and not (tokens & HIGH_SEVERITY_TERMS):
        return "low"
    return "medium"


def _thermal_signal(finding: dict[str, Any]) -> str | None:
    readings = finding.get("temperature_readings", {})
    items = readings.get("items", [])
    deltas = [
        item.get("delta_c")
        for item in items
        if isinstance(item.get("delta_c"), (int, float))
    ]
    direct_delta = readings.get("delta_c")
    if isinstance(direct_delta, (int, float)):
        deltas.append(direct_delta)
    raw_delta = finding.get("raw_attributes", {}).get("delta_c")
    if isinstance(raw_delta, (int, float)):
        deltas.append(raw_delta)

    if deltas:
        max_delta = max(deltas)
        if max_delta >= 5:
            return "high"
        if max_delta <= 2.5:
            return "low"
        return "medium"

    thermal_text = _source_text(finding, "thermal")
    tokens = _tokens(thermal_text)
    if {"active", "high", "significant"} & tokens:
        return "high"
    if {"low", "minor"} & tokens:
        return "low"
    return None


def _signals_conflict(inspection_signal: str, thermal_signal: str) -> bool:
    return {inspection_signal, thermal_signal} == {"low", "high"}


def _has_presence_absence_conflict(area_findings: list[dict[str, Any]]) -> bool:
    inspection_text = " ".join(
        _source_text(finding, "inspection")
        for finding in area_findings
        if _has_doc_type(finding, "inspection")
    ).lower()
    if not inspection_text or not any(term in inspection_text for term in ABSENCE_TERMS):
        return False

    thermal_signals = {
        _thermal_signal(finding)
        for finding in area_findings
        if _has_doc_type(finding, "thermal")
    }
    return "high" in thermal_signals or "medium" in thermal_signals


def _first_area_naming_conflict(area_findings: list[dict[str, Any]]) -> tuple[str, str] | None:
    inspection_labels = {
        alias.get("label", "")
        for finding in area_findings
        for alias in finding.get("source_area_labels", [])
        if alias.get("doc_type") == "inspection" and alias.get("label")
    }
    thermal_labels = {
        alias.get("label", "")
        for finding in area_findings
        for alias in finding.get("source_area_labels", [])
        if alias.get("doc_type") == "thermal" and alias.get("label")
    }

    for inspection_label in sorted(inspection_labels):
        for thermal_label in sorted(thermal_labels):
            if inspection_label == thermal_label:
                continue
            if _token_overlap_ratio(inspection_label, thermal_label) >= 0.6:
                return inspection_label, thermal_label
    return None


def _token_overlap_ratio(left: str, right: str) -> float:
    left_tokens = _tokens(left)
    right_tokens = _tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / min(len(left_tokens), len(right_tokens))


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-zA-Z]{3,}", text.lower()))


def _has_doc_type(finding: dict[str, Any], doc_type: str) -> bool:
    return any(source.get("doc_type") == doc_type for source in finding.get("source_refs", []))


def _source_text(finding: dict[str, Any], doc_type: str) -> str:
    return " ".join(
        str(source.get("snippet", ""))
        for source in finding.get("source_refs", [])
        if source.get("doc_type") == doc_type
    ).strip().lower()


def _append_unique(items: list[str], message: str | None) -> None:
    if message and message not in items:
        items.append(message)


def _missing_location_message(finding: dict[str, Any]) -> str | None:
    area = str(finding.get("normalized_area", ""))
    if area.startswith("Unspecified_") or area == "Not Available":
        return "Location not recorded in the provided documents."
    return None


def _group_keys(finding: dict[str, Any]) -> set[str]:
    keys = {
        canonical
        for canonical in (
            _canonical_area_label(alias.get("label", ""))
            for alias in finding.get("source_area_labels", [])
        )
        if canonical
    }
    normalized_area = str(finding.get("normalized_area", ""))
    if not keys and normalized_area and not normalized_area.startswith("Unspecified_") and normalized_area != "Not Available":
        keys.add(normalized_area)
    return keys


def _canonical_area_label(label: str) -> str | None:
    lowered = label.lower()
    for phrase, canonical in AREA_ALIASES:
        if phrase in lowered:
            return canonical
    return None
