# Atlas ROS v8.2.0 Natural Comment Reconciliation Traceability

| Root cause | Required control | Implementation | Verification |
|---|---|---|---|
| Inbox-only reconciliation omitted Todoist events | Composite aliases plus explicit isolated scopes | `reconciliation/composite.py` | Composite and scope-isolation tests |
| Ordinary comments required `@atlas` | Explicit-first, natural-second interpretation | `reconciliation/service.py`, `comment_lifecycle.py` | Parent/subtask ordinary-comment tests |
| Normalizer received task text, not comments | Canonical comment source with stable identity and metadata | `TodoistCommentSourceAdapter` | Exact connector comment-to-plan fixture |
| Common ownership/follow-up grammar absent | Deterministic commitment, bounded coreference, and Ryan follow-up rules | `task_update_normalizer.py` | Parametrized grammar/date tests |
| Acceptance bypassed connector ingestion | Connector fixture from Todoist comment through verified dry-run plan | `test_v820_natural_comment_reconciliation.py` | Kweku/Rivian acceptance fixture |
| Watermark could suppress delayed events | Per-event identity authoritative; bounded overlap only | service/state | Older unseen event test |
| Blocked/ignored comments could disappear | Typed outcomes and complete dry-run counts/reasons | service, state, CLI | Blocked/informational reporting tests |
| Inference could be invisible or overbroad | Typed origins, evidence, confidence, ambiguity, exact approval | contracts/planner/service | Proposal and authorization tests |
| Proposed Notion fields did not exist | Store versioned event envelope in existing `Notes` | `NotionReconciliationStateStore` | Live-schema contract unit test |
| v8.1 source advanced during initial implementation | Apply and validate against exact v8.1.0 package source | v8.2 branch/workflow | Patch check, full regression suite |
| ADR number collided with v8.1 | Allocate ADR-0082 | documentation | Documentation authority check |
