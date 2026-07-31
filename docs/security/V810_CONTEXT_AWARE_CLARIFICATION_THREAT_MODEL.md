# Atlas ROS v8.1.0 Context-Aware Clarification Threat Model

Status: candidate security analysis; not production-active.

## Protected properties

The capability must preserve original captures, exact capture and correlation identity, current user authority, provider-write boundaries, deterministic replay, item isolation, and the accepted v7.5.2 clarification decision contract.

## Threats and controls

| Threat | Control | Required evidence |
|---|---|---|
| Unknown entity is overwritten as a typo | Entity-position preservation; local connector scrutiny | LEW and Novaryn fixtures |
| Leading interpretation silently becomes execution | Analysis and resolution set routing and execution authority to false | Zero-write receipts and model validation |
| Clarification binds to wrong item | Capture, correlation, original instruction, and analysis digest binding | Wrong-capture rejection test |
| Duplicate answer resumes twice | Deterministic idempotency identity and duplicate replay disposition | Exact-once replay test |
| Different second answer overwrites first | Conflicting resolution fails closed | Replay-conflict test |
| One ambiguous item blocks the whole batch | Partial-item pause and eligible-after-interruption list | Four-item batch fixture |
| Clarification is delayed until final summary | First ambiguity creates an interrupt-before-next-item plan | Interruption-position test |
| Person mention becomes delegation | Tentative delegation category and v7.5.2 decision binding | Ambiguous-delegation fixture |
| Missing owner, outcome, or completion criteria is invented | Dedicated missing-field categories | Required-category tests |
| Unbounded context leaks unrelated data | Caller supplies bounded context object and source references | Context contract validation |
| Context injection changes authority | Context is evidence only; routing and execution remain false | Compatibility and zero-write tests |
| Clarification creates persistent intent memory | No memory adapter, index write, or profile update exists | Architecture inspection and zero Notion writes |
| Provider calls occur during analysis | Capability has no provider ports and catalog marks writes_providers false | Architecture check and provider-write receipt |
| Determinism is lost through timestamps | Timestamps are optional caller evidence; operational outputs are input-bound | Replay digest test |

## Trust-boundary decisions

The analyzer may rank interpretations but cannot authorize routing, planning, delegation, Todoist creation, Notion mutation, messaging, scheduling, or execution. The accepted v7.5.2 `ClarificationDecisionV1` remains the predecessor decision boundary. v8.1.0 adds evidence and interaction quality; it does not replace attended authorization.

## Failure posture

Any missing identity, conflicting answer, ambiguous material target, conflicting date or priority, unresolved ownership, missing completion boundary, schema mismatch, context digest mismatch, or replay conflict fails closed. The original capture remains unchanged and unrelated independent work remains eligible to continue.
