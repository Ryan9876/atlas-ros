"""CLI for deterministic non-publishing release compilation."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(_REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPOSITORY_ROOT))


def main() -> None:
    from tools.release.release_compiler import (
        compile_release,
        load_release_specification,
    )

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
