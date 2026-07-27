from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.validate_v700_exact_artifact import (
    ExactArtifactValidationError,
    validate_exact_artifact,
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def build_artifact(root: Path, candidate_sha: str, run_id: str) -> Path:
    source = root / "atlas_ros-7.0.0rc1.tar.gz"
    wheel = root / "atlas_ros-7.0.0rc1-py3-none-any.whl"
    source.write_bytes(b"source archive")
    wheel.write_bytes(b"wheel archive")
    evidence = root / "evidence"
    write_json(
        evidence / "FINAL_IDENTITY_CANDIDATE.json",
        {
            "release_version": "7.0.0rc1",
            "candidate_commit": candidate_sha,
            "workflow_run_id": run_id,
            "source": {"name": source.name, "sha256": sha(source)},
            "wheel": {"name": wheel.name, "sha256": sha(wheel)},
            "provider_writes": 0,
            "promotion_authorized": False,
        },
    )
    write_json(
        evidence / "V700_CANDIDATE_STATUS.json",
        {
            "candidate_sha": candidate_sha,
            "active_production_restored": True,
            "immediate_rollback_restored": True,
            "provider_writes": 0,
            "production_promotion_authorized": False,
            "final_tag_created": False,
            "final_release_published": False,
            "authority_activated": False,
            "drive_retired": False,
        },
    )
    evidence_files = sorted(path for path in evidence.iterdir() if path.is_file())
    (evidence / "EVIDENCE_CHECKSUMS.sha256").write_text(
        "".join(f"{sha(path)}  {path.name}\n" for path in evidence_files),
        encoding="utf-8",
    )
    publication_files = [source, wheel, evidence / "EVIDENCE_CHECKSUMS.sha256"]
    (root / "PUBLICATION_CHECKSUMS.sha256").write_text(
        "".join(
            f"{sha(path)}  {path.relative_to(root).as_posix()}\n"
            for path in publication_files
        ),
        encoding="utf-8",
    )
    return root


def performance(path: Path) -> Path:
    write_json(
        path,
        {
            "status": "passed",
            "provider_writes": 0,
            "candidate": {"p95_ms": 10.0},
            "baseline": {"p95_ms": 10.5},
        },
    )
    return path


def integrations(path: Path) -> Path:
    write_json(
        path,
        {
            "required_v7_integrations": [
                {
                    "name": name,
                    "connection_status": "connected",
                    "approval_status": "approved",
                    "acceptance_status": "passed",
                    "current": True,
                    "least_privilege_verified": True,
                }
                for name in ("GitHub", "Notion", "Todoist")
            ]
        },
    )
    return path


def test_exact_artifact_passes_with_drive_and_live_readback_findings(tmp_path: Path) -> None:
    candidate_sha = "a" * 40
    root = build_artifact(tmp_path / "artifact", candidate_sha, "42")

    result = validate_exact_artifact(
        artifact_root=root,
        candidate_sha=candidate_sha,
        artifact_id="123",
        artifact_digest="b" * 64,
        candidate_run_id="42",
        standard_ci_run_id="43",
        architecture_run_id="44",
        performance_path=performance(tmp_path / "performance.json"),
        integration_snapshot_path=integrations(tmp_path / "integrations.json"),
        drive_inventory_path=None,
        output_dir=tmp_path / "output",
    )

    assert result["status"] == "passed_with_findings"
    assert result["rollback_simulation"]["status"] == "ready"
    assert result["promotion_simulation"]["status"] == "blocked"
    assert "Drive migration ledger has not passed" in result["findings"]
    assert result["provider_writes"] == 0
    assert (tmp_path / "output/EXACT_ARTIFACT_VALIDATION.json").is_file()


def test_exact_artifact_rejects_tampered_nested_evidence(tmp_path: Path) -> None:
    candidate_sha = "a" * 40
    root = build_artifact(tmp_path / "artifact", candidate_sha, "42")
    status = root / "evidence/V700_CANDIDATE_STATUS.json"
    status.write_text("{}\n", encoding="utf-8")

    with pytest.raises(ExactArtifactValidationError, match="checksum mismatch"):
        validate_exact_artifact(
            artifact_root=root,
            candidate_sha=candidate_sha,
            artifact_id="123",
            artifact_digest="b" * 64,
            candidate_run_id="42",
            standard_ci_run_id="43",
            architecture_run_id="44",
            performance_path=performance(tmp_path / "performance.json"),
            integration_snapshot_path=integrations(tmp_path / "integrations.json"),
            drive_inventory_path=None,
            output_dir=tmp_path / "output",
        )


def test_exact_artifact_rejects_failed_performance_gate(tmp_path: Path) -> None:
    candidate_sha = "a" * 40
    root = build_artifact(tmp_path / "artifact", candidate_sha, "42")
    performance_path = performance(tmp_path / "performance.json")
    payload = json.loads(performance_path.read_text(encoding="utf-8"))
    payload["status"] = "failed"
    write_json(performance_path, payload)

    with pytest.raises(ExactArtifactValidationError, match="performance"):
        validate_exact_artifact(
            artifact_root=root,
            candidate_sha=candidate_sha,
            artifact_id="123",
            artifact_digest="b" * 64,
            candidate_run_id="42",
            standard_ci_run_id="43",
            architecture_run_id="44",
            performance_path=performance_path,
            integration_snapshot_path=integrations(tmp_path / "integrations.json"),
            drive_inventory_path=None,
            output_dir=tmp_path / "output",
        )
