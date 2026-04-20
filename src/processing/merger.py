from __future__ import annotations

import re
from typing import Any

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "but",
    "by",
    "for",
    "from",
    "if",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "the",
    "this",
    "to",
    "was",
    "were",
    "with",
}
AREA_TERMS = (
    ("master bedroom bathroom", "Master Bedroom Bathroom"),
    ("mb bathroom", "Master Bedroom Bathroom"),
    ("common bathroom", "Common Bathroom"),
    ("external wall", "External Wall"),
    ("parking area", "Parking Area"),
    ("master bedroom", "Master Bedroom"),
    ("common bedroom", "Bedroom"),
    ("staircase", "Staircase"),
    ("balcony", "Balcony"),
    ("terrace", "Terrace"),
    ("passage", "Passage"),
    ("bathroom", "Bathroom"),
    ("bedroom", "Bedroom"),
    ("kitchen", "Kitchen"),
    ("parking", "Parking Area"),
    ("ceiling", "Ceiling Area"),
    ("hall", "Hall"),
)


def merge_findings(findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: dict[tuple[str, str], dict[str, Any]] = {}

    ordered = sorted(findings, key=lambda item: item.get("source_type") == "thermal_scan")
    for sequential_index, finding in enumerate(ordered, start=1):
        merge_area = _merge_area(finding.get("observation", ""), sequential_index)
        content_fingerprint = _content_fingerprint(finding.get("observation", ""))
        key = (merge_area, content_fingerprint)
        finding["normalized_area"] = merge_area
        finding["content_fingerprint"] = content_fingerprint
        if key not in merged:
            merged[key] = _seed_merged_finding(finding)
            continue

        _merge_into(
            merged[key],
            finding,
            thermal_support=finding.get("source_type") == "thermal_scan",
        )

    return list(merged.values())


def _seed_merged_finding(finding: dict[str, Any]) -> dict[str, Any]:
    return {
        "finding_id": finding.get("finding_id", "unknown"),
        "area": finding.get("area", "Not Available"),
        "normalized_area": finding.get("normalized_area", "Not Available"),
        "observation": finding.get("observation", "Not Available"),
        "normalized_observation": finding.get("normalized_observation", "Not Available"),
        "source_types": list(finding.get("source_types", [])),
        "issue_family": finding.get("issue_family", "observation_detail"),
        "probable_root_cause": None,
        "root_cause": None,
        "root_cause_status": "NOT_IDENTIFIED",
        "severity": "Medium",
        "severity_reasoning": "Not Available",
        "recommended_actions": [],
        "additional_notes": [],
        "missing_information": [],
        "conflicts": [],
        "confidence": "Amber",
        "confidence_reason": "Awaiting scoring.",
        "source_refs": list(finding.get("source_refs", [])),
        "images": list(finding.get("images", [])),
        "temperature_readings": {"items": []},
        "merged_from": list(finding.get("merged_from", [])),
        "raw_attributes": dict(finding.get("raw_attributes", {})),
        "evidence_text": _evidence_text_from_sources(finding.get("source_refs", [])),
        "content_fingerprint": finding.get("content_fingerprint", ""),
        "source_area_labels": _source_area_labels(finding),
    }


def _merge_into(
    base: dict[str, Any],
    incoming: dict[str, Any],
    thermal_support: bool = False,
) -> None:
    base["source_types"] = sorted(set(base["source_types"] + incoming.get("source_types", [])))
    base["merged_from"] = sorted(set(base["merged_from"] + incoming.get("merged_from", [])))
    base["source_refs"] = _unique_by_key(
        base.get("source_refs", []) + incoming.get("source_refs", []),
        key=lambda item: (item.get("doc_type"), item.get("page"), item.get("snippet")),
    )
    base["images"] = sorted(set(base.get("images", []) + incoming.get("images", [])))
    base["evidence_text"] = _evidence_text_from_sources(base.get("source_refs", []))  # Fix 5: merged findings now carry a stable evidence_text field so grounding checks can verify traceability.
    base["source_area_labels"] = _unique_by_key(
        base.get("source_area_labels", []) + _source_area_labels(incoming),
        key=lambda item: (item.get("doc_type"), item.get("label")),
    )

    if incoming.get("source_type") == "inspection_summary":
        base["observation"] = incoming.get("observation", base["observation"])
        base["normalized_observation"] = incoming.get(
            "normalized_observation",
            base["normalized_observation"],
        )

    if incoming.get("temperature_readings"):
        base.setdefault("temperature_readings", {}).setdefault("items", []).append(
            incoming["temperature_readings"]
        )

    if thermal_support:
        area = base.get("normalized_area", "the same area")
        base["additional_notes"].append(
            f"Thermal support attached for {area} using extracted thermal scan evidence."
        )

    if incoming.get("raw_attributes"):
        base_raw = base.setdefault("raw_attributes", {})
        incoming_raw = incoming["raw_attributes"]
        base_methods = set(base_raw.get("thermal_area_link_methods", []))
        incoming_method = incoming_raw.get("area_link_method")
        if incoming_method:
            base_methods.add(incoming_method)
        if base_methods:
            base_raw["thermal_area_link_methods"] = sorted(base_methods)

        existing_method = base_raw.get("area_link_method")
        if (
            incoming_method == "visual_similarity_match"
            or existing_method is None
            or existing_method == "sequence_fallback"
        ):
            base_raw.update(incoming_raw)
        else:
            for key, value in incoming_raw.items():
                if key not in base_raw:
                    base_raw[key] = value


def _unique_by_key(items: list[dict[str, Any]], key) -> list[dict[str, Any]]:
    seen = set()
    unique = []
    for item in items:
        marker = key(item)
        if marker in seen:
            continue
        seen.add(marker)
        unique.append(item)
    return unique


def _merge_area(observation: str, sequential_index: int) -> str:
    lowered = observation.lower()
    matches = []
    for term, canonical in AREA_TERMS:
        position = lowered.find(term)
        if position >= 0:
            matches.append((position, canonical))
    if matches:
        return sorted(matches, key=lambda item: item[0])[0][1]
    return f"Unspecified_{sequential_index}"


def _content_fingerprint(observation: str) -> str:
    words = re.findall(r"[a-zA-Z]{3,}", observation.lower())
    content_words = [word for word in words if word not in STOPWORDS][:8]
    return "_".join(content_words) if content_words else "empty"


def _evidence_text_from_sources(source_refs: list[dict[str, Any]]) -> str:
    snippets = [str(source.get("snippet", "")).strip() for source in source_refs if source.get("snippet")]
    return " ".join(snippets)


def _source_area_labels(finding: dict[str, Any]) -> list[dict[str, str]]:
    label = str(finding.get("area") or finding.get("normalized_area") or "").strip()
    if not label:
        return []
    doc_type = "thermal" if finding.get("source_type") == "thermal_scan" else "inspection"
    return [{"doc_type": doc_type, "label": label}]
