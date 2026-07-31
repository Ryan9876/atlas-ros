import pytest

from atlas_ros.adapters.notion import FakeNotionAdapter
from atlas_ros.adapters.todoist import FakeTodoistAdapter, TodoistComment, TodoistTask
from atlas_ros.reconciliation.baseline import (
    BaselineAuthorization,
    ProductionBaselineService,
)
from atlas_ros.reconciliation.state import (
    LedgerFailureCode,
    LedgerValidationError,
    NotionReconciliationStateStore,
)


def _text(value: str) -> dict[str, object]:
    return {"rich_text": [{"plain_text": value}]}


def _select(value: str) -> dict[str, object]:
    return {"select": {"name": value}}


def _service() -> tuple[ProductionBaselineService, FakeNotionAdapter, FakeTodoistAdapter]:
    notion = FakeNotionAdapter()
    notion.create_page(
        "actions",
        {
            "Execution System": _select("Todoist"),
            "Execution Object ID": _text("parent"),
        },
    )
    todoist = FakeTodoistAdapter()
    todoist.tasks["parent"] = TodoistTask(id="parent", content="Parent", project_id="work")
    todoist.tasks["child"] = TodoistTask(
        id="child", content="Child", project_id="work", parent_id="parent"
    )
    todoist.comments = {
        "parent": [
            TodoistComment(
                id="p1",
                task_id="parent",
                content="historic parent",
                posted_at="2026-07-01T00:00:00+00:00",
            ),
            TodoistComment(
                id="new",
                task_id="parent",
                content="new comment",
                posted_at="2026-08-02T00:00:00+00:00",
            ),
        ],
        "child": [
            TodoistComment(
                id="s1",
                task_id="child",
                content="historic child",
                posted_at="2026-07-02T00:00:00+00:00",
            )
        ],
    }
    return (
        ProductionBaselineService(
            notion,
            todoist,
            NotionReconciliationStateStore(notion, "state"),
            action_data_source_id="actions",
        ),
        notion,
        todoist,
    )


def _authorization(plan) -> BaselineAuthorization:  # type: ignore[no-untyped-def]
    return BaselineAuthorization(
        run_id=plan.run_id,
        cutover_at=plan.cutover_at,
        source_inventory_digest=plan.source_inventory_digest,
        plan_digest=plan.plan_digest,
        authorization_identity="baseline-auth",
    )


def test_baseline_is_inert_complete_and_replay_safe() -> None:
    service, notion, todoist = _service()
    plan = service.plan(run_id="baseline-1", cutover_at="2026-08-01T00:00:00+00:00")
    assert [event.event_id for event in plan.events] == ["todoist-comment:p1", "todoist-comment:s1"]
    assert plan.mapped_parent_count == 1 and plan.subtask_count == 1
    receipt = service.apply(plan, _authorization(plan))
    assert receipt.complete and receipt.written_events == 2 and receipt.checkpoint_created
    assert len(notion.query_pages("state", {})) == 3
    assert todoist.tasks["parent"].checked is False
    replay = service.apply(plan, _authorization(plan))
    assert replay.complete and replay.written_events == 0 and replay.replayed_events == 2
    assert len(notion.query_pages("state", {})) == 3


def test_baseline_partial_failure_does_not_create_checkpoint() -> None:
    service, notion, _todoist = _service()
    original = notion.create_page
    writes = 0

    def fail_second(source: str, properties: dict[str, object]):
        nonlocal writes
        writes += 1
        if writes == 2:
            raise RuntimeError("Notion unavailable")
        return original(source, properties)

    notion.create_page = fail_second  # type: ignore[method-assign]
    plan = service.plan(run_id="baseline-2", cutover_at="2026-08-01T00:00:00+00:00")
    receipt = service.apply(plan, _authorization(plan))
    assert not receipt.complete and not receipt.checkpoint_created
    assert service.state._find(service.state.CHECKPOINT_KEY) is None


def test_baseline_conflicting_existing_evidence_blocks_checkpoint() -> None:
    service, _notion, _todoist = _service()
    plan = service.plan(run_id="baseline-3", cutover_at="2026-08-01T00:00:00+00:00")
    service.state.mark_event("todoist-comment:p1", "ignored", {"source_digest": "wrong"})
    receipt = service.apply(plan, _authorization(plan))
    assert not receipt.complete and "conflicts" in receipt.failures[0]
    assert service.state._find(service.state.CHECKPOINT_KEY) is None


def test_baseline_requires_exact_attended_authorization() -> None:
    service, _notion, _todoist = _service()
    plan = service.plan(run_id="baseline-4", cutover_at="2026-08-01T00:00:00+00:00")
    with pytest.raises(LedgerValidationError) as error:
        service.apply(
            plan,
            BaselineAuthorization(
                run_id=plan.run_id,
                cutover_at=plan.cutover_at,
                source_inventory_digest=plan.source_inventory_digest,
                plan_digest="wrong",
                authorization_identity="baseline-auth",
            ),
        )
    assert error.value.code is LedgerFailureCode.BASELINE_AUTHORIZATION_INVALID


def test_baseline_cutover_is_immutable_and_utc() -> None:
    service, _notion, _todoist = _service()
    with pytest.raises(ValueError, match="exact UTC"):
        service.plan(run_id="baseline-5", cutover_at="2026-08-01T00:00:00Z")
