from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.validate_v700_final_controller import (
    FinalControllerValidationError,
    validate_final_controller,
)
from tools.release.live_authority_snapshot import compile_snapshot, write_snapshot


def write_json(path: Path, payload: object) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def exact_artifact(path: Path, *, status: str = "passed_with_findings") -> Path:
    return write_json(
        path,
        {
            "status": status,
            "candidate_sha": "a" * 40,
            "candidate_artifact_id": "123",
            "candidate_artifact_digest": "b" * 64,
            "source_sha256": "c" * 64,
            "wheel_sha256": "d" * 64,
            "integration_snapshot_ready": True,
            "active_v650_restoration_passed": True,
            "rollback_v620_restoration_passed": True,
            "provider_writes": 0,
        },
    )


def authority_records() -> list[dict[str, object]]:
    return [
        {
            "name": name,
            "source_url": f"https://authority.example/{name}",
            "observed_active_version": "6.5.0",
            "observed_rollback_version": "6.2.0",
            "content_sha256": digest * 64,
            "readback_passed": True,
        }
        for name, digest in (
            ("release_index", "1"),
            ("system_state", "2"),
            ("active_manifest", "3"),
            ("integration_inventory", "4"),
        )
    ]


def integration_records() -> list[dict[str, object]]:
    return [
        {
            "name": name,
            "source_url": f"https://integration.example/{name.lower()}",
            "connected": True,
            "approved": True,
            "accepted": True,
            "current": True,
            "least_privilege_verified": True,
        }
        for name in ("GitHub", "Notion", "Todoist")
    ]


def live_snapshot(
    path: Path,
    *,
    candidate_sha: str = "a" * 40,
    artifact_digest: str = "b" * 64,
) -> Path:
    snapshot = compile_snapshot(
        phase="pre_promotion_baseline",
        exact_package_commit=candidate_sha,
        exact_artifact_digest=artifact_digest,
        staged_authority_digest="e" * 64,
        expected_active_version="6.5.0",
        expected_rollback_version="6.2.0",
        authorities=authority_records(),
        required_integrations=integration_records(),
    )
    write_snapshot(snapshot, path)
    return path


def test_final_controller_validation_emits_blocked_zero_write_plans(tmp_path: Path) -> None:
    output = tmp_path / "output"

    result = validate_final_controller(
        exact_artifact_validation_path=exact_artifact(tmp_path / "exact.json"),
        final_source_commit="e" * 40,
        candidate_pr_merged=False,
        decision_record_url="https://app.notion.com/decision",
        review_record_url="https://app.notion.com/review",
        output_dir=output,
    )

    assert result["status"] == "validated_not_authorized"
    assert result["final_controller"]["status"] == "blocked"
    assert "candidate PR merge has not passed" in result["final_controller"]["blockers"]
    assert "Drive migration ledger has not passed" in result["final_controller"]["blockers"]
    assert "live authority readback has not passed" in result["final_controller"]["blockers"]
    assert "exact-package Ryan authorization is required" in result["final_controller"]["blockers"]
    assert result["post_publication_verification"]["status"] == "blocked"
    assert result["authority_activation"]["status"] == "blocked"
    assert result["provider_writes"] == 0
    assert result["publication_performed"] is False
    assert result["tag_created"] is False
    assert result["authority_activated"] is False
    assert result["drive_retired"] is False
    assert (output / "V700_FINAL_CONTROLLER_VALIDATION.json").is_file()
    assert (output / "FINAL_PUBLICATION_CONTROLLER_PLAN.json").is_file()
    assert (output / "POST_PUBLICATION_VERIFICATION_PLAN.json").is_file()
    assert (output / "AUTHORITY_ACTIVATION_PLAN.json").is_file()


def test_bound_live_snapshot_closes_only_live_readback_blocker(tmp_path: Path) -> None:
    result = validate_final_controller(
        exact_artifact_validation_path=exact_artifact(tmp_path / "exact.json"),
        final_source_commit="e" * 40,
        candidate_pr_merged=False,
        decision_record_url="https://app.notion.com/decision",
        review_record_url="https://app.notion.com/review",
        output_dir=tmp_path / "output",
        live_authority_snapshot_path=live_snapshot(tmp_path / "live-authority.json"),
    )

    blockers = result["final_controller"]["blockers"]
    assert "live authority readback has not passed" not in blockers
    assert "candidate PR merge has not passed" in blockers
    assert "Drive migration ledger has not passed" in blockers
    assert "exact-package Ryan authorization is required" in blockers
    assert result["live_authority_snapshot_present"] is True
    assert result["live_authority_snapshot_sha256"]
    assert result["provider_writes"] == 0


def test_final_controller_rejects_snapshot_for_different_package(tmp_path: Path) -> None:
    with pytest.raises(FinalControllerValidationError, match="different candidate commit"):
        validate_final_controller(
            exact_artifact_validation_path=exact_artifact(tmp_path / "exact.json"),
            final_source_commit="e" * 40,
            candidate_pr_merged=False,
            decision_record_url="https://app.notion.com/decision",
            review_record_url="https://app.notion.com/review",
            output_dir=tmp_path / "output",
            live_authority_snapshot_path=live_snapshot(
                tmp_path / "wrong-live-authority.json",
                candidate_sha="f" * 40,
            ),
        )


def test_final_controller_validation_rejects_failed_exact_artifact(tmp_path: Path) -> None:
    with pytest.raises(FinalControllerValidationError, match="exact-artifact"):
        validate_final_controller(
            exact_artifact_validation_path=exact_artifact(
                tmp_path / "exact.json",
                status="failed",
            ),
            final_source_commit="e" * 40,
            candidate_pr_merged=False,
            decision_record_url="https://app.notion.com/decision",
            review_record_url="https://app.notion.com/review",
            output_dir=tmp_path / "output",
        )


def test_final_controller_validation_rejects_provider_write_evidence(tmp_path: Path) -> None:
    path = exact_artifact(tmp_path / "exact.json")
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["provider_writes"] = 1
    write_json(path, payload)

    with pytest.raises(FinalControllerValidationError, match="provider writes"):
        validate_final_controller(
            exact_artifact_validation_path=path,
            final_source_commit="e" * 40,
            candidate_pr_merged=False,
            decision_record_url="https://app.notion.com/decision",
            review_record_url="https://app.notion.com/review",
            output_dir=tmp_path / "output",
        )
