#!/usr/bin/env python3
"""Assemble the non-publishing Atlas ROS v7.1.0 final package and staged authority."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import traceback
from datetime import datetime
from pathlib import Path

_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(_REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPOSITORY_ROOT))

VERSION = "7.1.0"
MANIFEST_PATH = Path("release/RELEASE_MANIFEST_V710.md")
V701_COMMIT = "f26f5154ea6cd4b431c5a2638c439d7de9282761"
V650_COMMIT = "bb6d6fea70d6824c9bc6a42e63ba36cc88029260"
V620_COMMIT = "863d5ddf9ebd4723200166cf31c7acd93ebec54f"
SYSTEM_STATE_URL = "https://app.notion.com/p/3a0b8344ad2c81d1b545d0266b7cd809"


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def assemble(
    *,
    repository_root: Path,
    package_root: Path,
    source_commit: str,
    source_timestamp: str,
    installed_packages_path: Path,
) -> dict[str, object]:
    from atlas_ros.contracts.digests import sha256_digest
    from tools.release.authority_compiler import (
        ActiveReleaseSpec,
        AuthorityCompilationSpec,
        RollbackReleaseSpec,
        compile_authority,
    )

    datetime.fromisoformat(source_timestamp.replace("Z", "+00:00"))
    manifest = repository_root / MANIFEST_PATH
    source = package_root / f"atlas_ros-{VERSION}.tar.gz"
    wheel = package_root / f"atlas_ros-{VERSION}-py3-none-any.whl"
    source_tree = package_root / "SOURCE_TREE.txt"
    compiler_receipt_path = (
        package_root / "compiler-output/evidence/RELEASE_COMPILATION_RECEIPT.json"
    )
    manifest_receipt_path = package_root / "PRODUCTION_MANIFEST_VALIDATION.json"

    for path in (
        manifest,
        source,
        wheel,
        source_tree,
        compiler_receipt_path,
        manifest_receipt_path,
        installed_packages_path,
    ):
        if not path.is_file():
            raise ValueError(f"required final-package input is missing: {path}")

    manifest_text = manifest.read_text(encoding="utf-8")
    manifest_raw_sha = file_digest(manifest)
    manifest_canonical_sha = sha256_digest(manifest_text)
    source_sha = file_digest(source)
    wheel_sha = file_digest(wheel)
    source_tree_sha = file_digest(source_tree)
    compiler_receipt = json.loads(compiler_receipt_path.read_text(encoding="utf-8"))
    manifest_receipt = json.loads(manifest_receipt_path.read_text(encoding="utf-8"))
    installed_packages = json.loads(installed_packages_path.read_text(encoding="utf-8"))

    if manifest_receipt["manifest_canonical_sha256"] != manifest_canonical_sha:
        raise ValueError("production manifest digest changed after validation")
    if compiler_receipt["source_commit"] != source_commit:
        raise ValueError("compiler receipt does not bind the exact source commit")

    source_manifest = {
        "schema_version": "1.0",
        "package_name": "atlas-ros",
        "release_version": VERSION,
        "source_commit": source_commit,
        "source_timestamp": source_timestamp,
        "source_tree_sha256": source_tree_sha,
        "sdist_file": source.name,
        "sdist_sha256": source_sha,
        "wheel_file": wheel.name,
        "wheel_sha256": wheel_sha,
        "immutable_manifest_path": MANIFEST_PATH.as_posix(),
        "immutable_manifest_raw_sha256": manifest_raw_sha,
        "immutable_manifest_canonical_sha256": manifest_canonical_sha,
        "compiler_receipt": "compiler-output/evidence/RELEASE_COMPILATION_RECEIPT.json",
        "compiler_output_digest": compiler_receipt["output_digest"],
        "compiler_specification_digest": compiler_receipt["specification_digest"],
        "provider_writes": 0,
        "destructive_actions": 0,
        "production_authorized": False,
        "published": False,
        "authority_activated": False,
    }
    source_manifest_path = package_root / "SOURCE_MANIFEST_FINAL.json"
    write_json(source_manifest_path, source_manifest)

    spdx_packages = []
    for index, package in enumerate(
        sorted(installed_packages, key=lambda item: item["name"].lower()), start=1
    ):
        spdx_packages.append(
            {
                "SPDXID": f"SPDXRef-Package-{index}",
                "name": package["name"],
                "versionInfo": package["version"],
                "downloadLocation": "NOASSERTION",
                "filesAnalyzed": False,
                "licenseConcluded": "NOASSERTION",
                "licenseDeclared": "NOASSERTION",
                "copyrightText": "NOASSERTION",
            }
        )
    sbom = {
        "spdxVersion": "SPDX-2.3",
        "dataLicense": "CC0-1.0",
        "SPDXID": "SPDXRef-DOCUMENT",
        "name": f"atlas-ros-{VERSION}",
        "documentNamespace": (
            "https://github.com/Ryan9876/atlas-ros/releases/final-package/"
            + source_commit
        ),
        "creationInfo": {
            "created": source_timestamp,
            "creators": ["Tool: Atlas ROS version-neutral final-package assembler"],
        },
        "packages": spdx_packages,
    }
    sbom_path = package_root / "SBOM.spdx.json"
    write_json(sbom_path, sbom)

    authority = compile_authority(
        AuthorityCompilationSpec(
            active=ActiveReleaseSpec(
                version=VERSION,
                immutable_commit=source_commit,
                tag="v7.1.0",
                manifest_path=MANIFEST_PATH.as_posix(),
                manifest_url=(
                    f"https://github.com/Ryan9876/atlas-ros/blob/{source_commit}/"
                    f"{MANIFEST_PATH.as_posix()}"
                ),
                manifest_sha256=manifest_canonical_sha,
                release_url="https://github.com/Ryan9876/atlas-ros/releases/tag/v7.1.0",
                source_sha256=source_sha,
                wheel_sha256=wheel_sha,
            ),
            rollback=RollbackReleaseSpec(
                version="7.0.1",
                immutable_commit=V701_COMMIT,
                tag="v7.0.1",
                release_url="https://github.com/Ryan9876/atlas-ros/releases/tag/v7.0.1",
            ),
            historical_rollbacks=(
                RollbackReleaseSpec(
                    version="6.5.0",
                    immutable_commit=V650_COMMIT,
                    tag="v6.5.0",
                    release_url="https://github.com/Ryan9876/atlas-ros/releases/tag/v6.5.0",
                ),
                RollbackReleaseSpec(
                    version="6.2.0",
                    immutable_commit=V620_COMMIT,
                    tag="v6.2.0",
                    release_url="https://github.com/Ryan9876/atlas-ros/releases/tag/v6.2.0",
                ),
            ),
            notion_system_state_url=SYSTEM_STATE_URL,
            last_promotion_transaction_id=("v710-promotion-pending-" + source_commit[:12]),
            last_verified_at=source_timestamp,
        )
    )
    staged = package_root / "staged-authority"
    staged.mkdir(parents=True, exist_ok=True)
    (staged / "AUTHORITY.json").write_text(authority.authority_json, encoding="utf-8")
    (staged / "RELEASE_INDEX.md").write_text(
        authority.release_index_markdown, encoding="utf-8"
    )

    final_identity = {
        "schema_version": "1.0",
        "status": "final_package_validated_not_authorized",
        "release_version": VERSION,
        "source_commit": source_commit,
        "source_sha256": source_sha,
        "wheel_sha256": wheel_sha,
        "manifest_path": MANIFEST_PATH.as_posix(),
        "manifest_raw_sha256": manifest_raw_sha,
        "manifest_canonical_sha256": manifest_canonical_sha,
        "sbom_sha256": file_digest(sbom_path),
        "source_manifest_sha256": file_digest(source_manifest_path),
        "compiler_output_digest": compiler_receipt["output_digest"],
        "compiler_specification_digest": compiler_receipt["specification_digest"],
        "staged_authority_sha256": authority.authority_sha256,
        "staged_release_index_sha256": authority.release_index_sha256,
        "active_production_release": "7.0.1",
        "immediate_rollback_after_promotion": "7.0.1",
        "historical_rollbacks": ["6.5.0", "6.2.0"],
        "required_integrations": ["GitHub", "Notion", "Todoist"],
        "optional_integrations": ["Google Drive"],
        "provider_writes": 0,
        "destructive_actions": 0,
        "production_authorized": False,
        "published": False,
        "authority_activated": False,
    }
    write_json(package_root / "FINAL_PACKAGE_IDENTITY.json", final_identity)
    write_json(
        package_root / "PROMOTION_INPUTS.json",
        {
            "schema_version": "1.0",
            "status": "awaiting_exact_package_authorization",
            "tag": "v7.1.0",
            **final_identity,
        },
    )
    return final_identity


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repository-root", type=Path, default=Path("."))
    parser.add_argument("--package-root", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--source-timestamp", required=True)
    parser.add_argument("--installed-packages", type=Path, required=True)
    args = parser.parse_args()

    package_root = args.package_root.resolve()
    try:
        identity = assemble(
            repository_root=args.repository_root.resolve(),
            package_root=package_root,
            source_commit=args.source_commit,
            source_timestamp=args.source_timestamp,
            installed_packages_path=args.installed_packages.resolve(),
        )
    except Exception:
        package_root.mkdir(parents=True, exist_ok=True)
        (package_root / "FINALIZATION_ERROR.txt").write_text(
            traceback.format_exc(), encoding="utf-8"
        )
        raise
    print(json.dumps(identity, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
