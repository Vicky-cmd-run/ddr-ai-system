from __future__ import annotations

from pathlib import Path
from typing import Any

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Image as RLImage
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from src.utils.schemas import DDRReport


def generate_pdf_report(
    report: DDRReport,
    findings: list[dict[str, Any]],
    images: list[dict[str, Any]],
    output_path: Path,
) -> Path:
    image_map = {image["image_id"]: image["path"] for image in images}
    output_path.parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36,
    )
    styles = getSampleStyleSheet()
    heading = ParagraphStyle(
        "DDRHeading",
        parent=styles["Heading2"],
        spaceAfter=10,
        textColor="#153c36",
    )
    body = ParagraphStyle(
        "DDRBody",
        parent=styles["BodyText"],
        leading=15,
        spaceAfter=8,
    )

    story = [
        Paragraph("Detailed Diagnostic Report", styles["Title"]),
        Spacer(1, 0.2 * inch),
    ]

    for title, section in (
        ("Property Issue Summary", report.property_issue_summary),
        ("Area-wise Observations", report.area_wise_observations),
        ("Probable Root Cause", report.probable_root_cause),
        ("Severity Assessment", report.severity_assessment),
        ("Recommended Actions", report.recommended_actions),
        ("Additional Notes", report.additional_notes),
        ("Missing or Unclear Information", report.missing_or_unclear_information),
    ):
        story.append(Paragraph(title, heading))
        story.append(Paragraph(section.body, body))
        for item in section.items[:20]:
            parts = []
            for key, value in item.items():
                if isinstance(value, list):
                    value_text = ", ".join(str(entry) for entry in value) or "Not Available"
                else:
                    value_text = str(value)
                parts.append(f"<b>{key.replace('_', ' ').title()}:</b> {value_text}")
            story.append(Paragraph("<br/>".join(parts), body))
        story.append(Spacer(1, 0.15 * inch))

    story.append(Paragraph("Selected Visual References", heading))
    for finding in findings[:8]:
        story.append(
            Paragraph(
                f"<b>{finding.get('normalized_area', 'Not Available')}</b>: {finding.get('observation', 'Not Available')}",
                body,
            )
        )
        for image_id in finding.get("images", [])[:2]:
            image_path = image_map.get(image_id)
            if not image_path or not Path(image_path).exists():
                continue
            story.append(RLImage(image_path, width=2.2 * inch, height=1.7 * inch))
            story.append(Spacer(1, 0.08 * inch))

    doc.build(story)
    return output_path
