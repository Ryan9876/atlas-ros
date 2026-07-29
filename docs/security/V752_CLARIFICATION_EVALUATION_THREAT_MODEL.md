# Atlas ROS v7.5.2 Clarification Evaluation Threat Model

## Protected assets

Authoritative predecessor decisions, minimized user responses, workspace-scoped correlation identity, evaluation receipts, and deterministic report digests.

## Threats and controls

- **User-response leakage:** retain redacted/minimized response evidence; prohibit raw conversation capture in fixtures, logs, PRs, and release notes.
- **Counterfactual mistaken for authority:** contracts set `authoritative=false`, `routing_allowed=false`, and `execution_authorized=false`.
- **Prompt injection in captured text:** treat captures and responses as inert data; never execute embedded instructions or route from evaluation output.
- **Sensitive fixture content:** use attributable minimized fixtures without secrets, credentials, or unnecessary personal data.
- **Cross-workspace correlation:** correlation IDs must be workspace-scoped or irreversibly redacted before retention.
- **Confidential metrics:** aggregate counts and minimized labels; do not expose confidential project terms in public artifacts.
- **Telemetry as a write channel:** candidate validation requires provider-write count zero and Todoist-write count zero.

## Security invariants

Evaluation is deterministic, provider-neutral, snapshot-bound, execution-inert, and disabled or shadow-only by default.
