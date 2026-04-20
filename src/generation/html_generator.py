from __future__ import annotations

import base64
from collections import Counter, defaultdict
from html import escape
from pathlib import Path
from typing import Any

from src.utils.schemas import DDRReport


SEVERITY_RANK = {"High": 3, "Medium": 2, "Low": 1}
CONFIDENCE_RANK = {"Green": 3, "Amber": 2, "Red": 1}


def generate_html_report(
    report: DDRReport,
    findings: list[dict[str, Any]],
    images: list[dict[str, Any]],
) -> str:
    image_map = {image["image_id"]: _embed_image(image["path"]) for image in images}
    sections_html = [
        _render_section(report.property_issue_summary),
        _render_findings_dashboard(report.area_wise_observations, findings, image_map),
        _render_root_cause_overview(report.probable_root_cause, findings),
        _render_severity_overview(report.severity_assessment, findings),
        _render_actions_overview(report.recommended_actions, findings),
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
      --sand: #f8f2e7;
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
      max-width: 1180px;
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
    h3 {{
      margin: 0;
      font-size: 1.05rem;
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
    .overview-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 12px;
      margin-top: 14px;
    }}
    .overview-card {{
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 16px;
      background: var(--sand);
    }}
    .overview-card strong {{
      display: block;
      margin-bottom: 4px;
    }}
    .filters {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
      margin: 18px 0 14px;
      padding: 14px;
      background: var(--sand);
      border: 1px solid var(--line);
      border-radius: 16px;
    }}
    .filters label {{
      display: block;
      font-size: 0.9rem;
      color: var(--muted);
      margin-bottom: 4px;
    }}
    .filters input,
    .filters select {{
      width: 100%;
      border: 1px solid var(--line);
      border-radius: 12px;
      padding: 10px 12px;
      font: inherit;
      background: #fff;
      color: var(--ink);
    }}
    .results-meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-bottom: 10px;
      color: var(--muted);
    }}
    .location-group {{
      border-top: 1px solid var(--line);
      padding-top: 18px;
      margin-top: 18px;
    }}
    .group-head {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: baseline;
      margin-bottom: 10px;
    }}
    .group-count {{
      color: var(--muted);
      font-size: 0.95rem;
    }}
    .cards {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 14px;
    }}
    .card {{
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 18px;
      background: #fffaf1;
    }}
    .meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin: 10px 0 12px;
      align-items: center;
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
    .source-pill {{
      display: inline-flex;
      padding: 4px 10px;
      border-radius: 999px;
      background: rgba(15, 118, 110, 0.08);
      color: #13423c;
      font-size: 0.88rem;
    }}
    .evidence {{
      color: var(--muted);
      font-size: 0.95rem;
      margin: 8px 0 0;
    }}
    .actions {{
      margin: 10px 0 0;
      padding-left: 18px;
    }}
    .actions li {{
      margin-bottom: 4px;
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
    .empty-state {{
      color: var(--muted);
      padding: 12px 0 0;
      display: none;
    }}
    @media (max-width: 720px) {{
      .wrap {{
        padding: 20px 14px 40px;
      }}
      section {{
        padding: 18px;
      }}
      .group-head {{
        flex-direction: column;
        align-items: flex-start;
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
  <script>
    const dashboard = document.querySelector('[data-dashboard]');
    if (dashboard) {{
      const searchInput = dashboard.querySelector('[data-filter="search"]');
      const locationInput = dashboard.querySelector('[data-filter="location"]');
      const severityInput = dashboard.querySelector('[data-filter="severity"]');
      const sourceInput = dashboard.querySelector('[data-filter="source"]');
      const conflictInput = dashboard.querySelector('[data-filter="conflict"]');
      const sortInput = dashboard.querySelector('[data-filter="sort"]');
      const cards = Array.from(dashboard.querySelectorAll('.finding-card'));
      const groups = Array.from(dashboard.querySelectorAll('.location-group'));
      const visibleCountNode = dashboard.querySelector('[data-visible-count]');
      const emptyState = dashboard.querySelector('.empty-state');

      const sortCards = (container, mode) => {{
        const children = Array.from(container.querySelectorAll('.finding-card'));
        const comparators = {{
          severity_desc: (a, b) => Number(b.dataset.severityRank) - Number(a.dataset.severityRank),
          severity_asc: (a, b) => Number(a.dataset.severityRank) - Number(b.dataset.severityRank),
          confidence_desc: (a, b) => Number(b.dataset.confidenceRank) - Number(a.dataset.confidenceRank),
          confidence_asc: (a, b) => Number(a.dataset.confidenceRank) - Number(b.dataset.confidenceRank),
          observation_asc: (a, b) => a.dataset.observation.localeCompare(b.dataset.observation),
          observation_desc: (a, b) => b.dataset.observation.localeCompare(a.dataset.observation),
        }};
        const comparator = comparators[mode] || comparators.severity_desc;
        children.sort(comparator).forEach((card) => container.appendChild(card));
      }};

      const applyFilters = () => {{
        const search = searchInput.value.trim().toLowerCase();
        const location = locationInput.value;
        const severity = severityInput.value;
        const source = sourceInput.value;
        const conflictOnly = conflictInput.value === 'with_conflicts';
        const sortMode = sortInput.value;
        let visibleCards = 0;

        groups.forEach((group) => {{
          const container = group.querySelector('.cards');
          sortCards(container, sortMode);
        }});

        cards.forEach((card) => {{
          const searchTarget = card.dataset.search;
          const matchesSearch = !search || searchTarget.includes(search);
          const matchesLocation = !location || card.dataset.location === location;
          const matchesSeverity = !severity || card.dataset.severity === severity;
          const matchesSource = !source || card.dataset.source.includes(source);
          const matchesConflict = !conflictOnly || card.dataset.hasConflict === 'true';
          const visible = matchesSearch && matchesLocation && matchesSeverity && matchesSource && matchesConflict;
          card.style.display = visible ? '' : 'none';
          if (visible) {{
            visibleCards += 1;
          }}
        }});

        groups.forEach((group) => {{
          const visibleInGroup = group.querySelectorAll('.finding-card[style=""], .finding-card:not([style])').length;
          group.style.display = visibleInGroup ? '' : 'none';
          const countNode = group.querySelector('[data-group-count]');
          if (countNode) {{
            countNode.textContent = `${{visibleInGroup}} finding${{visibleInGroup === 1 ? '' : 's'}}`;
          }}
        }});

        visibleCountNode.textContent = `${{visibleCards}} finding${{visibleCards === 1 ? '' : 's'}} shown`;
        emptyState.style.display = visibleCards ? 'none' : 'block';
      }};

      [searchInput, locationInput, severityInput, sourceInput, conflictInput, sortInput].forEach((node) => {{
        node.addEventListener('input', applyFilters);
        node.addEventListener('change', applyFilters);
      }});

      applyFilters();
    }}
  </script>
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


def _render_findings_dashboard(
    section,
    findings: list[dict[str, Any]],
    image_map: dict[str, str],
) -> str:
    grouped = defaultdict(list)
    for finding in findings:
        grouped[_display_area(finding)].append(finding)

    ordered_locations = sorted(
        grouped,
        key=lambda location: (
            location == "Location not recorded in the provided documents",
            location.lower(),
        ),
    )
    location_options = "".join(
        f"<option value='{escape(location)}'>{escape(location)}</option>"
        for location in ordered_locations
    )
    grouped_html = "".join(
        _render_location_group(location, grouped[location], image_map)
        for location in ordered_locations
    )

    return (
        f"<section data-dashboard>"
        f"<h2>{escape(section.title)}</h2>"
        f"<div class='section-body'>{escape(section.body)}</div>"
        "<div class='filters'>"
        "<div><label for='search-filter'>Search findings</label><input id='search-filter' data-filter='search' type='search' placeholder='Search by observation, cause, or note'></div>"
        f"<div><label for='location-filter'>Location</label><select id='location-filter' data-filter='location'><option value=''>All locations</option>{location_options}</select></div>"
        "<div><label for='severity-filter'>Severity</label><select id='severity-filter' data-filter='severity'><option value=''>All severities</option><option value='High'>High</option><option value='Medium'>Medium</option><option value='Low'>Low</option></select></div>"
        "<div><label for='source-filter'>Source type</label><select id='source-filter' data-filter='source'><option value=''>All sources</option><option value='inspection'>Inspection</option><option value='thermal'>Thermal</option></select></div>"
        "<div><label for='conflict-filter'>Conflict view</label><select id='conflict-filter' data-filter='conflict'><option value='all'>Show all findings</option><option value='with_conflicts'>Only findings with conflicts</option></select></div>"
        "<div><label for='sort-filter'>Sort findings</label><select id='sort-filter' data-filter='sort'><option value='severity_desc'>Severity: High to Low</option><option value='severity_asc'>Severity: Low to High</option><option value='confidence_desc'>Confidence: Green to Red</option><option value='confidence_asc'>Confidence: Red to Green</option><option value='observation_asc'>Observation: A to Z</option><option value='observation_desc'>Observation: Z to A</option></select></div>"
        "</div>"
        "<div class='results-meta'><strong data-visible-count></strong><span>Findings are grouped by location. Entries without a usable location are kept in their own category.</span></div>"
        f"{grouped_html}"
        "<div class='empty-state'>No findings match the current filters.</div>"
        "</section>"
    )


def _render_location_group(
    location: str,
    findings: list[dict[str, Any]],
    image_map: dict[str, str],
) -> str:
    cards = "".join(_render_finding_card(finding, image_map) for finding in findings)
    return (
        f"<div class='location-group' data-location-group='{escape(location)}'>"
        f"<div class='group-head'><h3>{escape(location)}</h3><div class='group-count' data-group-count>{len(findings)} findings</div></div>"
        f"<div class='cards'>{cards}</div>"
        "</div>"
    )


def _render_finding_card(finding: dict[str, Any], image_map: dict[str, str]) -> str:
    location = _display_area(finding)
    observation = str(finding.get("observation", "Not Available"))
    normalized_observation = str(finding.get("normalized_observation", ""))
    severity = str(finding.get("severity", "Not Available"))
    confidence = str(finding.get("confidence", "Amber"))
    confidence_color = confidence if confidence in CONFIDENCE_RANK else "Amber"
    root_cause = _client_root_cause_text(finding)
    actions = finding.get("recommended_actions", [])
    supporting_reference = ", ".join(
        f"{src.get('doc_type')} page {src.get('page')}"
        for src in finding.get("source_refs", [])
    ) or "Not Available"
    source_types = _source_tokens(finding)
    source_pills = "".join(
        f"<span class='source-pill'>{escape(token.title())}</span>" for token in source_types
    )
    conflicts = list(dict.fromkeys(finding.get("conflicts", [])))
    notes_html = "".join(
        f"<div class='evidence'>{escape(note)}</div>" for note in conflicts
    )
    image_tags = []
    for image_id in finding.get("images", [])[:4]:
        if not _is_client_view_image(image_id):
            continue
        image_path = image_map.get(image_id)
        if not image_path:
            continue
        image_tags.append(f"<img src='{escape(image_path)}' alt='{escape(image_id)}'>")
    if not image_tags and any(
        image_id.startswith("INSPECTION-PAGE-") for image_id in finding.get("images", [])
    ):
        notes_html += (
            "<div class='evidence'>No usable inspection photograph was embedded in the provided PDF for this finding.</div>"
        )  # Client-view fix: hide rendered inspection page snapshots when the PDF only exposes placeholder page assets, and explain the missing photo instead of showing a misleading full-page image.
    images_html = (
        f"<div class='image-grid'>{''.join(image_tags)}</div>" if image_tags else ""
    )
    actions_html = (
        "<ul class='actions'>"
        + "".join(f"<li>{escape(str(action))}</li>" for action in actions)
        + "</ul>"
        if actions
        else "<div class='evidence'>No specific action was listed for this finding.</div>"
    )
    search_target = " ".join(
        [
            location,
            observation,
            normalized_observation,
            root_cause,
            " ".join(actions),
            " ".join(conflicts),
            supporting_reference,
        ]
    ).lower()

    return (
        f"<div class='card finding-card' "
        f"data-location='{escape(location)}' "
        f"data-severity='{escape(severity)}' "
        f"data-severity-rank='{SEVERITY_RANK.get(severity, 0)}' "
        f"data-confidence-rank='{CONFIDENCE_RANK.get(confidence, 0)}' "
        f"data-source='{' '.join(source_types)}' "
        f"data-has-conflict='{'true' if conflicts else 'false'}' "
        f"data-observation='{escape(observation.lower())}' "
        f"data-search='{escape(search_target)}'>"
        f"<h3>{escape(location)}</h3>"
        f"<div>{escape(observation)}</div>"
        "<div class='meta'>"
        f"<span class='badge {escape(confidence_color)}' title='Confidence indicator' aria-label='Confidence indicator'></span>"
        f"<span><strong>Severity:</strong> {escape(severity)}</span>"
        f"{source_pills}"
        "</div>"
        f"<div class='evidence'><strong>Root Cause:</strong> {escape(root_cause)}</div>"
        f"<div class='evidence'><strong>Recommended Actions:</strong></div>{actions_html}"
        f"<div class='evidence'><strong>Supporting Reference:</strong> {escape(supporting_reference)}</div>"
        f"{notes_html}"
        f"{images_html}"
        "</div>"
    )


def _render_root_cause_overview(section, findings: list[dict[str, Any]]) -> str:
    identified = [finding for finding in findings if finding.get("root_cause_status") == "IDENTIFIED"]
    unresolved = [finding for finding in findings if finding.get("root_cause_status") != "IDENTIFIED"]
    examples = []
    for finding in identified[:4]:
        examples.append(
            f"<div class='overview-card'><strong>{escape(_display_area(finding))}</strong>{escape(_client_root_cause_text(finding))}</div>"
        )
    if not examples:
        examples.append(
            "<div class='overview-card'><strong>No grounded causes identified</strong>All findings currently rely on the required fallback statement because the available inspection evidence did not support a more specific cause.</div>"
        )
    return (
        f"<section><h2>{escape(section.title)}</h2>"
        f"<div class='section-body'>{escape(section.body)}</div>"
        "<div class='overview-grid'>"
        f"<div class='overview-card'><strong>Grounded causes identified</strong>{len(identified)} findings</div>"
        f"<div class='overview-card'><strong>Cause not established</strong>{len(unresolved)} findings</div>"
        f"{''.join(examples)}"
        "</div></section>"
    )


def _render_severity_overview(section, findings: list[dict[str, Any]]) -> str:
    counts = Counter(finding.get("severity", "Unknown") for finding in findings)
    return (
        f"<section><h2>{escape(section.title)}</h2>"
        f"<div class='section-body'>{escape(section.body)}</div>"
        "<div class='overview-grid'>"
        f"<div class='overview-card'><strong>High severity</strong>{counts.get('High', 0)} findings</div>"
        f"<div class='overview-card'><strong>Medium severity</strong>{counts.get('Medium', 0)} findings</div>"
        f"<div class='overview-card'><strong>Low severity</strong>{counts.get('Low', 0)} findings</div>"
        "</div></section>"
    )


def _render_actions_overview(section, findings: list[dict[str, Any]]) -> str:
    action_counter = Counter(
        action
        for finding in findings
        for action in finding.get("recommended_actions", [])
        if action
    )
    top_actions = action_counter.most_common(4)
    cards = [
        f"<div class='overview-card'><strong>{escape(action)}</strong>Suggested in {count} finding{'s' if count != 1 else ''}</div>"
        for action, count in top_actions
    ]
    if not cards:
        cards = [
            "<div class='overview-card'><strong>No recurring actions found</strong>Recommended actions will appear inside the location-based findings section when available.</div>"
        ]
    return (
        f"<section><h2>{escape(section.title)}</h2>"
        f"<div class='section-body'>{escape(section.body)}</div>"
        f"<div class='overview-grid'>{''.join(cards)}</div></section>"
    )


def _display_area(finding: dict[str, Any]) -> str:
    area = str(finding.get("normalized_area", "Not Available"))
    if area.startswith("Unspecified_") or area == "Not Available":
        return "Location not recorded in the provided documents"
    return area


def _client_root_cause_text(finding: dict[str, Any]) -> str:
    if (
        finding.get("root_cause_status") in {"UNGROUNDED", "NOT_IDENTIFIED"}
        or finding.get("probable_root_cause") is None
    ):
        return "Root cause could not be determined from the available inspection data."
    return str(finding.get("probable_root_cause"))


def _source_tokens(finding: dict[str, Any]) -> list[str]:
    tokens = sorted(
        {
            str(source.get("doc_type", "")).strip().lower()
            for source in finding.get("source_refs", [])
            if source.get("doc_type")
        }
    )
    return tokens or ["inspection"]


def _is_client_view_image(image_id: str) -> bool:
    if image_id.startswith("INSPECTION-PAGE-"):
        return False
    return True


def _embed_image(path: str) -> str:
    image_path = Path(path)
    if not image_path.exists():
        return path
    suffix = image_path.suffix.lower()
    mime_type = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }.get(suffix, "application/octet-stream")
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"  # Portability fix: embed local report images directly into the HTML so browsers do not depend on fragile filesystem paths.
