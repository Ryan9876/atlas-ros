# Atlas ROS v7.6.0 Intent Memory Operator Runbook

## Inspection

Inspection may be enabled without inference. Return the interpreted pattern, source, scope, confidence, freshness, contradiction count, eligibility, last use, user-control state, and deterministic digest.

## Correction

1. Confirm Ryan's exact corrected interpretation and scope.
2. Preserve the original evidence unchanged except for corrected and ineligible state.
3. Create a successor evidence record sourced to the current instruction.
4. Produce a deterministic correction record and user-control receipt.
5. Read back both records before comparable future use.

## Retirement

Mark the evidence retired and inference-ineligible, preserve provenance, update the active index, and verify the receipt and index readback.

## Forgetting

A forgetting request immediately excludes evidence from active indexes but does not claim deletion. Live forgetting requires exact authorization naming the evidence and provider targets. After provider mutation, verify absence, retain only the authorized content-free tombstone, and record a readback-verified receipt. Never modify immutable releases or unrelated authority.

## Safe fallback

When disabled, unavailable, stale, contradictory, out of scope, or uncertain, use accepted v7.5.2 clarification behavior and perform no provider write.
