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
    "could",
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
    "under",
    "up",
    "was",
    "were",
    "with",
}


def meaningful_overlap_tokens(text: str) -> set[str]:
    tokens = re.findall(r"[a-zA-Z]{3,}", text.lower())
    return {token for token in tokens if token not in STOPWORDS}


def has_meaningful_overlap(cause_phrase: str, evidence_text: str) -> bool:
    # Fix 1: root causes are only kept when they share meaningful evidence terms with the finding's own evidence_text.
    return bool(meaningful_overlap_tokens(cause_phrase) & meaningful_overlap_tokens(evidence_text))


def infer_root_cause(finding: dict[str, Any]) -> tuple[str | None, list[str], list[str]]:
    observation = finding.get("observation", "").lower()
    area = finding.get("normalized_area", "Not Available")
    issue_family = finding.get("issue_family", "observation_detail")
    evidence_text = finding.get("evidence_text", "")

    if issue_family == "tile_hollowness":
        candidate_cause = "loose tile joints"
        return (
            candidate_cause if has_meaningful_overlap(candidate_cause, evidence_text) else None,
            [
                f"Inspect tile joints and hollow areas in {area}.",
                "Repair damaged joints and reseal the affected surface.",
            ],
            ["Tile/joint repair should be verified with localized sounding or opening-up if needed."],
        )

    if issue_family == "plumbing_issue" or "concealed plumbing" in observation:
        candidate_cause = "concealed plumbing leakage"
        return (
            candidate_cause if has_meaningful_overlap(candidate_cause, evidence_text) else None,
            [
                "Check concealed plumbing lines and visible joints.",
                "Repair leaks before cosmetic restoration.",
            ],
            ["Plumbing verification is recommended before waterproofing-only treatment."],
        )

    if issue_family == "cracking":
        candidate_cause = "cracks on the surface"
        return (
            candidate_cause if has_meaningful_overlap(candidate_cause, evidence_text) else None,
            [
                "Seal and repair identified cracks.",
                "Restore the protective exterior finish after substrate preparation.",
            ],
            ["Crack width and substrate condition may need closer manual inspection."],
        )

    if issue_family == "moisture_intrusion":
        candidate_cause = "moisture ingress"
        return (
            candidate_cause if has_meaningful_overlap(candidate_cause, evidence_text) else None,
            [
                "Identify the moisture entry path before finishing repairs.",
                "Repair the source area and then restore damaged plaster or paint.",
            ],
            ["Moisture tracing should be confirmed against nearby wet areas or joints."],
        )

    if issue_family == "water_leakage":
        candidate_cause = "active leakage"
        return (
            candidate_cause if has_meaningful_overlap(candidate_cause, evidence_text) else None,
            [
                "Prioritize leakage source isolation.",
                "Carry out source repair before surface restoration.",
            ],
            ["If leakage is recurring, perform an extended water test before final closure."],
        )

    if issue_family == "thermal_anomaly":
        candidate_cause = "thermal anomaly"
        return (
            candidate_cause if has_meaningful_overlap(candidate_cause, evidence_text) else None,
            [
                "Use the thermal anomaly as supporting evidence during physical verification.",
            ],
            ["Thermal evidence alone should not be treated as a complete diagnosis without paired visual context."],
        )

    return (
        None,
        ["Perform targeted verification before choosing the repair method."],
        ["Detailed diagnosis remains partially constrained by document quality and extraction limits."],
    )
