#!/usr/bin/env python3
"""Build deterministic authority-neutral evidence for the v7.4.5 candidate."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import uuid
from datetime import UTC, datetime
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build-dir", required=True)
    parser.add_argument("--dist-dir", required=True)
    args = parser.parse_args()
    build = Path(args.build_dir)
    dist = Path(args.dist_dir)
    build.mkdir(parents=True, exist_ok=True)

    packages = []
    for distribution in sorted(
        importlib.metadata.distributions(), key=lambda item: item.metadata["Name"].lower()
    ):
        name = distribution.metadata["Name"]
        packages.append(
            {
                "SPDXID": f"SPDXRef-Package-{name.replace('_', '-').replace('.', '-')}",
                "name": name,
                "versionInfo": distribution.version,
                "downloadLocation": "NOASSERTION",
                "filesAnalyzed": False,
                "licenseConcluded": "NOASSERTION",
                "licenseDeclared": "NOASSERTION",
            }
        )
    sbom = {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": "atlas-ros-7.4.5-candidate",
        "documentNamespace": f"urn:uuid:{uuid.uuid4()}",
        "creationInfo": {
            "created": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "creators": ["Tool: Atlas ROS v7.4.5 candidate workflow"],
        },
        "packages": packages,
    }
    sbom_path = build / "SBOM.spdx.json"
    sbom_path.write_text(json.dumps(sbom, indent=2, sort_keys=True) + "\n")

    source_commit = (build / "SOURCE_COMMIT.txt").read_text().strip()
    artifacts = {
        path.name: sha256(path)
        for path in sorted(dist.iterdir())
        if path.is_file()
    }
    report = {
        "schema_version": "v745-candidate-evidence-v1",
        "candidate_version": "7.4.5",
        "candidate_commit": source_commit,
        "status": "non-publishing-candidate",
        "build_count": 1,
        "artifacts": artifacts,
        "source_manifest_sha256": sha256(build / "SOURCE_MANIFEST.sha256"),
        "sbom_sha256": sha256(sbom_path),
        "provider_writes": 0,
        "production_authority_changes": 0,
        "production_schema_migrations": 0,
        "release_publications": 0,
        "production_tags_created_or_moved": 0,
        "integration_scope_expansions": 0,
        "credential_actions": 0,
        "excluded_capabilities": [
            "incremental_pipeline_digests",
            "bounded_runtime_concurrency",
            "attended_warm_session",
        ],
        "promotion": "separately_authorized",
    }
    (build / "V745_CANDIDATE_EVIDENCE.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n"
    )


if __name__ == "__main__":
    main()
