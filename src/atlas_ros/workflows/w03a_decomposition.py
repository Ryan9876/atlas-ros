from __future__ import annotations

from atlas_ros.config.loader import load_config
from atlas_ros.contracts import ManagementPackage
from atlas_ros.domain.models import Action, ReadinessReport, ReadinessStatus
from atlas_ros.planning import ExecutionPlanner, ExecutionPlanningPolicy
from atlas_ros.rules import RulesEngine, action_rules


class DecompositionService:
    """Legacy W03A facade over readiness rules and the canonical Execution Planner."""

    def select_pattern(self, text: str) -> tuple[str, list[str]]:
        patterns = load_config("patterns")["patterns"]
        words = set(__import__("re").findall(r"[a-z0-9]+", text.casefold()))
        ranked = sorted(
            patterns.items(), key=lambda item: (-len(words & set(item[0].split("_"))), item[0])
        )
        for name, steps in ranked:
            if words & set(name.split("_")):
                return name, list(steps)
        return "investigation", list(patterns["investigation"])

    def readiness(self, action: Action) -> ReadinessReport:
        findings = RulesEngine(action_rules()).evaluate(action, action.id)
        failures = [finding.rule_id for finding in findings if finding.severity.value == "error"]
        candidates = self.select_pattern(action.title)[1]
        compatibility_policy = ExecutionPlanningPolicy(
            max_steps=len(candidates),
            review_threshold=max(5, len(candidates)),
        )
        management = ManagementPackage(
            source_component="legacy.w03a",
            responsibility=action.title,
            desired_outcome=action.definition_of_done or action.title,
            owner=action.owner or "Ryan",
            workstream=action.todoist_section,
        )
        execution_plan = ExecutionPlanner(compatibility_policy).plan(
            management,
            action_id=action.id,
            destination=action.todoist_project,
            candidate_steps=tuple(candidates),
        )
        return ReadinessReport(
            status=ReadinessStatus.READY if not failures else ReadinessStatus.NOT_READY,
            passed_rules=[] if failures else [rule.id for rule in action_rules()],
            failed_rules=failures,
            required_human_decisions=[finding.recommended_action for finding in findings],
            proposed_subtasks=[step.title for step in execution_plan.steps],
        )
