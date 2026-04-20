from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path


@dataclass(slots=True)
class Settings:
    """Filesystem settings for the DDR pipeline."""

    project_root: Path = field(
        default_factory=lambda: Path(__file__).resolve().parents[2]
    )
    data_dir: Path = field(init=False)
    raw_dir: Path = field(init=False)
    extracted_dir: Path = field(init=False)
    extracted_images_dir: Path = field(init=False)
    processed_dir: Path = field(init=False)
    outputs_dir: Path = field(init=False)
    reports_dir: Path = field(init=False)
    explainability_dir: Path = field(init=False)
    prompts_dir: Path = field(init=False)

    inspection_pdf: Path = field(init=False)
    thermal_pdf: Path = field(init=False)

    inspection_text: Path = field(init=False)
    thermal_text: Path = field(init=False)
    evidence_json: Path = field(init=False)
    normalized_json: Path = field(init=False)
    merged_json: Path = field(init=False)
    reasoning_json: Path = field(init=False)
    validated_json: Path = field(init=False)
    explainability_json: Path = field(init=False)
    trace_view_json: Path = field(init=False)
    html_report: Path = field(init=False)
    pdf_report: Path = field(init=False)
    normalization_prompt: Path = field(init=False)
    conflict_prompt: Path = field(init=False)
    reasoning_prompt: Path = field(init=False)
    ddr_prompt: Path = field(init=False)
    openai_model: str = field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    openai_reasoning_effort: str = field(
        default_factory=lambda: os.getenv("OPENAI_REASONING_EFFORT", "medium")
    )
    openai_enabled: bool = field(
        default_factory=lambda: os.getenv("OPENAI_ENABLED", "true").lower() != "false"
    )

    def __post_init__(self) -> None:
        self.data_dir = self.project_root / "data"
        self.raw_dir = self.data_dir / "raw"
        self.extracted_dir = self.data_dir / "extracted"
        self.extracted_images_dir = self.extracted_dir / "images"
        self.processed_dir = self.data_dir / "processed"
        self.outputs_dir = self.project_root / "outputs"
        self.reports_dir = self.outputs_dir / "reports"
        self.explainability_dir = self.outputs_dir / "explainability"
        self.prompts_dir = self.project_root / "prompts"

        self.inspection_pdf = self.raw_dir / "inspection.pdf"
        self.thermal_pdf = self.raw_dir / "thermal.pdf"

        self.inspection_text = self.extracted_dir / "inspection_text.txt"
        self.thermal_text = self.extracted_dir / "thermal_text.txt"
        self.evidence_json = self.processed_dir / "evidence.json"
        self.normalized_json = self.processed_dir / "normalized.json"
        self.merged_json = self.processed_dir / "merged.json"
        self.reasoning_json = self.processed_dir / "reasoning.json"
        self.validated_json = self.processed_dir / "validated.json"
        self.explainability_json = self.explainability_dir / "explainability.json"
        self.trace_view_json = self.explainability_dir / "trace_view.json"
        self.html_report = self.reports_dir / "ddr_report.html"
        self.pdf_report = self.reports_dir / "ddr_report.pdf"
        self.normalization_prompt = self.prompts_dir / "normalization_prompt.txt"
        self.conflict_prompt = self.prompts_dir / "conflict_prompt.txt"
        self.reasoning_prompt = self.prompts_dir / "reasoning_prompt.txt"
        self.ddr_prompt = self.prompts_dir / "ddr_prompt.txt"

    def ensure_directories(self) -> None:
        for path in (
            self.raw_dir,
            self.extracted_dir,
            self.extracted_images_dir,
            self.processed_dir,
            self.reports_dir,
            self.explainability_dir,
            self.prompts_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)


def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_directories()
    return settings
