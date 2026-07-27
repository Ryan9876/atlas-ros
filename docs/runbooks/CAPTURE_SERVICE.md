# Capture Service Operator Runbook

## Status

Current, version-neutral operating guidance for the attended Capture Service. This runbook describes the production boundary without changing provider permissions, automation scope, scheduling, or release authority.

## Production authority

- Atlas ROS release authority is determined by the active release manifest and live System State.
- The Capture Service is an attended, reversible-internal automation.
- The current production driver is Raycast Capture 1.1.5.
- The authoritative business destination is the Notion Universal Inbox.
- Local runtime storage is retry and outbox state only; it is not canonical business authority.

## Capture contract

Every capture must preserve one correlation ID from initial acceptance through local persistence, provider delivery, readback, retry, and reconciliation.

Required input fields:

- content;
- source;
- optional due-date input;
- optional delegation input;
- optional additional context.

The repository Capture Service creates a typed capture, persists it to `pending_capture`, and creates a corresponding `outbox_event` in the same local database transaction. It must not report provider delivery merely because local persistence succeeded.

## Required execution sequence

1. Accept an attended capture request.
2. Validate that required content is present.
3. Create or reuse the capture and correlation IDs.
4. Persist the pending capture and outbox event atomically.
5. Deliver through the approved Notion adapter or deployed Raycast driver.
6. Query the authoritative destination using the original correlation ID.
7. Confirm the durable Notion record ID and expected canonical content.
8. Mark local outbox state complete only after readback succeeds.
9. Retain the original payload and IDs when delivery or readback fails.

## Idempotency

- The correlation ID is the primary duplicate-prevention key.
- Retries must reuse the original correlation ID and payload.
- A retry must query the authoritative destination before creating another record.
- A matching existing record is treated as an idempotent completion, not a new write.
- Never generate a replacement correlation ID to bypass a failed transaction.

## Success criteria

A capture is complete only when all of the following are true:

- the local pending input was durably recorded;
- the provider operation completed or an existing matching record was found;
- the authoritative Notion record was read back;
- the readback preserves the correlation ID and expected content;
- the local outbox state reflects the verified provider result.

Local persistence without provider readback is pending, not successful.

## Failure handling

On local database failure:

- report failure;
- do not attempt provider delivery;
- do not claim capture acceptance.

On provider or network failure:

- retain the retry-safe pending capture and outbox payload;
- preserve the original IDs;
- retry through the attended execution path;
- do not create an untracked manual duplicate.

On readback mismatch:

- mark the transaction blocked;
- retain both write and readback evidence;
- do not report success;
- require operator review before any corrective write.

## Observability

Record, without sensitive payload disclosure:

- capture ID;
- correlation ID;
- source;
- local persistence result;
- outbox state;
- provider operation result;
- provider record ID;
- readback result;
- retry count;
- final completion state.

## Security and authority boundaries

- No autonomous capture scheduling.
- No provider write without an attended capture request and approved adapter path.
- No calendar, email, messaging, deletion, or live-network authority.
- The adapter may translate and write; it may not plan, authorize, change responsibility, or add work.
- The reconciliation path may verify and repair state but may not create new execution intent.

## v7 migration boundary

The v7 candidate introduces a canonical coordinator, immutable authorization contracts, exact execution transactions, and mandatory provider readback. Until v7 is separately promoted, the current production release and deployed driver remain authoritative. Candidate code, branch state, and simulation receipts must not be presented as production execution evidence.

## Verification checklist

- Confirm the active release and rollback through Atlas initialization.
- Confirm the Automation Register identifies this immutable runbook URL.
- Confirm the deployed driver version and checksum are recorded.
- Submit one attended test capture using a unique correlation ID.
- Verify one durable Universal Inbox record.
- Verify retrying the same correlation ID does not create a duplicate.
- Verify local completion occurs only after provider readback.
