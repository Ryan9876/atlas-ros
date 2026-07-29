#!/usr/bin/env python3
"""Fail closed if the v7.4.5 candidate implements an explicitly excluded feature."""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCAN_ROOTS = [ROOT / "src" / "atlas_ros" / "runtime_performance"]
PROHIBITED_TOKENS = {
    "asyncio": "async runtime conversion",
    "ThreadPoolExecutor": "bounded runtime concurrency",
    "ProcessPoolExecutor": "bounded runtime concurrency",
    "multiprocessing": "parallel operational computation",
    "create_task(": "concurrent capability execution",
    "gather(": "concurrent provider reads",
    "resident daemon": "resident warm session",
    "authorization_cache": "authorization retention",
    "pipeline_stage_digest_v2": "pipeline digest semantic change",
}


def main() -> None:
    findings: list[str] = []
    for root in SCAN_ROOTS:
        for path in sorted(root.rglob("*.py")):
            text = path.read_text(encoding="utf-8")
            for token, description in PROHIBITED_TOKENS.items():
                if token in text:
                    findings.append(f"{path.relative_to(ROOT)}: {description} ({token})")
    if findings:
        raise SystemExit("v7.4.5 exclusion validation failed:\n" + "\n".join(findings))
    print("v7.4.5 exclusions validated: no concurrency, resident session, or digest change")


if __name__ == "__main__":
    main()
