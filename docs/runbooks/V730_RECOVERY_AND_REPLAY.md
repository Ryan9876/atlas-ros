# v7.3 Recovery and Replay Runbook

1. Preserve source command text, source revision, command digest, lifecycle-plan digest, canonical-plan digest, and journal state.
2. Read current Notion and Todoist targets before retry.
3. If the exact command identity already completed, return the existing receipt.
4. If partially applied, resume only remaining exact operations after readback.
5. If current provider state contradicts the plan, stop for attended review; do not generate successor intent in reconciliation.
6. Compensate only through an exact authorized plan using the pre-write snapshot.
7. Preserve the persistent parent outcome and completed subtasks.
8. Production rollback remains the live-authority-defined v7.1.0 package; this candidate does not alter rollback authority.
