from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from atlas_ros.contracts.release import ReleaseSpecification
from tools.release.release_compiler import (
    ReleaseCompilationError,
    compile_release,
    load_release_specification,
)


def values(version: str = "7.1.0") -> dict[str, object]:
    return {
        "package_name": "atlas-ros",
        "identity": {
            "version": version,
            "source_commit": "a" * 40,
            "tag": f"v{version}",
        },
        "authority_model_version": "7.0",
        "release_scope": (
            "Drive retirement readiness",
            "governed historical cleanup",
            "version-neutral release compiler",
            "legacy isolation",
            "verified lazy loading",
        ),
        "immediate_rollback": {
            "version": "6.5.0",
            "source_commit": "b" * 40,
            "tag": "v6.5.0",
        },
        "historical_rollbacks": (
            {
                "version": "6.2.0",
                "source_commit": "c" * 40,
                "tag": "v6.2.0",
            },
        ),
        "required_integrations": ("GitHub", "Notion", "Todoist"),
        "optional_integrations": ("Google Drive",),
        "validation_profile": ("ruff", "mypy", "pytest", "restoration"),
        "artifact_requirements": ("sdist", "wheel", "checksums", "SBOM"),
        "promotion_prerequisites": (
            "build-once artifacts",
            "independent post-publication readback",
            "rollback restoration",
        ),
        "publication_policy": ("separate exact authorization", "immutable tag"),
        "authority_activation_policy": (
            "publication readback must pass",
            "transactional GitHub and Notion activation",
        ),
        "restoration_requirements": ("v7.0.1", "v6.5.0", "v6.2.0"),
        "migration_requirements": ("legacy compatibility fixtures",),
        "compatibility_rules": (
            "preserve v7.0.1 behavior",
            "deprecated wrappers contain no independent policy",
        ),
        "notion_system_state_url": "https://app.notion.com/p/system-state",
        "integration_inventory_url": "https://app.notion.com/p/integrations",
        "integration_inventory_data_source": (
            "collection://46af021f-eb9a-4eba-b10c-4523e70df0c3"
        ),
        "candidate_only": True,
    }


def specification(version: str = "7.1.0") -> ReleaseSpecification:
    return ReleaseSpecification.create(**values(version))


def test_compiler_is_deterministic_and_candidate_only(tmp_path: Path) -> None:
    compiled_at = datetime(2026, 7, 28, tzinfo=UTC)
    first = compile_release(specification(), compiled_at=compiled_at)
    second = compile_release(specification(), compiled_at=compiled_at)

    assert first.files == second.files
    assert first.receipt == second.receipt
    assert first.receipt.production_authorized is False
    assert first.receipt.published is False
    assert first.receipt.authority_activated is False
    assert first.receipt.provider_writes == 0
    assert "release/RELEASE_MANIFEST_V710.md" in first.files
    assert '"status": "Candidate"' in first.files["governance/AUTHORITY_CANDIDATE.json"]
    assert (
        "Integration Inventory data source: "
        "collection://46af021f-eb9a-4eba-b10c-4523e70df0c3"
        in first.files["release/RELEASE_MANIFEST_V710.md"]
    )
    assert (
        '"integration_inventory_data_source": '
        '"collection://46af021f-eb9a-4eba-b10c-4523e70df0c3"'
        in first.files["governance/AUTHORITY_CANDIDATE.json"]
    )
    assert "Production status: not authorized" in first.files[
        "governance/RELEASE_INDEX_CANDIDATE.md"
    ]

    written = first.write(tmp_path)
    assert len(written) == len(first.files)
    assert (tmp_path / "CHECKSUMS.sha256").is_file()


def test_compiler_supports_corrective_minor_and_major_fixtures() -> None:
    for version in ("7.1.1", "7.2.0", "8.0.0"):
        compiled = compile_release(specification(version))
        assert compiled.receipt.release_version == version
        assert f"RELEASE_MANIFEST_V{version.replace('.', '')}.md" in "\n".join(
            compiled.files
        )


def test_specification_rejects_drive_as_required() -> None:
    raw = values()
    raw["required_integrations"] = ("GitHub", "Notion", "Todoist", "Google Drive")
    raw["optional_integrations"] = ()

    with pytest.raises(ValueError, match="Google Drive"):
        ReleaseSpecification.create(**raw)


def test_loader_rejects_mutable_source_identity(tmp_path: Path) -> None:
    path = tmp_path / "spec.yaml"
    path.write_text(
        "package_name: atlas-ros\n"
        "identity:\n"
        "  version: 7.1.0\n"
        "  source_commit: main\n"
        "  tag: v7.1.0\n",
        encoding="utf-8",
    )

    with pytest.raises(ReleaseCompilationError):
        load_release_specification(path)


def test_repository_release_fixtures_compile_deterministically() -> None:
    fixtures = Path("tests/fixtures/release-specs")
    receipts = []
    for path in sorted(fixtures.glob("*.yaml")):
        specification = load_release_specification(path)
        first = compile_release(specification)
        second = compile_release(specification)
        assert first.files == second.files
        assert first.receipt == second.receipt
        receipts.append(first.receipt.release_version)
    assert receipts == ["7.0.2", "8.0.0", "7.2.0"]


def test_template_spec_requires_exact_source_commit_override(tmp_path: Path) -> None:
    source = Path("release/specifications/V710.yaml")
    with pytest.raises(ReleaseCompilationError, match="unbound"):
        load_release_specification(source)
    specification = load_release_specification(source, source_commit="d" * 40)
    assert specification.identity.source_commit == "d" * 40
    with pytest.raises(ReleaseCompilationError, match="disagrees"):
        exact = tmp_path / "exact.yaml"
        exact.write_text(source.read_text().replace("__SOURCE_COMMIT__", "e" * 40))
        load_release_specification(exact, source_commit="f" * 40)


def test_v711_repository_template_compiles_with_direct_inventory_reference() -> None:
    source = Path("release/specifications/V711.yaml")
    specification = load_release_specification(source, source_commit="1" * 40)
    compiled = compile_release(specification)

    manifest = compiled.files["release/RELEASE_MANIFEST_V711.md"]
    assert specification.identity.version == "7.1.1"
    assert specification.immediate_rollback.version == "7.1.0"
    assert (
        "Integration Inventory data source: "
        "collection://46af021f-eb9a-4eba-b10c-4523e70df0c3"
        in manifest
    )
