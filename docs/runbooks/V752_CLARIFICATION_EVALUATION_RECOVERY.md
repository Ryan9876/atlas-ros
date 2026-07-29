# Atlas ROS v7.5.2 Clarification Evaluation Recovery Guide

## Recovery objective

Restore accepted predecessor behavior without changing production authority or provider data.

## Recovery actions

1. Set the evaluation feature to `disabled`.
2. Discard incomplete shadow reports; do not alter predecessor decisions.
3. Verify provider writes and Todoist writes remain zero.
4. Re-run disabled-feature equivalence and deterministic replay tests.
5. If candidate validation fails, correct the candidate branch only; do not modify Active authority.
6. Validate restoration against Active v7.5.1 and immediate rollback v7.5.0 using retained release artifacts.

## Escalation conditions

Escalate and fail closed if evaluation output affected routing, execution intent, provider state, correlation crossed workspace boundaries, retained evidence contains secrets, or deterministic replay produces a different report digest.

No production data deletion, schema reversal, credential change, tag movement, authority activation, or release publication is authorized by this guide.
