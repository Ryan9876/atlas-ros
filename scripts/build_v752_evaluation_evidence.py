from __future__ import annotations

import argparse
from pathlib import Path

from atlas_ros.clarification_baseline_v752 import write_evaluation_evidence


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build deterministic provider-write-free v7.5.2 evaluation evidence."
    )
    parser.add_argument("--fixtures", type=Path, required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    arguments = parser.parse_args()
    for path in write_evaluation_evidence(
        fixture_path=arguments.fixtures,
        output_directory=arguments.output_directory,
    ):
        print(path)


if __name__ == "__main__":
    main()
