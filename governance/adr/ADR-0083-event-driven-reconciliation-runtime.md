# ADR-0083: Event-driven reconciliation runtime

Status: Accepted for the v8.3.0 candidate; production activation blocked.

## Decision

Extend the v8.2.1 canonical reconciliation services with a runtime-neutral Python event-control layer and deployable WSGI receiver. The receiver exposes authenticated Todoist and Notion webhook endpoints, health/readiness endpoints, and persists a canonical event before returning success. A durable SQLite implementation supplies the reference inbox/queue, leases, retries, dead-letter isolation, receipts, controls, and outbound fingerprints. Production may replace SQLite with an approved durable service only if the same contracts and tests pass.

Webhooks are notifications. Workers fetch current provider state and invoke the existing planner, field-authority registry, orchestration, adapters, readback, and checkpoint services. A bounded incremental backstop and manual replay use the same canonical queue.

## Runtime selection

No approved always-on HTTPS runtime, secret store, backup owner, or production webhook registration is recorded in current authority. Therefore the candidate includes the deployable receiver but leaves ingress, planning, backstop, approval, replay, and automatic application disabled. `MONITOR_ONLY` and the kill switch are defaults.

The production runtime must provide TLS termination, encrypted secret injection and rotation, durable backup/restore, horizontal worker coordination, structured telemetry, rate limiting, alerts, and an operational owner. A local process or GitHub Actions workflow is not an acceptable event runtime.

Provider contracts were verified against the current [Todoist API webhook documentation](https://developer.todoist.com/api/v1/), [Notion webhook setup and signature documentation](https://developers.notion.com/reference/webhooks), and [Notion event delivery documentation](https://developers.notion.com/reference/webhooks-events-delivery).

## Consequences

- Todoist `X-Todoist-Hmac-SHA256` is verified over raw bytes with the app client secret; delivery ID is the retry identity.
- Notion `X-Notion-Signature` is verified over raw bytes with the subscription verification token.
- Accepted events survive restart and are leased per worker; unrelated objects may run concurrently after an approved durable-lock implementation is selected.
- Event payloads are reduced to digests and normalized evidence; secrets and full sensitive comments are not logged.
- Production activation remains a separate release-controlled decision.

## Alternatives rejected

- ChatGPT connectors alone: attended request surfaces are not an event bus.
- GitHub Actions polling: not a low-latency or durable webhook runtime and would mix release automation with production execution.
- Webhook payload as source of truth: providers explicitly require current-object retrieval for reliable convergence.
