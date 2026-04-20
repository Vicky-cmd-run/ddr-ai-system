# DDR AI System

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Architecture](https://img.shields.io/badge/Architecture-Evidence--First-0F766E)](#overview)
[![Outputs](https://img.shields.io/badge/Outputs-HTML%20%7C%20PDF%20%7C%20JSON-225D52)](#what-the-system-produces)
[![LLM](https://img.shields.io/badge/LLM-OpenAI%20or%20Ollama-B7791F)](#llm-configuration)

An evidence-first pipeline for converting inspection and thermal reports into a structured, client-ready Detailed Diagnostic Report (DDR) with traceable reasoning and explainability artifacts.

## Quick Start

If you want the fastest path to a working run:

### macOS

```bash
cd /Users/viggu/Desktop/V/IIT-Ropar/FOX-Scan/ddr-ai-system
python3 -m pip install -r requirements.txt
export LLM_PROVIDER="ollama"
export OPENAI_ENABLED="true"
export OPENAI_MODEL="qwen2.5:7b"
PYTHONPATH=. python3 main.py
```

### Windows PowerShell

```powershell
cd C:\path\to\ddr-ai-system
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
$env:LLM_PROVIDER="ollama"
$env:OPENAI_ENABLED="true"
$env:OPENAI_MODEL="qwen2.5:7b"
$env:PYTHONPATH="."
python main.py
```

After the run finishes, check:

- `outputs/reports/ddr_report.html`
- `outputs/reports/ddr_report.pdf`
- `outputs/explainability/explainability.json`
- `outputs/explainability/trace_view.json`

## Overview

Most report-generation workflows fail at the same point: they optimize for fluent output before they establish reliable evidence. This project takes the opposite approach.

The DDR AI System is designed as a staged diagnostic pipeline that:

- extracts observations from raw PDFs
- grounds each finding in source evidence
- normalizes inconsistent terminology across report types
- preserves uncertainty, missing information, and document conflicts
- produces both client-facing and audit-facing outputs

The result is not just a generated report, but a reproducible reporting system that can be inspected, validated, and extended.

## Core Design Principles

- Evidence first: source documents are parsed before any summarization or composition step occurs.
- No invented facts: unsupported root causes are removed before final report generation.
- Explicit uncertainty: missing details are marked clearly instead of being guessed.
- Explainability by design: every important output can be traced back to document, page, and image references.
- Generalizable structure: the system is built around a canonical finding schema rather than one fixed sample format.

## What The System Produces

From an inspection PDF and a thermal PDF, the pipeline generates:

- a client-ready HTML DDR
- a PDF export of the DDR
- validated structured findings in JSON
- an explainability JSON artifact
- a source trace view for auditing

## End-to-End Pipeline

The workflow follows a staged architecture:

1. PDF ingestion and extraction  
   Layout-aware extraction of text, page references, and embedded images.

2. Evidence building  
   Each observation is converted into a traceable evidence object with source metadata.

3. Image placement tagging  
   Images are associated with sections, areas, and findings where possible.

4. Evidence linking  
   Document, page, and image references are attached to each finding.

5. Semantic normalization  
   Raw wording is mapped into a canonical schema so similar issues can be processed consistently.

6. Merge and deduplication  
   Related findings are merged conservatively using area-aware and content-aware keys.

7. Conflict and missing-data detection  
   Cross-document inconsistencies and missing details are surfaced explicitly.

8. Confidence scoring  
   Findings are scored based on the strength and coverage of supporting evidence.

9. Structured reasoning  
   Severity and probable root cause are assigned using grounded, explainable logic.

10. Validation  
    Unsupported root causes and incomplete fields are blocked before final composition.

11. DDR composition and export  
    The final report is generated in a client-facing form, along with explainability outputs.

## Architecture Snapshot

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

## Why This Approach Is Different

This system is intentionally not a one-shot LLM summarizer. It separates evidence extraction, reasoning, validation, and composition into distinct stages.

That design choice creates four important advantages:

- claims can be traced back to source evidence
- conflicts between reports are preserved instead of flattened away
- missing information is reported explicitly
- reasoning-heavy stages stay transparent and testable

In short, the project treats report generation as a diagnostic workflow, not just a writing task.

## Reasoning Strategy

The pipeline uses a hybrid design:

- rule-based logic for severity assessment, root-cause grounding, validation, and conflict detection
- model-assisted text refinement for semantic normalization and final DDR composition

This split is deliberate. High-risk reasoning steps stay deterministic and auditable, while language cleanup and report phrasing can benefit from a model when available.

## Generalization Strategy

The implementation is designed to work beyond a single pair of sample reports.

Generalization is supported through:

- canonical area normalization
- issue-family normalization across wording variants
- document-type-agnostic evidence objects
- conservative merge logic that avoids collapsing unrelated observations
- fallback handling when areas are unlabeled or only partially recoverable
- validation rules that prefer `Not Available` over speculation

## Inputs

Expected raw inputs:

- `data/raw/inspection.pdf`
- `data/raw/thermal.pdf`

## Outputs

Generated artifacts:

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

## Local Setup

Install dependencies in your preferred Python environment:

```bash
pip install -r requirements.txt
```

### macOS Tutorial

1. Open Terminal.
2. Move into the project folder:

```bash
cd /Users/viggu/Desktop/V/IIT-Ropar/FOX-Scan/ddr-ai-system
```

3. Install dependencies:

```bash
python3 -m pip install -r requirements.txt
```

4. Run the pipeline:

```bash
PYTHONPATH=. python3 main.py
```

If you want to use the bundled runtime already available in this workspace:

```bash
cd /Users/viggu/Desktop/V/IIT-Ropar/FOX-Scan/ddr-ai-system
PYTHONPATH=. /Users/viggu/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 main.py
```

### Windows Tutorial

1. Open PowerShell.
2. Move into the project folder:

```powershell
cd C:\path\to\ddr-ai-system
```

3. Create and activate a virtual environment:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

4. Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

5. Run the pipeline:

```powershell
$env:PYTHONPATH="."
python main.py
```

If PowerShell blocks script activation, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

## LLM Configuration

The pipeline can optionally use an LLM for:

- semantic normalization
- final client-facing DDR composition

All structured reasoning remains outside the model path.

### Option 1: OpenAI

#### macOS

```bash
export LLM_PROVIDER="openai"
export OPENAI_API_KEY="your_key_here"
export OPENAI_MODEL="gpt-4o-mini"
export OPENAI_ENABLED="true"
export OPENAI_REASONING_EFFORT="medium"
```

#### Windows PowerShell

```powershell
$env:LLM_PROVIDER="openai"
$env:OPENAI_API_KEY="your_key_here"
$env:OPENAI_MODEL="gpt-4o-mini"
$env:OPENAI_ENABLED="true"
$env:OPENAI_REASONING_EFFORT="medium"
```

Notes:

- the code uses the OpenAI Responses API pattern
- if the `openai` SDK is unavailable, the client falls back to direct HTTP calls
- never commit API keys into the repository

### Option 2: Free Local Ollama

#### macOS

```bash
brew install ollama
ollama serve
ollama pull qwen2.5:7b

export LLM_PROVIDER="ollama"
export OPENAI_ENABLED="true"
export OPENAI_MODEL="qwen2.5:7b"
export OLLAMA_BASE_URL="http://127.0.0.1:11434"
```

#### Windows

1. Install Ollama from the official installer.
2. Start Ollama.
3. Pull the model:

```powershell
ollama pull qwen2.5:7b
```

4. Set environment variables in PowerShell:

```powershell
$env:LLM_PROVIDER="ollama"
$env:OPENAI_ENABLED="true"
$env:OPENAI_MODEL="qwen2.5:7b"
$env:OLLAMA_BASE_URL="http://127.0.0.1:11434"
```

Notes:

- Ollama allows the normalization and composition stages to run locally without API quota
- the rule-based reasoning, validation, and conflict logic remain unchanged
- `.env.example` is included as a local configuration template

## Explainability Model

Explainability in this project means evidence-backed traceability, not hidden chain-of-thought exposure.

Each consolidated finding can carry:

- source document type
- page references
- linked image references
- evidence text
- confidence label and explanation
- severity assessment
- probable root cause status
- missing-information flags
- conflict flags

This makes the system suitable not only for generating a report, but also for reviewing how that report was assembled.

## Current Limitations

- thermal PDFs may not always expose reliable area labels in extracted text, so some cross-document mapping still depends on inference
- image extraction quality depends on how the source PDF embeds or compresses image assets
- local or hosted LLM output quality depends on model availability and runtime conditions
- the current conflict rules are practical and transparent, but they are still heuristic rather than fully spatial

## Next Improvements

If extended further, the most valuable improvements would be:

- stronger OCR and layout recovery for noisy reports
- richer thermal-to-inspection spatial alignment
- broader evaluation datasets with expected DDR outputs
- configurable report templates for different building and inspection contexts
- more domain-specific conflict and severity rules

## Repository Notes

- generated artifacts under `data/extracted`, `data/processed`, and `outputs` are ignored by Git
- secrets must be supplied through environment variables
- `.env.example` is included for local setup, but real credentials must never be committed

## Summary

The DDR AI System is built as a reliable reporting pipeline rather than a single prompt wrapped around PDFs. Its main value is the combination of structured evidence handling, explicit uncertainty, grounded reasoning, and client-ready output generation.

That makes it useful not only as a report generator, but as a defensible and extensible foundation for similar multi-document diagnostic workflows.
