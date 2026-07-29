#!/usr/bin/env python3
"""Compile the deterministic v7.4.5 verified runtime registry bundle."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

from atlas_ros.runtime_performance.services import RuntimeBundleBuilder


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default="src/atlas_ros/data/runtime_performance/verified_runtime_bundle.json",
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    source_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=root, text=True
    ).strip()
    source_paths = {
        "architecture": root / "governance" / "architecture.yaml",
        "authority-policy": root / "governance" / "ATLAS_PROJECT_INITIALIZATION.md",
        "feature-contract": root
        / "devtools"
        / "feature_delivery"
        / "contracts"
        / "v745-runtime-performance-foundation.yaml",
        "runtime-contracts": root
        / "src"
        / "atlas_ros"
        / "runtime_performance"
        / "contracts.py",
        "runtime-services": root
        / "src"
        / "atlas_ros"
        / "runtime_performance"
        / "services.py",
    }
    source_digests = {name: sha256(path) for name, path in source_paths.items()}
    builder = RuntimeBundleBuilder(
        architecture_identity=source_digests["architecture"],
        source_commit=source_commit,
        package_version="7.4.5",
        compiler_versions={"runtime-bundle-builder": "1"},
    )
    bundle = builder.build(
        policies={
            "authority-resolution": source_digests["authority-policy"],
            "runtime-performance": source_digests["feature-contract"],
        },
        contracts={
            "runtime-performance-contracts": source_digests["runtime-contracts"],
        },
        capabilities={
            "operation-read-snapshot": "v1",
            "provider-read-planning": "v1",
            "verified-runtime-bundle": "v1",
            "performance-governance": "v1",
            "capability-scoped-composition": "v1",
            "incremental-operational-computation": "v1",
        },
        schemas={
            "feature-contract": source_digests["feature-contract"],
            "architecture": source_digests["architecture"],
        },
        command_bindings={
            "status": "operational-awareness",
            "brief": "operating-brief",
            "context": "execution-context-pack",
        },
        dependencies={
            "operational-awareness": ("operation-read-snapshot", "provider-read-planning"),
            "operating-brief": (
                "operation-read-snapshot",
                "provider-read-planning",
                "incremental-operational-computation",
            ),
            "execution-context-pack": (
                "operation-read-snapshot",
                "provider-read-planning",
                "incremental-operational-computation",
            ),
        },
        source_file_digests=source_digests,
    )
    output = root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(bundle.model_dump_json(indent=2) + "\n", encoding="utf-8")
    loaded = json.loads(output.read_text(encoding="utf-8"))
    assert loaded["source_commit"] == source_commit
    assert loaded["package_version"] == "7.4.5"
    print(output)


if __name__ == "__main__":
    main()
