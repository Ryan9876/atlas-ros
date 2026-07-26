from uuid import uuid4

from atlas_ros.engines import IntentPartitioner


def test_cloudvision_controls_do_not_replace_primary_outcome() -> None:
    text = """Task = arista cloud vision code upgrade automation pilot.
Compare against v5.2 through v6.0.
Preserve previous records.
Do not block the new task as a duplicate.
Require transaction journaling, readback, and a reconciliation receipt."""
    partition = IntentPartitioner().partition(text, correlation_id=uuid4())
    assert partition.primary_business_outcome == (
        "Launch the Arista CloudVision code-upgrade automation pilot"
    )
    assert partition.evaluation_context == ("Compare against v5.2 through v6.0.",)
    assert partition.execution_constraints == (
        "Preserve previous records.",
        "Do not block the new task as a duplicate.",
    )
    assert partition.audit_requirements == (
        "Require transaction journaling, readback, and a reconciliation receipt.",
    )
    assert not partition.requires_human_decision
    assert partition.verify_digest()


def test_audit_primary_remains_the_business_outcome() -> None:
    partition = IntentPartitioner().partition(
        "Produce a reconciliation audit report for the CloudVision pilot.",
        correlation_id=uuid4(),
    )
    assert partition.primary_business_outcome == (
        "Produce a reconciliation audit report for the CloudVision pilot"
    )
    assert not partition.requires_human_decision


def test_multiple_business_outcomes_fail_closed() -> None:
    partition = IntentPartitioner().partition(
        "Create a financial budget. Launch a network automation pilot.",
        correlation_id=uuid4(),
    )
    assert partition.requires_human_decision
    assert "multiple_plausible_primary_outcomes" in partition.ambiguities
