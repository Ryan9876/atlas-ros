# v8.3.0 Event Reconciliation Operator Runbook

Candidate behavior is not Active production capability. Default controls are monitor-only, kill switch on, and all ingress/application controls disabled.

## Production prerequisites

1. Promote and activate the exact v8.3.0 package and policy through release authority.
2. Approve an always-on HTTPS runtime, operational owner, encrypted secret store, retention, backup, restore, alerting, and incident path.
3. Register Todoist webhook events in an application, complete Ryan's OAuth installation (the app owner does not receive webhooks by default), store the client secret, and verify delivery.
4. Register and verify the Notion subscription, store its verification token, and confirm the authoritative data sources and required capabilities.
5. Run a zero-write inventory and backstop dry run from the v8.2.1 checkpoint.
6. Enable ingress and planning in `MONITOR_ONLY`; prove webhook/backstop parity, deduplication, latency, and zero business-provider writes.
7. Activate the exact bounded-autonomy policy only after the separate authorization and readback gate.

Setup references: [Todoist API webhooks](https://developer.todoist.com/api/v1/), [Notion webhooks](https://developers.notion.com/reference/webhooks), and [Notion event types and delivery](https://developers.notion.com/reference/webhooks-events-delivery).

## Endpoints and service levels

- `POST /webhooks/todoist`: raw-body HMAC verification, durable acceptance, HTTP 200.
- `POST /webhooks/notion`: raw-body HMAC verification, durable acceptance, HTTP 202.
- `GET /healthz`: process health.
- `GET /readyz`: returns not-ready until ingress is activated.
- Normal target: acceptance within 10 seconds and reconciliation start within 60 seconds after provider delivery. Provider-side delivery delay is reported separately. Backstop target is bounded convergence within 15 minutes.

## Operator controls

Inspect queue depth/age, state counts, event evidence, plan digest, decision, reason, attempts, lease, receipts, checkpoint/sync health, policy, and kill switch. Controls are separate for ingress, planning, auto-apply, approval, backstop, replay, kill switch, and mode.

- Pause: set kill switch true and auto-apply disabled. Intake may continue.
- Resume: requires exact production policy-activation authorization and readback.
- Approve: bind Ryan, event set, snapshots, plan, authority/policy, and expiry. Re-read all preconditions.
- Reject: record actor and reason; move the exact proposal to Blocked.
- Replay/re-plan: create a causally linked manual event; never mutate the original event.
- Dead letter: inspect signature, identity, mapping, snapshots, plan, attempts, and provider errors. Release only after attended actor/reason evidence; preserve original idempotency.
- Repair: read back every target, classify each mutation applied/not applied/indeterminate, keep the checkpoint unchanged, and prepare an exact repair plan requiring attended approval.

## Incident response

Immediately engage the kill switch for loops, unexpected writes, authority conflict, permission drift, signature failure bursts, readback mismatch, checkpoint divergence, or queue runaway. Preserve intake and evidence when safe. Do not use Todoist as an error queue. Do not cascade provider deletion. Escalate through ROS Operations and governing Review Records after production activation.

## Rollback

Disable ingress/planning/auto-apply/backstop/replay, drain no additional business mutations, preserve v8.3 events and receipts, restore v8.2.1 code and policy, verify the production ledger/checkpoint, and confirm v8.2.1 readers ignore additive event tables/evidence. Never restore or query W04.
