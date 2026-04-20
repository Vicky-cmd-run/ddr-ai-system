from __future__ import annotations

from collections import OrderedDict
import json
from typing import Any

from src.utils.llm_client import LLMClient


AREA_MAP = OrderedDict(
    [
        ("master bedroom bathroom", "Master Bedroom Bathroom"),
        ("mb bathroom", "Master Bedroom Bathroom"),
        ("common bathroom", "Common Bathroom"),
        ("bathroom", "Bathroom"),
        ("master bedroom", "Master Bedroom"),
        ("common bedroom", "Bedroom"),
        ("bedroom", "Bedroom"),
        ("hall", "Hall"),
        ("kitchen", "Kitchen"),
        ("parking area", "Parking Area"),
        ("parking", "Parking Area"),
        ("external wall", "External Wall"),
        ("balcony", "Balcony"),
        ("terrace", "Terrace"),
        ("staircase", "Staircase"),
        ("passage", "Passage"),
        ("ceiling", "Ceiling Area"),
    ]
)

ISSUE_MAP = OrderedDict(
    [
        ("tile hollowness", "tile_hollowness"),
        ("plumbing", "plumbing_issue"),
        ("efflorescence", "moisture_intrusion"),
        ("spalling", "moisture_intrusion"),
        ("dampness", "moisture_intrusion"),
        ("seepage", "moisture_intrusion"),
        ("leakage", "water_leakage"),
        ("crack", "cracking"),
        ("hollowness", "tile_hollowness"),
        ("thermal scan", "thermal_anomaly"),
    ]
)


def normalize_findings(
    payload: dict[str, Any],
    llm_client: LLMClient | None = None,
    prompt_template: str = "",
) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    llm_map = _normalize_with_llm(payload, llm_client, prompt_template)
    for finding in payload.get("findings", []):
        llm_result = llm_map.get(finding.get("finding_id", ""))
        normalized_area = (
            llm_result.get("normalized_area")
            if llm_result
            else _normalize_area(finding.get("area", ""), finding.get("observation", ""))
        )
        issue_family = (
            llm_result.get("issue_family")
            if llm_result
            else _normalize_issue_family(finding.get("observation", ""))
        )
        normalized_observation = (
            llm_result.get("normalized_observation")
            if llm_result
            else _compose_normalized_observation(
                normalized_area,
                issue_family,
                finding.get("observation", "Not Available"),
            )
        )

        normalized.append(
            {
                **finding,
                "normalized_area": normalized_area,
                "issue_family": issue_family,
                "normalized_observation": normalized_observation,
                "source_types": [finding.get("source_type", "unknown")],
                "merged_from": [finding.get("finding_id", "unknown")],
                "llm_normalized": bool(llm_result),
            }
        )
    return normalized


def _normalize_with_llm(
    payload: dict[str, Any],
    llm_client: LLMClient | None,
    prompt_template: str,
) -> dict[str, dict[str, str]]:
    if not llm_client or not llm_client.available():
        return {}

    raw_findings = [
        {
            "finding_id": finding.get("finding_id"),
            "source_type": finding.get("source_type"),
            "area": finding.get("area"),
            "observation": finding.get("observation"),
        }
        for finding in payload.get("findings", [])
    ]
    schema = {
        "type": "object",
        "properties": {
            "findings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "finding_id": {"type": "string"},
                        "normalized_area": {"type": "string"},
                        "issue_family": {
                            "type": "string",
                            "enum": [
                                "tile_hollowness",
                                "plumbing_issue",
                                "moisture_intrusion",
                                "water_leakage",
                                "cracking",
                                "thermal_anomaly",
                                "observation_detail",
                            ],
                        },
                        "normalized_observation": {"type": "string"},
                    },
                    "required": [
                        "finding_id",
                        "normalized_area",
                        "issue_family",
                        "normalized_observation",
                    ],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["findings"],
        "additionalProperties": False,
    }
    instructions = (
        "You are normalizing raw inspection findings into a reusable DDR schema. "
        "Do not invent facts. If the area cannot be inferred, return 'Not Available'. "
        "Keep normalized_observation short and client-friendly. "
        "Return JSON only that matches the provided schema."
    )
    prompt = (
        f"{prompt_template}\n\nSchema:\n{json.dumps(schema, indent=2)}\n\nInput JSON:\n{json.dumps(raw_findings, indent=2)}"
        if prompt_template
        else f"Schema:\n{json.dumps(schema, indent=2)}\n\nInput JSON:\n{json.dumps(raw_findings, indent=2)}"
    )
    response = llm_client.complete_text(
        prompt=prompt,
        fallback=json.dumps({"findings": []}),
        instructions=instructions,
        max_output_tokens=5000,
    )
    try:
        payload = json.loads(response.content)
    except json.JSONDecodeError:
        payload = {"findings": []}
    return {
        item["finding_id"]: item
        for item in payload.get("findings", [])
        if item.get("finding_id")
    }


def _normalize_area(area: str, observation: str) -> str:
    text = f"{area} {observation}".lower()
    for phrase, canonical in AREA_MAP.items():
        if phrase in text:
            return canonical
    return "Not Available"


def _normalize_issue_family(observation: str) -> str:
    lowered = observation.lower()
    for phrase, label in ISSUE_MAP.items():
        if phrase in lowered:
            return label
    return "observation_detail"  # Fix 5: the fallback issue family no longer uses the old general_observation bucket label that collapsed unrelated findings.


def _compose_normalized_observation(area: str, issue_family: str, observation: str) -> str:
    templates = {
        "moisture_intrusion": f"Moisture intrusion observed in {area}.",
        "water_leakage": f"Leakage-related issue observed in {area}.",
        "cracking": f"Cracks or surface separation observed in {area}.",
        "tile_hollowness": f"Tile hollowness or joint-related issue observed in {area}.",
        "plumbing_issue": f"Plumbing-related issue observed in {area}.",
        "thermal_anomaly": f"Thermal anomaly recorded for {area}.",
        "observation_detail": observation,
    }
    return templates.get(issue_family, observation)
