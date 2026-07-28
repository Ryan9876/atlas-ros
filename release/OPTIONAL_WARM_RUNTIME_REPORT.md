# Optional Warm Runtime Foundation — v7.1 Candidate

The warm runtime is justified only as an optional local cache for expensive validated read-only material. It is authenticated, TTL-bound, source-digest-bound, restart-safe, disposable, file-permission restricted, bounded, non-authoritative, and provider-write disabled.

It may cache compiled policy, validated catalogs, schemas, capability metadata, and immutable authority snapshots. It may not cache authorization, execution intent, mutable provider truth, permanent system-of-record data, or stale integration state. Cold CLI behavior remains canonical and fully supported.
