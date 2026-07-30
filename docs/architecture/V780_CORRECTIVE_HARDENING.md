# Atlas ROS v7.8.0 Corrective Hardening

## Status and help semantics

The installed-package `atlas status` surface reports only installed package identity, runtime identity, that live authority was not loaded, and zero provider writes. It does not infer or claim the Active production release. Authority-aware initialization remains a separate fail-closed path.

Root `atlas --help` and `atlas -h` return success. Invoking `atlas` with no arguments prints help and preserves the established no-argument exit behavior. Unknown commands remain errors. Lightweight status and root help do not import provider, intelligence, or release modules.

## Validation diagnostics

Validation selection, tier semantics, fail-fast behavior, and receipt schema remain unchanged. Successful commands remain quiet. On the first failed command, Atlas emits the command label, replays captured stdout to stdout, and replays captured stderr to stderr.

## SQLite permissions

On POSIX systems runtime database directories are restored to `0700`; database, WAL, and SHM files are restored to `0600`. Missing sidecars are ignored. Hardening runs after connection configuration, commit, rollback, initialization, and around close. SQLite WAL mode, locking, and transactions are unchanged. Non-POSIX platforms retain SQLite behavior without asserting POSIX mode bits.

## Governed retries

Adapters remain single-attempt transports. They may expose sanitized integer `Retry-After` delta-seconds on retryable failures, but they do not sleep or retry. HTTP-date values and malformed guidance are ignored to preserve deterministic parsing.

The attended orchestration layer owns attempt limits, delay selection, maximum delay bounds, injected sleeping, retry evidence, and recovery. A valid bounded provider delay is preferred when policy permits; otherwise the configured governed backoff is used. Simulation does not sleep. Uncertain writes always perform readback before another provider write.

## Reconciliation invariant

`successful_write_keys` records an idempotency key only after provider apply returns successfully. A later mismatch or readback exception does not prove the provider write failed, so the key remains. Retry reads back before applying again, preventing duplicate external writes. Checkpoint advancement remains blocked until consistency is verified. The legacy `applied_keys` interface remains a compatibility alias.

## Threat-model changes

The release reduces four risks: stale production-authority claims from installed packages, hidden retry amplification, world-readable SQLite sidecars, and duplicate provider writes after uncertain results. It adds no autonomous execution, async adapter conversion, concurrent writes, production schema migration, credential change, messaging, calendar action, or scheduling.

## Operator recovery

When validation fails, use the stream-correct diagnostic output and retain the failed-command receipt entry. When a provider write result is uncertain, inspect journaled delay and readback evidence and resume the same exact authorized plan only after safe state is established. When SQLite files are recreated, the lifecycle helper restores private modes automatically.
