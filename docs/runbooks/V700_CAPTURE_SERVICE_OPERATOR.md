# Atlas ROS v7 Capture Service Operator Runbook

## Status and authority boundary

This runbook defines the candidate Atlas ROS v7 Capture Service operating contract. It does not activate v7, replace the current production driver, expand provider permissions, or authorize unattended execution.

Atlas ROS v6.5.0 remains the sole Active production release. Atlas ROS v6.2.0 remains the immediate immutable rollback. The current Raycast Capture 1.1.5 production driver remains attended and limited to the authoritative Notion Universal Inbox until a separately authorized v7 production transaction completes.

## Purpose

Capture converts one attended input into one durable, retry-safe record while preserving the exact user content, correlation identity, and provider readback evidence required by the canonical processing pipeline.

Capture is not planning, authorization, provider execution, or reconciliation. It may not create Todoist work, schedule activity, send messages, delete data, or infer additional work.

## Required inputs

Each capture requires:

- non-empty content;
- a stable source identifier;
- one correlation ID generated before the first provider attempt;
- optional due-date, delegation, and additional-context fields supplied explicitly by the caller;
- the current authoritative Universal Inbox destination resolved from live Notion governance.

The original correlation ID must be reused for every retry. A retry must never create a new logical capture identity.

## Canonical capture sequence

1. Accept the attended input.
2. Normalize transport formatting without changing semantic content.
3. Create an immutable `CaptureEnvelope` containing the source, content, correlation ID, and capture timestamp.
4. Persist retry-safe local pending state before the first provider write.
5. Query the authoritative Universal Inbox for the correlation ID.
6. If a matching durable record already exists, return that record as an idempotent success.
7. Otherwise, write exactly one Universal Inbox record using the original correlation ID.
8. Read the created record back independently from Notion.
9. Verify that the readback record ID, correlation ID, and governed capture fields match the attempted write.
10. Mark local pending state complete only after successful readback.
11. Return a capture receipt containing the durable Notion record ID and correlation ID.
12. Invoke canonical processing only after durable capture succeeds.

## Success contract

Capture succeeds only when all of the following are true:

- Notion returned a durable record ID;
- independent readback completed;
- readback contains the original correlation ID;
- readback fields match the governed write projection;
- local retry state is marked complete;
- no duplicate Universal Inbox record was created.

A transport-level success response without durable provider readback is not success.

## Failure and retry behavior

On provider, network, authentication, schema, or readback failure:

- retain the retry-safe pending payload locally;
- retain the original correlation ID;
- record the failing phase and sanitized error reason;
- do not report capture success;
- do not create a replacement correlation ID;
- do not delete partial local evidence;
- retry only through the attended Capture Service entry point;
- query by correlation ID before every repeated write.

If a write may have succeeded but readback failed, the next attempt must query for the correlation ID before issuing another write.

## Idempotency controls

The correlation ID is the canonical capture idempotency key.

Required invariants:

- one correlation ID maps to at most one durable Universal Inbox record;
- repeated identical payloads with the same correlation ID return the existing record;
- a repeated correlation ID with contradictory content fails closed for operator review;
- local pending state cannot be rebound to a different correlation ID or payload digest;
- provider success is not inferred from local state alone.

## Data handling

Local runtime state may retain only what is required for retry, outbox state, leases, and evidence. It is not business or release authority.

Secrets, provider tokens, and private signing material must never be stored in capture payloads, logs, receipts, or the Universal Inbox. Logs must prefer correlation IDs, record IDs, stage names, and content digests over raw content.

## Provider and autonomy boundaries

The Capture Service may write only to the authoritative Notion Universal Inbox under the current attended A2 reversible-internal boundary.

It may not:

- write directly to Todoist;
- authorize an execution plan;
- add inferred tasks or outcomes;
- change Notion schemas;
- create calendar events;
- send email or messages;
- delete provider records;
- perform live network operations;
- activate releases or modify release authority.

Any downstream provider work requires the separate canonical planning, attended authorization, guarded execution, readback, and reconciliation sequence.

## Operator verification

For a capture verification test:

1. Use a unique test correlation ID.
2. Submit one attended test capture.
3. Verify one Universal Inbox record exists with the exact correlation ID.
4. Verify the returned durable record ID matches provider readback.
5. Repeat the same request with the same correlation ID.
6. Verify the existing record is returned and no duplicate is created.
7. Confirm no Todoist, calendar, email, messaging, deletion, or other provider write occurred.
8. Remove or archive the test record only through an explicitly authorized provider action.

## Observability

Capture telemetry must expose:

- correlation ID;
- capture source;
- pending, writing, readback, completed, or failed state;
- provider record ID after durable readback;
- retry count;
- idempotent replay count;
- duplicate-prevention result;
- stage latency;
- sanitized failure classification;
- deployed driver version and checksum.

Raw capture content should not be emitted in normal telemetry.

## Recovery

If the current Capture Service becomes unavailable:

- preserve local pending state and original correlation IDs;
- stop before any unverified provider write;
- restore the currently Active v6.5 production package and driver configuration from GitHub release evidence;
- verify Notion connectivity and Universal Inbox schema compatibility;
- replay pending captures individually through the idempotent attended path;
- verify each durable record by readback.

The immutable v6.2.0 rollback remains available for governed release recovery. This runbook does not authorize invoking rollback.

## Promotion and metadata transition

Before this runbook becomes the production Automation Register target:

- the exact GitHub commit containing this file must be immutable and validated;
- the deployed Capture Service version and checksum must be recorded;
- production readback and duplicate-prevention tests must pass;
- the Automation Register must be updated to the immutable GitHub URL;
- the write must be verified by immediate Notion readback;
- the existing Drive link must not be removed until its GitHub replacement is confirmed readable.

Updating the Automation Register does not by itself activate v7 or expand Capture Service authority.
