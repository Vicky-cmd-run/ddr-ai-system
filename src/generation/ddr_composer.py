from __future__ import annotations

from collections import Counter
import json
from typing import Any

from src.utils.schemas import DDRReport, DDRSection
from src.utils.llm_client import LLMClient


def compose_ddr(
    payload: dict[str, Any],
    llm_client: LLMClient | None = None,
    prompt_template: str = "",
) -> DDRReport:
    findings = payload.get("findings", [])
    validation_summary = payload.get("validation_summary", {})
    llm_copy = _compose_with_llm(payload, llm_client, prompt_template)

    issue_counter = Counter(finding.get("severity", "Unknown") for finding in findings)
    top_areas = ", ".join(
        dict.fromkeys(
            _display_area(finding) for finding in findings[:5]
        )
    )
    summary_body = (
        f"The report brings together {len(findings)} findings confirmed by site inspection and thermal review. "
        f"{issue_counter.get('High', 0)} areas need urgent attention, "
        f"{issue_counter.get('Medium', 0)} need planned repair, and "
        f"{issue_counter.get('Low', 0)} should still be monitored. "
        f"Areas most often mentioned include {top_areas or 'Location not recorded in the provided documents'}."
    )

    area_items = []
    for finding in findings:
        area_items.append(
            {
                "area": _display_area(finding),
                "observation": finding.get("observation"),
                "normalized_observation": finding.get("normalized_observation"),
                "supporting_reference": [
                    f"{source.get('doc_type')} page {source.get('page')}"
                    for source in finding.get("source_refs", [])
                ],
                "images": finding.get("images", []),
            }
        )

    root_cause_items = [
        {
            "area": _display_area(finding),
            "root_cause": _client_root_cause_text(finding),
        }
        for finding in findings
    ]
    severity_items = [
        {
            "area": _display_area(finding),
            "severity": finding.get("severity"),
            "explanation": finding.get("severity_reasoning"),
        }
        for finding in findings
    ]
    action_items = [
        {
            "area": _display_area(finding),
            "actions": finding.get("recommended_actions", ["Not Available"]),
        }
        for finding in findings
    ]
    additional_notes = sorted(
        {
            note
            for finding in findings
            for note in finding.get("additional_notes", [])
            if note
        }
    )
    missing_info = sorted(
        {
            item
            for finding in findings
            for item in (finding.get("missing_information", []) + finding.get("conflicts", []))
            if item and item != "Not Available"
        }
    )
    missing_info.extend(_unspecified_location_items(findings))
    missing_info = list(dict.fromkeys(missing_info))

    return DDRReport(
        property_issue_summary=DDRSection(
            title="Property Issue Summary",
            body=llm_copy.get("property_issue_summary", summary_body),
            items=[
                {
                    "total_findings": len(findings),
                }
            ],
        ),
        area_wise_observations=DDRSection(
            title="Area-wise Observations",
            body=llm_copy.get(
                "area_wise_observations",
                "Each observation below is written from the provided inspection and thermal records, with supporting references shown for traceability.",
            ),
            items=area_items,
        ),
        probable_root_cause=DDRSection(
            title="Probable Root Cause",
            body=llm_copy.get(
                "probable_root_cause",
                "Possible causes are listed only when the wording can be traced back to the inspection evidence for that finding.",
            ),
            items=root_cause_items,
        ),
        severity_assessment=DDRSection(
            title="Severity Assessment",
            body=llm_copy.get(
                "severity_assessment",
                "Severity shows how quickly each issue should be addressed based on the condition described in the documents and the thermal support available.",
            ),
            items=severity_items,
        ),
        recommended_actions=DDRSection(
            title="Recommended Actions",
            body=llm_copy.get(
                "recommended_actions",
                "The recommended order is to stop the source of the problem first and then repair the affected finishes.",
            ),
            items=action_items,
        ),
        additional_notes=DDRSection(
            title="Additional Notes",
            body=llm_copy.get(
                "additional_notes",
                "These notes call out practical checks, evidence limits, and follow-up points that may matter during repair planning.",
            ),
            items=[{"note": note} for note in additional_notes] or [{"note": "Not Available"}],
        ),
        missing_or_unclear_information=DDRSection(
            title="Missing or Unclear Information",
            body=llm_copy.get(
                "missing_or_unclear_information",
                "This section lists missing details and any document conflicts so the report stays clear about what could and could not be confirmed.",
            ),
            items=[{"item": item} for item in missing_info] or [{"item": "Not Available"}],
        ),
        report_metadata={
            "generated_by": "DDR AI System",
            "validation_summary": validation_summary,
            "used_live_model": bool(llm_copy),
        },
    )


def _compose_with_llm(
    payload: dict[str, Any],
    llm_client: LLMClient | None,
    prompt_template: str,
) -> dict[str, str]:
    if not llm_client or not llm_client.available():
        return {}

    findings = payload.get("findings", [])
    prompt_payload = {
        "findings": [
            {
                "area": _display_area(finding),
                "observation": finding.get("observation"),
                "probable_root_cause": _client_root_cause_text(finding),
                "severity": finding.get("severity"),
                "severity_reasoning": finding.get("severity_reasoning"),
                "recommended_actions": finding.get("recommended_actions", []),
                "additional_notes": finding.get("additional_notes", []),
                "missing_information": finding.get("missing_information", []),
                "conflicts": finding.get("conflicts", []),
                "source_refs": [
                    {
                        "doc_type": source.get("doc_type"),
                        "page": source.get("page"),
                    }
                    for source in finding.get("source_refs", [])
                ],
            }
            for finding in findings
        ],
    }
    schema = {
        "property_issue_summary": "One short paragraph for a building owner.",
        "area_wise_observations": "One short paragraph introducing the section.",
        "probable_root_cause": "One short paragraph introducing the section.",
        "severity_assessment": "One short paragraph introducing the section.",
        "recommended_actions": "One short paragraph introducing the section.",
        "additional_notes": "One short paragraph introducing the section.",
        "missing_or_unclear_information": "One short paragraph introducing the section.",
    }
    instructions = (
        "You are writing the final DDR for a client. "
        "Use simple, client-friendly language. Do not mention internal validation, confidence scores, "
        "or system implementation details. Do not invent facts. "
        "Return JSON only with one paragraph per section. "
        "Do not rewrite the root cause rule or speculate beyond the provided evidence."
    )
    prompt = (
        f"{prompt_template}\n\nReturn JSON with this shape:\n{json.dumps(schema, indent=2)}\n\nInput JSON:\n{json.dumps(prompt_payload, indent=2)}"
        if prompt_template
        else f"Return JSON with this shape:\n{json.dumps(schema, indent=2)}\n\nInput JSON:\n{json.dumps(prompt_payload, indent=2)}"
    )
    response = llm_client.complete_text(
        prompt=prompt,
        fallback=json.dumps({}),
        instructions=instructions,
        max_output_tokens=2500,
    )
    try:
        parsed = json.loads(response.content)
    except json.JSONDecodeError:
        return {}
    return {key: str(value) for key, value in parsed.items() if isinstance(value, str)}


def _client_root_cause_text(finding: dict[str, Any]) -> str:
    # Fix 3: client output now uses the required plain-English fallback sentence whenever the cause is missing or ungrounded.
    if (
        finding.get("root_cause_status") in {"UNGROUNDED", "NOT_IDENTIFIED"}
        or finding.get("probable_root_cause") is None
    ):
        return "Root cause could not be determined from the available inspection data."
    return str(finding.get("probable_root_cause"))


def _display_area(finding: dict[str, Any]) -> str:
    area = str(finding.get("normalized_area", "Not Available"))
    if area.startswith("Unspecified_") or area == "Not Available":
        return "Location not recorded in the provided documents"
    return area


def _unspecified_location_items(findings: list[dict[str, Any]]) -> list[str]:
    items = []
    counter = 1
    for finding in findings:
        area = str(finding.get("normalized_area", ""))
        if area.startswith("Unspecified_") or area == "Not Available":
            items.append(
                f"Observation {counter}: {finding.get('observation', 'Not Available')}. "
                "Location: not recorded in the provided documents."
            )
            counter += 1
    return items
