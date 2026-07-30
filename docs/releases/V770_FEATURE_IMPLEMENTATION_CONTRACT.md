# Atlas ROS v7.7.0 Feature Implementation Contract

## Purpose

Atlas ROS v7.7.0 adds a deterministic Initialization Circuit Breaker for ordinary Quick Initialization. The control is enforced in runtime code before provider invocation; prompt text is not an enforcement mechanism.

## Authorized scope

This candidate may implement and validate the package through the exact-package authorization checkpoint. It must not publish a release, create or move a production tag, merge the candidate to `main`, activate GitHub or Notion authority, write Todoist data, change integration scope, or perform any other production write.

## Predecessor gate

The candidate is valid only while live authority identifies:

- Active predecessor: Atlas ROS v7.6.1.
- Proposed immediate rollback after activation: Atlas ROS v7.6.1.
- Preserved predecessor rollback: Atlas ROS v7.6.0.
- Required integrations: exactly GitHub, Notion, and Todoist.

A predecessor mismatch blocks candidate validation.

## Required behavior

1. Quick Initialization creates one operation-scoped state machine and capability profile before the first provider call.
2. The clean cold path executes exactly six external reads, in order:
   1. GitHub `governance/AUTHORITY.json` at `HEAD`.
   2. The Release Index path named by live authority at `HEAD`.
   3. The immutable manifest path named by live authority at its exact immutable commit.
   4. The Notion System State URL named by live authority.
   5. The Integration Inventory reference named by the immutable manifest.
   6. One Todoist connector-liveness read.
3. Successful GitHub and Notion authority reads establish their readability. No redundant GitHub or Notion liveness calls are allowed.
4. An authenticated warm path may replace the two immutable GitHub document reads with locally validated cached material. Live authority, System State, Integration Inventory, and Todoist liveness remain required.
5. A rejected cache may fall back once to the cold immutable reads and may not create exploratory calls.
6. Out-of-order states, unauthorized capabilities, unauthorized targets, duplicate reads, exhausted budgets, and terminal-state calls fail closed before provider invocation.
7. One retry is allowed only for a plausibly transient failure that returned no authoritative content, uses the same capability and exact target, occurs before terminal state, and has remaining retry budget.
8. Contradictions, integrity failures, malformed authority, stale authority, access denial, invalid schemas, permanent connector failures, and terminal calls are not retried.
9. Quick Initialization always terminates before receipt rendering. A clean `READY` cannot escalate to Full Validation in the same operation.
10. Full Validation remains a separate operation with separate scope and authority.

## Receipt contract

The v2 receipt preserves accepted v1 fields and adds:

- operation ID and terminal status;
- Active and rollback identities;
- authority-model version and agreement results;
- cold, warm, or warm-fallback path;
- expected external-read plan and actual trace;
- attempted, completed, failed, retried, cached, and rejected counts;
- reads by connector and exact target;
- rejected-call summaries proving `provider_invoked=false`;
- read-budget result and terminal-lock activation;
- provider writes = 0;
- Google Drive reads = 0;
- post-terminal executed calls = 0.

## Compatibility requirements

- Existing `InitializationReceipt` consumers accepting schema `1.0` remain valid.
- Schema `2.0` is additive and retains all v1 field names.
- Existing provider-neutral authority ports remain read-only.
- Existing CLI commands remain lightweight and fail closed without configured readers.
- `initialize` and `initialize_full` remain separate from bounded `quick_initialize`.

## Security boundaries

Quick Initialization must not load or call:

- repository or workspace search;
- arbitrary file reads;
- plugin or skill discovery;
- Google Drive;
- Todoist task or project writes;
- email, messaging, calendar, scheduling, credentials, deletion, schema, publication, or authority mutation;
- web search;
- v7.6 intent-memory inspection, correction, migration, retirement, or forgetting functions;
- v7.6.1 profile loading, communication policy compilation, or situational playbooks;
- provider-backed diagnostics or telemetry.

## Definition of completion

The candidate is ready for exact-package authorization only after one frozen commit passes the complete non-publishing workflow, produces one build of the source distribution and wheel, preserves restoration of v7.6.1 and v7.6.0, and emits a retained evidence artifact with deterministic cold/warm traces and zero post-terminal provider calls.
