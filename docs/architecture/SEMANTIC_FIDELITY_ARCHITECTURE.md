# Semantic Fidelity Architecture

## Purpose

Preserve the user's business outcome while keeping benchmark, audit, provider-control, and system-evidence instructions available to the appropriate control plane.

## Flow

1. **Intent Partitioning** assigns clauses to primary outcome, current action, delegated action, conditional action, evaluation, audit, execution constraint, or reference context.
2. **Reasoning Package V4** retains classification and planning-model selection while carrying the immutable intent partition and its digest.
3. **Knowledge Composition V2** resolves provider-neutral planning knowledge for V4 reasoning.
4. **Management Package V3** constructs the business outcome, current path, delegated work, conditional work, and non-projectable evidence as separate fields.
5. **Semantic Execution Planning V3** validates fidelity, projects only the current business path, and records why every other item remains outside Todoist.
6. **Execution Orchestration V2** continues to authorize and apply the exact provider-neutral plan without adding or reinterpreting work.
7. **Canonical Reconciliation V2** continues only after verified application.

## Central invariant

```text
business_plan(base_request)
==
business_plan(base_request + benchmark_and_audit_controls)
```

Allowed differences are limited to duplicate handling, existing-representation evidence, evaluation records, audit records, authorization evidence, and reconciliation evidence.

## Fail-closed behavior

The planner emits no execution objects and requires attended review when:

- no primary business outcome is resolved;
- multiple plausible primary outcomes exist;
- semantic confidence is below threshold;
- the controlled-pilot current path is incomplete;
- control-plane evidence displaces business execution;
- delegated work becomes Ryan-owned execution;
- conditional or future work enters the current horizon.

## Provider boundary

Intent, reasoning, knowledge, management, and planning remain provider-free. The semantic planner never authorizes or writes. Todoist and Notion adapters remain downstream of exact attended authorization.
