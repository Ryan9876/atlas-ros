from atlas_ros.domain.models import Action, Classification, Severity
from atlas_ros.rules.engine import Rule


def action_rules() -> list[Rule]:
    return [
        Rule(
            "ACTION_EXECUTION_READY_REQUIRES_DOD",
            "Definition of Done",
            "Execution-ready actions require a Definition of Done.",
            "config/readiness.yaml",
            "readiness",
            Severity.ERROR,
            Action,
            lambda a: not a.execution_ready or bool(a.definition_of_done.strip()),
            "Add a binary Definition of Done.",
        ),
        Rule(
            "ACTION_EXECUTION_READY_REQUIRES_RYAN_OWNER",
            "Ryan ownership",
            "Execution-ready actions require Ryan as owner.",
            "config/readiness.yaml",
            "readiness",
            Severity.ERROR,
            Action,
            lambda a: not a.execution_ready or a.owner.strip().lower() == "ryan",
            "Assign Ryan as accountable owner.",
        ),
        Rule(
            "ACTION_TODOIST_REQUIRES_ACTION",
            "Action classification",
            "Projects and workstreams cannot be sent to Todoist as Actions.",
            "config/classifications.yaml",
            "todoist",
            Severity.ERROR,
            Action,
            lambda a: a.classification == Classification.ACTION,
            "Create or use the Portfolio Project record.",
        ),
        Rule(
            "ACTION_DELEGATION_REVIEWED",
            "Delegation reviewed",
            "Execution-ready actions require an explicit delegation review.",
            "config/readiness.yaml",
            "delegation",
            Severity.ERROR,
            Action,
            lambda a: not a.execution_ready or a.delegation_reviewed or a.delegated_work_present,
            "Confirm whether delegated technical work is required.",
        ),
        Rule(
            "ACTION_REQUIRED_DELEGATION_SEPARATED",
            "Required delegated work separation",
            "When delegated technical work is required, it must be represented separately.",
            "config/readiness.yaml",
            "delegation",
            Severity.ERROR,
            Action,
            lambda a: (
                not a.execution_ready or not a.delegated_work_required or a.delegated_work_present
            ),
            "Create or link the Delegated Work record.",
        ),
    ]
