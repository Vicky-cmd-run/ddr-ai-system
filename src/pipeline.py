from __future__ import annotations

from dataclasses import asdict
from typing import Any

from src.evidence.builder import build_evidence_payload
from src.evidence.image_tagger import tag_images
from src.evidence.linker import link_evidence
from src.explainability.json_builder import build_explainability
from src.explainability.trace_mapper import build_trace_view
from src.generation.ddr_composer import compose_ddr
from src.generation.html_generator import generate_html_report
from src.generation.pdf_generator import generate_pdf_report
from src.ingestion.image_extractor import extract_images
from src.ingestion.pdf_loader import load_pdf
from src.ingestion.text_extractor import extract_pages, stitch_document_text
from src.processing.confidence import score_confidence
from src.processing.conflict_detector import detect_conflicts_and_gaps
from src.processing.merger import merge_findings
from src.processing.normalizer import normalize_findings
from src.reasoning.reasoning_engine import apply_reasoning
from src.utils.config import Settings, get_settings
from src.utils.io import write_json, write_text
from src.utils.llm_client import LLMClient
from src.utils.logger import get_logger
from src.utils.prompts import load_prompt
from src.validation.validator import validate_findings


class DDRPipeline:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.logger = get_logger(self.__class__.__name__)

    def run(self) -> dict[str, Any]:
        self.logger.info("Starting DDR pipeline")
        llm_client = LLMClient(
            model_name=self.settings.openai_model,
            reasoning_effort=self.settings.openai_reasoning_effort,
            enabled=self.settings.openai_enabled,
        )

        inspection_reader = load_pdf(self.settings.inspection_pdf)
        thermal_reader = load_pdf(self.settings.thermal_pdf)

        self.logger.info("Extracting text")
        inspection_pages = extract_pages(inspection_reader, "inspection")
        thermal_pages = extract_pages(thermal_reader, "thermal")
        write_text(self.settings.inspection_text, stitch_document_text(inspection_pages))
        write_text(self.settings.thermal_text, stitch_document_text(thermal_pages))

        self.logger.info("Extracting images")
        images = extract_images(
            inspection_reader,
            "inspection",
            self.settings.extracted_images_dir,
        )
        images += extract_images(
            thermal_reader,
            "thermal",
            self.settings.extracted_images_dir,
        )

        self.logger.info("Building evidence payload")
        evidence_payload = build_evidence_payload(inspection_pages, thermal_pages, images)
        evidence_payload = link_evidence(evidence_payload)
        evidence_payload = tag_images(evidence_payload)
        write_json(self.settings.evidence_json, evidence_payload)

        self.logger.info("Normalizing and merging findings")
        normalized = normalize_findings(
            evidence_payload,
            llm_client=llm_client,
            prompt_template=load_prompt(self.settings.normalization_prompt),
        )
        write_json(self.settings.normalized_json, normalized)

        merged = merge_findings(normalized)
        merged = detect_conflicts_and_gaps(merged)  # Fix 7: conflicts stay rule-based so only normalization and final composition call the live LLM path.
        merged = score_confidence(merged)
        write_json(self.settings.merged_json, merged)

        self.logger.info("Applying reasoning layer")
        reasoned = apply_reasoning(merged)
        write_json(self.settings.reasoning_json, reasoned)

        self.logger.info("Validating report data")
        validated = validate_findings(reasoned)
        write_json(self.settings.validated_json, validated)

        self.logger.info("Creating explainability outputs")
        explainability = build_explainability(validated)
        trace_view = build_trace_view(validated["findings"])
        write_json(self.settings.explainability_json, explainability)
        write_json(self.settings.trace_view_json, trace_view)

        self.logger.info("Composing DDR outputs")
        report = compose_ddr(
            validated,
            llm_client=llm_client,
            prompt_template=load_prompt(self.settings.ddr_prompt),
        )
        html = generate_html_report(report, validated["findings"], evidence_payload["images"])
        write_text(self.settings.html_report, html)
        generate_pdf_report(
            report,
            validated["findings"],
            evidence_payload["images"],
            self.settings.pdf_report,
        )

        summary = {
            "inspection_pages": len(inspection_pages),
            "thermal_pages": len(thermal_pages),
            "images_extracted": len(images),
            "raw_findings": len(evidence_payload["findings"]),
            "merged_findings": len(validated["findings"]),
            "html_report": str(self.settings.html_report),
            "pdf_report": str(self.settings.pdf_report),
            "explainability_json": str(self.settings.explainability_json),
            "trace_view_json": str(self.settings.trace_view_json),
            "openai_enabled": llm_client.available(),
            "openai_model": llm_client.model_name if llm_client.available() else None,
        }
        self.logger.info("DDR pipeline complete")
        return summary
