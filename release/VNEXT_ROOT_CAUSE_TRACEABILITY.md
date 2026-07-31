# Natural Comment Reconciliation Traceability Matrix

| Root cause | Required control | Implementation | Verification |
|---|---|---|---|
| Inbox-only reconciliation omitted Todoist events | Composite ingress aliases and explicit scoped modes | `reconciliation/composite.py` | Composite and isolation tests |
| Ordinary comments required `@atlas` | Unified explicit-first, natural-second interpretation | `reconciliation/service.py`, `comment_lifecycle.py` | Parent/subtask comment tests |
| Normalizer received task text, not comments | Canonical comment source with event identity and metadata | `TodoistCommentSourceAdapter` | Exact comment-to-plan fixture |
| Narrow ownership/follow-up grammar | Deterministic commitment, pronoun, and Ryan follow-up rules | `task_update_normalizer.py` | Parametrized grammar tests |
| No connector-level acceptance path | Fake-provider end-to-end dry run, authorized apply, readback, replay | `test_vnext_natural_comment_reconciliation.py` | Required Kweku/Rivian scenario |
| Global watermark could suppress unseen events | Event ID is authoritative; 24-hour overlap is retrieval-only | reconciliation service/state | Older-unseen-event test |
| Ignored/blocked events were not visible | Typed event outcomes and expanded dry-run report | service, state ledger, CLI output | Informational/blocked reporting tests |
| Inference could be invisible | Field origins, confidence, provenance, exact authorization binding | contracts, planner, service | Plan assertions and authorization tests |
