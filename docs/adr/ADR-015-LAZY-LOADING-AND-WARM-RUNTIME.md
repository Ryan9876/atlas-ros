# ADR-015 — Verified Lazy Loading and Optional Warm Runtime

## Status

Accepted for the Atlas ROS v7.1.0 candidate.

## Context

Ordinary status and capture operations must not pay import or initialization costs for release tooling, migration packages, scenario analysis, or provider adapters. Optional acceleration must not become authority or cache mutable provider truth.

## Decision

The CLI uses explicit command-to-capability bindings and loads optional modules only after command selection. Production entry points cannot import release, migration, legacy, or provider packages. Startup tests measure wall time, Atlas module count, and process memory.

An optional local warm cache may store only compiled policy, validated catalogs, schemas, capability metadata, and immutable authority snapshots. It is authenticated, TTL-bound, digest-bound, entry-budgeted, disposable, non-authoritative, and provider-write disabled. It may not store authorization, execution intent, mutable provider truth, permanent system-of-record data, or stale integration state.

Cold initialization remains complete and canonical. Warm and cold paths must produce equivalent canonical results.
