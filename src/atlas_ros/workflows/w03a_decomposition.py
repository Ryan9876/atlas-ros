from __future__ import annotations

from atlas_ros.config.loader import load_config
from atlas_ros.domain.models import Action, ReadinessReport, ReadinessStatus
from atlas_ros.rules import RulesEngine, action_rules


class DecompositionService:
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
        return ReadinessReport(
            status=ReadinessStatus.READY if not failures else ReadinessStatus.NOT_READY,
            passed_rules=[] if failures else [rule.id for rule in action_rules()],
            failed_rules=failures,
            required_human_decisions=[finding.recommended_action for finding in findings],
            proposed_subtasks=self.select_pattern(action.title)[1],
        )
