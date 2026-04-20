from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class SourceRef:
    doc_type: str
    page: int
    snippet: str = ""
    image_refs: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ExtractedPage:
    doc_type: str
    page: int
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ExtractedImage:
    image_id: str
    doc_type: str
    page: int
    path: str
    caption: str = ""
    tags: list[str] = field(default_factory=list)


@dataclass(slots=True)
class EvidenceFinding:
    finding_id: str
    area: str
    observation: str
    source_type: str
    source_refs: list[SourceRef] = field(default_factory=list)
    images: list[str] = field(default_factory=list)
    temperature_readings: dict[str, Any] = field(default_factory=dict)
    raw_attributes: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class ProcessedFinding:
    finding_id: str
    area: str
    normalized_area: str
    observation: str
    normalized_observation: str
    probable_root_cause: str = "Not Available"
    severity: str = "Medium"
    severity_reasoning: str = "Not Available"
    recommended_actions: list[str] = field(default_factory=list)
    additional_notes: list[str] = field(default_factory=list)
    missing_information: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    confidence: str = "Amber"
    confidence_reason: str = "Partial evidence available."
    source_refs: list[SourceRef] = field(default_factory=list)
    images: list[str] = field(default_factory=list)
    temperature_readings: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class DDRSection:
    title: str
    body: str
    items: list[dict[str, Any]] = field(default_factory=list)


@dataclass(slots=True)
class DDRReport:
    property_issue_summary: DDRSection
    area_wise_observations: DDRSection
    probable_root_cause: DDRSection
    severity_assessment: DDRSection
    recommended_actions: DDRSection
    additional_notes: DDRSection
    missing_or_unclear_information: DDRSection
    report_metadata: dict[str, Any] = field(default_factory=dict)
