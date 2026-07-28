from __future__ import annotations

from dataclasses import replace

from tools.release.final_controller import (
    AuthorityActivationEvidence,
    FinalPackageEvidence,
    PostPublicationEvidence,
    compile_authority_activation,
    compile_final_controller,
    verify_post_publication,
)


def final_evidence() -> FinalPackageEvidence:
    return FinalPackageEvidence(
        candidate_version="7.0.0rc1",
        candidate_commit="a" * 40,
        final_source_commit="b" * 40,
        candidate_pr_merged=True,
        candidate_artifact_id="artifact-1",
        candidate_artifact_digest="c" * 64,
        final_package_version="7.0.0",
        final_package_artifact_id="final-artifact-1",
        final_package_artifact_digest="2" * 64,
        source_sha256="d" * 64,
        wheel_sha256="e" * 64,
        standard_ci_passed=True,
        architecture_validation_passed=True,
        candidate_validation_passed=True,
        exact_artifact_validation_passed=True,
        final_package_validation_passed=True,
        drive_migration_ledger_complete=True,
        drive_migration_ledger_sha256="f" * 64,
        live_authority_readback_complete=True,
        required_integrations_ready=True,
        v650_rollback_restored=True,
        v650_rollback_evidence_reconciled=True,
        v650_rollback_evidence_sha256="1" * 64,
        review_record_url="https://app.notion.com/review",
        decision_record_url="https://app.notion.com/decision",
        exact_package_authorization_id="authorization-v700",
        provider_writes_during_validation=0,
    )


def publication_evidence() -> PostPublicationEvidence:
    return PostPublicationEvidence(
        final_version="7.0.0",
        final_tag="v7.0.0",
        final_source_commit="b" * 40,
        published_release_readable=True,
        immutable_tag_points_to_final_source=True,
        publication_checksums_passed=True,
        source_sha256_matches_identity=True,
        wheel_sha256_matches_identity=True,
        clean_install_passed=True,
        v650_rollback_restored=True,
        v620_historical_rollback_restored=True,
        live_authority_readback_complete=True,
        provider_writes_during_verification=0,
    )


def activation_evidence() -> AuthorityActivationEvidence:
    return AuthorityActivationEvidence(
        final_version="7.0.0",
        final_tag="v7.0.0",
        final_source_commit="b" * 40,
        post_publication_verification_passed=True,
        release_index_digest="c" * 64,
        authority_record_digest="d" * 64,
        active_manifest_digest="e" * 64,
        notion_system_state_readback_passed=True,
        integration_inventory_readback_passed=True,
        v650_rollback_restored=True,
        exact_package_authorization_id="authorization-v700",
        provider_writes_during_activation_validation=0,
    )


def test_final_controller_is_ready_only_for_one_exact_authorized_package() -> None:
    receipt = compile_final_controller(
        final_evidence(),
        transaction_id="final-controller-v700",
    )

    assert receipt.status == "ready"
    assert receipt.final_version == "7.0.0"
    assert receipt.provider_writes == 0
    assert receipt.publication_performed is False
    assert receipt.tag_created is False
    assert receipt.authority_activated is False
    assert receipt.drive_retired is False


def test_final_controller_fails_closed_on_live_governance_gaps() -> None:
    evidence = replace(
        final_evidence(),
        drive_migration_ledger_complete=False,
        drive_migration_ledger_sha256=None,
        live_authority_readback_complete=False,
        v650_rollback_evidence_reconciled=False,
        v650_rollback_evidence_sha256=None,
        exact_package_authorization_id=None,
    )

    receipt = compile_final_controller(
        evidence,
        transaction_id="final-controller-v700",
    )

    assert receipt.status == "blocked"
    assert "Drive migration ledger has not passed" in receipt.blockers
    assert "live authority readback has not passed" in receipt.blockers
    assert "v6.5 rollback evidence reconciliation has not passed" in receipt.blockers
    assert "exact-package Ryan authorization is required" in receipt.blockers
    assert receipt.provider_writes == 0


def test_final_controller_rejects_missing_final_package_validation() -> None:
    receipt = compile_final_controller(
        replace(
            final_evidence(),
            final_package_validation_passed=False,
            final_package_artifact_id="",
        ),
        transaction_id="final-controller-v700",
    )

    assert receipt.status == "blocked"
    assert "final-package validation has not passed" in receipt.blockers
    assert "final package artifact ID is required" in receipt.blockers


def test_rollback_digest_cannot_replace_reconciliation() -> None:
    receipt = compile_final_controller(
        replace(
            final_evidence(),
            v650_rollback_evidence_reconciled=False,
        ),
        transaction_id="final-controller-v700",
    )

    assert receipt.status == "blocked"
    assert "v6.5 rollback evidence reconciliation has not passed" in receipt.blockers
    assert "v6.5 rollback evidence digest cannot replace reconciliation" in receipt.blockers


def test_post_publication_verification_is_independent_and_provider_free() -> None:
    receipt = verify_post_publication(
        publication_evidence(),
        transaction_id="verify-v700-publication",
    )

    assert receipt.status == "ready"
    assert receipt.provider_writes == 0
    assert receipt.publication_performed is False
    assert receipt.authority_activated is False
    assert receipt.drive_retired is False


def test_post_publication_verification_rejects_tag_or_checksum_gaps() -> None:
    evidence = replace(
        publication_evidence(),
        final_tag="v7.0.0rc1",
        publication_checksums_passed=False,
    )

    receipt = verify_post_publication(
        evidence,
        transaction_id="verify-v700-publication",
    )

    assert receipt.status == "blocked"
    assert "published identity must be Atlas ROS v7.0.0" in receipt.blockers
    assert "publication checksums has not passed" in receipt.blockers


def test_authority_activation_compiles_without_executing() -> None:
    receipt = compile_authority_activation(
        activation_evidence(),
        transaction_id="activate-v700-authority",
    )

    assert receipt.status == "ready"
    assert receipt.provider_writes == 0
    assert receipt.activation_performed is False
    assert receipt.drive_retired is False


def test_authority_activation_requires_readback_and_exact_authorization() -> None:
    evidence = replace(
        activation_evidence(),
        notion_system_state_readback_passed=False,
        integration_inventory_readback_passed=False,
        exact_package_authorization_id=None,
    )

    receipt = compile_authority_activation(
        evidence,
        transaction_id="activate-v700-authority",
    )

    assert receipt.status == "blocked"
    assert "Notion System State readback has not passed" in receipt.blockers
    assert "Integration Inventory readback has not passed" in receipt.blockers
    assert "exact-package Ryan authorization is required" in receipt.blockers