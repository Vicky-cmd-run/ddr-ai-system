# DDR AI Demo

This folder contains a static demo site for the DDR AI System.

## Deploy on Vercel

1. Import the repository into Vercel.
2. Set the project root directory to `demo`.
3. Keep the framework preset as `Other`.
4. Deploy.

## What the demo shows

- live pipeline replay of the 11-stage DDR workflow
- interactive findings explorer
- grounded evidence and conflict examples
- explainability and artifact summary

The site is static and reads from `demo/data/demo-report.json`, so it does not require Python, OpenAI, or Ollama at deploy time.
