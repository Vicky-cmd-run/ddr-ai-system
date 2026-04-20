from __future__ import annotations

import json

from src.pipeline import DDRPipeline


def main() -> None:
    pipeline = DDRPipeline()
    summary = pipeline.run()
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
