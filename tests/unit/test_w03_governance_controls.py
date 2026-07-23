from __future__ import annotations

import pytest

from atlas_ros.adapters.todoist import FakeTodoistAdapter, TodoistTask
from atlas_ros.domain.models import Action
from atlas_ros.workflows.w03_todoist import (
    TodoistService,
    route_todoist_section,
    task_description,
)


def action(title: str, done_when: str = "The outcome is complete and verified.") -> Action:
    return Action(
        id=title.casefold().replace(" ", "-"),
        title=title,
        definition_of_done=done_when,
        execution_ready=True,
        delegation_reviewed=True,
    )


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Define Team Operating Model", "Leadership & Team"),
        ("Complete performance review", "Leadership & Team"),
        ("Prepare 1:1 agenda", "Leadership & Team"),
        ("Interview candidate", "Leadership & Team"),
        ("Migrate datacenter", "Active Projects"),
        ("Complete firewall upgrade deployment", "Active Projects"),
        ("Complete incident RCA", "Operations"),
        ("Perform firewall rule cleanup", "Operations"),
        ("Study for AWS certification", "Development & Learning"),
        ("Read AI leadership book", "Development & Learning"),
        ("Waiting for vendor quote", "Waiting on Others"),
        ("Waiting for Tina review", "Waiting on Others"),
    ],
)
def test_management_domain_routing(title: str, expected: str) -> None:
    decision = route_todoist_section(action(title))
    assert decision.selected_section == expected
    assert decision.matched_rule
    assert decision.reason


def test_leadership_precedence_over_project_shape() -> None:
    decision = route_todoist_section(action("Implement Team Operating Model project"))
    assert decision.selected_section == "Leadership & Team"
    assert decision.fallback_used is False


def test_done_when_accepts_one_prose_criterion() -> None:
    description = task_description("Prepare the review", "The review is approved.")
    assert "**Objective:**" in description
    assert "**Done when:**" in description


def test_done_when_accepts_multiple_markdown_bullets() -> None:
    description = task_description(
        "Prepare the review",
        "- Feedback is collected.\n- Changes are incorporated.\n- Approval is recorded.",
    )
    assert description.count("\n-") == 3


@pytest.mark.parametrize(
    "criteria",
    [
        "Feedback is collected; changes are incorporated.",
        "Feedback is collected, and changes are incorporated.",
        "Feedback is collected.\nChanges are incorporated.",
        "- Feedback is collected.",
    ],
)
def test_done_when_rejects_nonconforming_multiple_criteria(criteria: str) -> None:
    with pytest.raises(ValueError):
        task_description("Prepare the review", criteria)


def test_section_move_preserves_parent_relationships_and_order() -> None:
    adapter = FakeTodoistAdapter()
    adapter.tasks = {
        "parent": TodoistTask(
            id="parent",
            content="Parent",
            project_id="work",
            section_id="active-projects",
            description="parent",
            order=7,
        ),
        "child-1": TodoistTask(
            id="child-1",
            content="Child 1",
            project_id="work",
            parent_id="parent",
            description="child 1",
            order=1,
        ),
        "child-2": TodoistTask(
            id="child-2",
            content="Child 2",
            project_id="work",
            parent_id="parent",
            description="child 2",
            order=2,
        ),
    }

    TodoistService(adapter=adapter).move_task_group(
        "parent", "leadership-team", confirmed=True
    )

    assert adapter.get_task("parent").section_id == "leadership-team"
    children = sorted(adapter.list_tasks(parent_id="parent"), key=lambda item: item.order)
    assert [child.id for child in children] == ["child-1", "child-2"]
    assert all(child.parent_id == "parent" for child in children)
    assert [child.order for child in children] == [1, 2]
