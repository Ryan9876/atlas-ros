from __future__ import annotations

import json
from dataclasses import replace

import pytest

from atlas_ros.kernel.authority import canonical_authority_payload
from atlas_ros.kernel.bootstrap import render_release_index
from atlas_ros.kernel.digests import sha256_digest
from tools.release.authority_compiler import (
    ActiveReleaseSpec,
    AuthorityCompilationError,
    AuthorityCompilationSpec,
    RollbackReleaseSpec,
    compile_authority,
)


def compilation_spec() -> AuthorityCompilationSpec:
    active_commit = "a" * 40
    manifest_path = "release/RELEASE_MANIFEST_V701.md"
    return AuthorityCompilationSpec(
        active=ActiveReleaseSpec(
            version="7.0.1",
            immutable_commit=active_commit,
            tag="v7.0.1",
            manifest_path=manifest_path,
            manifest_url=(
                f"https://github.com/Ryan9876/atlas-ros/blob/{active_commit}/"
                f"{manifest_path}"
            ),
            manifest_sha256="f" * 64,
            release_url="https://github.com/Ryan9876/atlas-ros/releases/tag/v7.0.1",
            source_sha256="b" * 64,
            wheel_sha256="c" * 64,
        ),
        rollback=RollbackReleaseSpec(
            version="6.5.0",
            immutable_commit="d" * 40,
            tag="v6.5.0",
            release_url="https://github.com/Ryan9876/atlas-ros/releases/tag/v6.5.0",
        ),
        historical_rollbacks=(
            RollbackReleaseSpec(
                version="6.2.0",
                immutable_commit="e" * 40,
                tag="v6.2.0",
                release_url="https://github.com/Ryan9876/atlas-ros/releases/tag/v6.2.0",
            ),
        ),
        notion_system_state_url="https://app.notion.com/p/3a0b8344ad2c81d1b545d0266b7cd809",
        last_promotion_transaction_id="promotion-v7.0.1-001",
        last_verified_at="2026-07-28T19:00:00Z",
    )


def test_compile_authority_binds_json_index_manifest_and_integrity() -> None:
    compiled = compile_authority(compilation_spec())
    raw = json.loads(compiled.authority_json)

    assert raw["active_release"]["version"] == "7.0.1"
    assert raw["active_release"]["manifest_path"] == "release/RELEASE_MANIFEST_V701.md"
    assert raw["active_release"]["manifest_sha256"] == "f" * 64
    assert raw["immediate_rollback"]["version"] == "6.5.0"
    assert raw["historical_rollbacks"][0]["version"] == "6.2.0"
    assert compiled.release_index_markdown == render_release_index(compiled.record)
    assert compiled.release_index_sha256 == sha256_digest(compiled.release_index_markdown)
    assert compiled.authority_sha256 == sha256_digest(compiled.authority_json)

    payload = compiled.record.model_dump(
        mode="json",
        exclude={"integrity"},
        exclude_defaults=True,
    )
    assert compiled.record.integrity.content_sha256 == sha256_digest(
        canonical_authority_payload(payload)
    )


def test_compile_authority_accepts_future_minor_release() -> None:
    spec = compilation_spec()
    compiled = compile_authority(
        replace(
            spec,
            active=replace(
                spec.active,
                version="7.1.0",
                tag="v7.1.0",
                manifest_path="release/RELEASE_MANIFEST_V710.md",
                manifest_url=(
                    "https://github.com/Ryan9876/atlas-ros/blob/"
                    + "a" * 40
                    + "/release/RELEASE_MANIFEST_V710.md"
                ),
            ),
        )
    )

    assert compiled.record.active_release.version == "7.1.0"


def test_compile_authority_rejects_non_semantic_release() -> None:
    spec = compilation_spec()
    invalid = replace(spec, active=replace(spec.active, version="7.1", tag="v7.1"))

    with pytest.raises(AuthorityCompilationError, match="semantic versioning"):
        compile_authority(invalid)


def test_compile_authority_rejects_mutable_manifest_path() -> None:
    spec = compilation_spec()
    invalid = replace(
        spec,
        active=replace(
            spec.active,
            manifest_path="release/RELEASE_MANIFEST.md",
            manifest_url=(
                "https://github.com/Ryan9876/atlas-ros/blob/"
                + "a" * 40
                + "/release/RELEASE_MANIFEST.md"
            ),
        ),
    )

    with pytest.raises(AuthorityCompilationError, match="versioned immutable"):
        compile_authority(invalid)


def test_compile_authority_rejects_inconsistent_rollback_identity() -> None:
    spec = compilation_spec()
    invalid = replace(
        spec,
        rollback=replace(spec.rollback, version="6.2.0", tag="v6.5.0"),
    )

    with pytest.raises(AuthorityCompilationError, match="rollback"):
        compile_authority(invalid)


def test_compile_authority_rejects_unbound_manifest_url() -> None:
    spec = compilation_spec()
    invalid = replace(
        spec,
        active=replace(
            spec.active,
            manifest_url=(
                "https://github.com/Ryan9876/atlas-ros/blob/main/"
                "release/RELEASE_MANIFEST_V701.md"
            ),
        ),
    )

    with pytest.raises(AuthorityCompilationError, match="exact active commit"):
        compile_authority(invalid)


def test_compile_authority_requires_timezone_and_transaction() -> None:
    spec = compilation_spec()

    with pytest.raises(AuthorityCompilationError, match="transaction ID"):
        compile_authority(replace(spec, last_promotion_transaction_id=" "))
    with pytest.raises(AuthorityCompilationError, match="timezone"):
        compile_authority(replace(spec, last_verified_at="2026-07-28T19:00:00"))
