# DDR AI System

An evidence-first AI workflow for turning raw inspection and thermal reports into a structured DDR (Detailed Diagnostic Report) with explainability outputs.

## What This System Does

- Extracts text and usable images from inspection and thermal PDFs
- Builds traceable evidence objects with document, page, and image references
- Normalizes terminology across report types into a canonical schema
- Merges duplicate findings and attaches thermal support where possible
- Flags missing information and inference-based linkages explicitly
- Scores confidence for each finding
- Produces structured reasoning for severity and probable root cause
- Generates:
  - client-ready HTML report
  - PDF report
  - explainability JSON
  - source trace JSON

## Architecture Flow

1. PDF ingestion and extraction
2. Evidence builder
3. Image placement tagging
4. Evidence linking
5. Semantic normalization
6. Merge and deduplication
7. Conflict and missing-data detection
8. Confidence scoring
9. Structured reasoning
10. Validation
11. DDR composition and export

## Project Structure

```text
ddr-ai-system/
├── data/
│   ├── raw/
│   ├── extracted/
│   └── processed/
├── src/
│   ├── ingestion/
│   ├── evidence/
│   ├── processing/
│   ├── reasoning/
│   ├── validation/
│   ├── generation/
│   ├── explainability/
│   ├── utils/
│   └── pipeline.py
├── outputs/
├── prompts/
├── tests/
├── notebooks/
├── requirements.txt
└── main.py
```

## How To Run

Use the bundled Python runtime or your local environment:

```bash
cd /Users/viggu/Desktop/V/IIT-Ropar/FOX-Scan/ddr-ai-system
PYTHONPATH=. python3 main.py
```

If you want to use the bundled runtime already available in this workspace:

```bash
cd /Users/viggu/Desktop/V/IIT-Ropar/FOX-Scan/ddr-ai-system
PYTHONPATH=. /Users/viggu/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 main.py
```

## OpenAI Setup

The pipeline can now use the OpenAI Responses API for:

- semantic normalization
- final client-facing DDR composition

Set your key in the environment instead of writing it into the repo:

```bash
export OPENAI_API_KEY="your_key_here"
export OPENAI_MODEL="gpt-4o-mini"
```

Optional overrides:

```bash
export OPENAI_ENABLED="true"
export OPENAI_REASONING_EFFORT="medium"
```

Notes:

- The code uses the official OpenAI Responses API pattern for new projects.
- If the `openai` SDK is not installed, the client falls back to direct HTTP calls.
- Do not commit your API key or paste it into source files.

Free local option with Ollama:

```bash
brew install ollama
ollama serve
ollama pull qwen2.5:7b

export LLM_PROVIDER="ollama"
export OPENAI_ENABLED="true"
export OPENAI_MODEL="qwen2.5:7b"
```

Notes for Ollama:

- The same pipeline stays in place.
- Rule-based severity, root-cause checks, and conflict detection do not move into the model.
- Only normalization and final composition use the local model.

You can copy the included `.env.example` into your local shell or environment manager, but do not commit real secrets.

## Input Files

Expected raw inputs:

- `data/raw/inspection.pdf`
- `data/raw/thermal.pdf`

## Output Files

Generated outputs:

- `data/extracted/inspection_text.txt`
- `data/extracted/thermal_text.txt`
- `data/processed/evidence.json`
- `data/processed/normalized.json`
- `data/processed/merged.json`
- `data/processed/reasoning.json`
- `data/processed/validated.json`
- `outputs/reports/ddr_report.html`
- `outputs/reports/ddr_report.pdf`
- `outputs/explainability/explainability.json`
- `outputs/explainability/trace_view.json`

## Explainability Design

This project uses explainability as `evidence-backed traceability`, not hidden chain-of-thought exposure.

Each consolidated finding includes:

- source document type
- page references
- linked image IDs
- confidence label and reason
- severity reasoning
- probable root cause
- missing-information flags
- conflict flags when present

## Generalization Strategy

The pipeline is intentionally built around a canonical finding schema instead of hard-coding one sample report format.

Generalization choices:

- area normalization through semantic keyword mapping
- issue-family normalization across wording variants
- document-type-agnostic evidence objects
- explicit fallback handling when thermal pages are unlabeled
- validation that prefers `Not Available` over invention

## Current Limitations

- The sample thermal document does not expose reliable area labels in extracted text, so later thermal-to-area linkage still falls back to inference when stronger visual matching is unavailable.
- PDF image extraction depends on how the source PDF embeds images. Some reports may expose placeholder assets instead of full-resolution photos.
- Live LLM stages depend on the availability of an OpenAI API key and network access.
- The system is designed to remain useful offline by falling back to deterministic logic.

## Why This Is Different

- The report is not generated directly from raw PDFs in one prompt.
- Reasoning happens after evidence extraction, normalization, and merge steps.
- Every important output artifact can be audited.
- Missing information is surfaced explicitly instead of being hallucinated away.

## Suggested Demo Narrative

For the Loom video, focus on:

1. Why you chose an evidence-first pipeline over a one-shot LLM summary
2. How traceability, confidence, and missing-data flags make the system safer
3. How the system can generalize to similar inspection-style report pairs
4. Where the next version would improve thermal-image alignment and richer OCR
