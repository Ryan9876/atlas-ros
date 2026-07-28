"""CLI for deterministic non-publishing release compilation."""

from __future__ import annotations

import argparse
from pathlib import Path

from tools.release.release_compiler import compile_release, load_release_specification


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("specification", type=Path)
    parser.add_argument("output", type=Path, nargs="?")
    parser.add_argument("--output", dest="output_option", type=Path)
    parser.add_argument("--source-commit")
    args = parser.parse_args()
    output = args.output_option or args.output
    if output is None:
        parser.error("an output directory is required")
    compiled = compile_release(
        load_release_specification(
            args.specification, source_commit=args.source_commit
        )
    )
    compiled.write(output)
    print(compiled.receipt.output_digest)


if __name__ == "__main__":
    main()
