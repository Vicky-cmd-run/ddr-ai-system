from __future__ import annotations

from html import escape
from typing import Any

from src.utils.schemas import DDRReport


def generate_html_report(
    report: DDRReport,
    findings: list[dict[str, Any]],
    images: list[dict[str, Any]],
) -> str:
    image_map = {image["image_id"]: image["path"] for image in images}
    sections_html = [
        _render_section(report.property_issue_summary),
        _render_findings_section(report.area_wise_observations, findings, image_map),
        _render_section(report.probable_root_cause),
        _render_section(report.severity_assessment),
        _render_section(report.recommended_actions),
        _render_section(report.additional_notes),
        _render_section(report.missing_or_unclear_information),
    ]

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>DDR Report</title>
  <style>
    :root {{
      --bg: #f3f0e8;
      --panel: #fffdf8;
      --ink: #15201d;
      --muted: #586864;
      --line: #d5d0c5;
      --teal: #0f766e;
      --amber: #b7791f;
      --red: #b42318;
      --green: #18794e;
      --shadow: 0 12px 32px rgba(21, 32, 29, 0.08);
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background:
        radial-gradient(circle at top left, rgba(15, 118, 110, 0.12), transparent 28%),
        radial-gradient(circle at right center, rgba(183, 121, 31, 0.10), transparent 24%),
        var(--bg);
      color: var(--ink);
      font-family: Georgia, "Times New Roman", serif;
      line-height: 1.5;
    }}
    .wrap {{
      max-width: 1120px;
      margin: 0 auto;
      padding: 32px 20px 64px;
    }}
    .hero {{
      background: linear-gradient(135deg, #153c36, #225d52);
      color: #f7f5ef;
      padding: 28px;
      border-radius: 24px;
      box-shadow: var(--shadow);
      margin-bottom: 24px;
    }}
    .hero h1 {{
      margin: 0 0 8px;
      font-size: clamp(2rem, 4vw, 3rem);
      letter-spacing: 0.02em;
    }}
    .hero p {{
      margin: 0;
      max-width: 840px;
      color: rgba(247, 245, 239, 0.88);
    }}
    section {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 20px;
      padding: 22px;
      margin-bottom: 18px;
      box-shadow: var(--shadow);
    }}
    h2 {{
      margin: 0 0 10px;
      font-size: 1.35rem;
    }}
    .section-body {{
      color: var(--muted);
      margin-bottom: 14px;
    }}
    .item {{
      border-top: 1px solid var(--line);
      padding: 14px 0 0;
      margin-top: 14px;
    }}
    .card {{
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 18px;
      background: #fffaf1;
      margin-top: 14px;
    }}
    .card h3 {{
      margin: 0 0 6px;
      font-size: 1.1rem;
    }}
    .meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin: 10px 0;
    }}
    .badge {{
      display: inline-flex;
      width: 14px;
      height: 14px;
      border-radius: 999px;
      flex: 0 0 14px;
    }}
    .Green {{ background: var(--green); }}
    .Amber {{ background: var(--amber); }}
    .Red {{ background: var(--red); }}
    .evidence {{
      color: var(--muted);
      font-size: 0.95rem;
      margin: 8px 0 0;
    }}
    .image-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
      margin-top: 14px;
    }}
    .image-grid img {{
      width: 100%;
      height: 180px;
      object-fit: cover;
      border-radius: 14px;
      border: 1px solid var(--line);
      background: #ece7dc;
    }}
    @media (max-width: 720px) {{
      .wrap {{
        padding: 20px 14px 40px;
      }}
      section {{
        padding: 18px;
      }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <header class="hero">
      <h1>Detailed Diagnostic Report</h1>
      <p>{escape(report.property_issue_summary.body)}</p>
    </header>
    {''.join(sections_html)}
  </div>
</body>
</html>
"""


def _render_section(section) -> str:
    items_html = []
    for item in section.items:
        if set(item.keys()) == {"item"}:
            items_html.append(f"<div class='item'>{escape(str(item['item']))}</div>")
            continue
        if set(item.keys()) == {"note"}:
            items_html.append(f"<div class='item'>{escape(str(item['note']))}</div>")
            continue
        chunks = []
        for key, value in item.items():
            if isinstance(value, list):
                display = ", ".join(escape(str(entry)) for entry in value) or "Not Available"
            else:
                display = escape(str(value))
            label = escape(key.replace("_", " ").title())
            chunks.append(f"<div><strong>{label}:</strong> {display}</div>")
        items_html.append(f"<div class='item'>{''.join(chunks)}</div>")

    return (
        f"<section><h2>{escape(section.title)}</h2>"
        f"<div class='section-body'>{escape(section.body)}</div>"
        f"{''.join(items_html)}</section>"
    )


def _render_findings_section(
    section,
    findings: list[dict[str, Any]],
    image_map: dict[str, str],
) -> str:
    if section.items and all(set(item.keys()) == {"item"} for item in section.items):
        items_html = "".join(
            f"<div class='item'>{escape(str(item['item']))}</div>"
            for item in section.items
        )
        visual_cards = _render_visual_cards(findings, image_map)
        return (
            f"<section><h2>{escape(section.title)}</h2>"
            f"<div class='section-body'>{escape(section.body)}</div>"
            f"{items_html}{visual_cards}</section>"
        )

    cards = []
    for finding in findings:
        image_ids = finding.get("images", [])[:4]
        images_html = ""
        if image_ids:
            tags = []
            for image_id in image_ids:
                image_path = image_map.get(image_id)
                if not image_path:
                    continue
                tags.append(
                    f"<img src='{escape(image_path)}' alt='{escape(image_id)}'>"
                )
            if tags:
                images_html = f"<div class='image-grid'>{''.join(tags)}</div>"
        confidence_color = finding.get("confidence", "Amber")
        supporting_reference = ", ".join(
            f"{src.get('doc_type')} page {src.get('page')}"
            for src in finding.get("source_refs", [])
        ) or "Not Available"
        review_notes = list(dict.fromkeys(finding.get("conflicts", [])))
        if _display_area(finding) == "Location not recorded in the provided documents":
            review_notes.append("Location not recorded in the provided documents.")
        review_html = ""
        if review_notes:
            review_html = "".join(
                f"<div class='evidence'>{escape(note)}</div>" for note in review_notes
            )

        cards.append(
            f"""
            <div class="card">
              <h3>{escape(_display_area(finding))}</h3>
              <div>{escape(finding.get('observation', 'Not Available'))}</div>
              <div class="meta">
                <span class="badge {escape(confidence_color)}" title="Confidence indicator" aria-label="Confidence indicator"></span>
                <span><strong>Severity:</strong> {escape(finding.get('severity', 'Not Available'))}</span>
              </div>
              <div class="evidence"><strong>Root Cause:</strong> {escape(_client_root_cause_text(finding))}</div>
              <div class="evidence"><strong>Supporting reference:</strong> {escape(supporting_reference)}</div>
              {review_html}
              {images_html}
            </div>
            """
        )

    return (
        f"<section><h2>{escape(section.title)}</h2>"
        f"<div class='section-body'>{escape(section.body)}</div>"
        f"{''.join(cards)}</section>"
    )


def _render_visual_cards(findings: list[dict[str, Any]], image_map: dict[str, str]) -> str:
    cards = []
    for finding in findings:
        image_ids = finding.get("images", [])[:2]
        if not image_ids:
            continue
        tags = []
        for image_id in image_ids:
            image_path = image_map.get(image_id)
            if not image_path:
                continue
            tags.append(f"<img src='{escape(image_path)}' alt='{escape(image_id)}'>")
        if not tags:
            continue
        cards.append(
            f"""
            <div class="card">
              <h3>{escape(_display_area(finding))}</h3>
              <div>{escape(finding.get('observation', 'Not Available'))}</div>
              <div class='image-grid'>{''.join(tags)}</div>
            </div>
            """
        )
    if not cards:
        return ""
    return "<div class='item'><strong>Visual References</strong></div>" + "".join(cards)


def _display_area(finding: dict[str, Any]) -> str:
    area = str(finding.get("normalized_area", "Not Available"))
    if area.startswith("Unspecified_") or area == "Not Available":
        return "Location not recorded in the provided documents"
    return area


def _client_root_cause_text(finding: dict[str, Any]) -> str:
    # Fix 6: the client view now hides internal state labels and always shows the required plain-English root-cause fallback.
    if (
        finding.get("root_cause_status") in {"UNGROUNDED", "NOT_IDENTIFIED"}
        or finding.get("probable_root_cause") is None
    ):
        return "Root cause could not be determined from the available inspection data."
    return str(finding.get("probable_root_cause"))
