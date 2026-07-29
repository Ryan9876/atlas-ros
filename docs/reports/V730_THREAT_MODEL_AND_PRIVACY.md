# v7.3 Threat Model and Privacy Review

## Threats and controls

- **Command injection:** only explicit `@atlas` grammar is accepted; ambiguity fails closed.
- **Replay/duplication:** command digest and operation idempotency keys are deterministic.
- **Privilege expansion:** current approved providers and object budgets only; no scope request.
- **Silent completion:** Definition of Done, child closure, evidence, and declared approval are mandatory.
- **Cross-system contradiction:** conflicts lower confidence, surface to Ryan, and block unsafe mutation conclusions.
- **Adapter overreach:** static architecture validation prohibits planning/authorization imports.
- **Reconciliation intent creation:** prohibited by architecture and regression tests.
- **Sensitive evidence:** context packs retain identities/links, apply redaction state, and warn when redaction affects interpretation.
- **Autonomous behavior:** no polling, scheduling, notifications, messages, email, calendar, deletion, credential action, or live-network execution.
