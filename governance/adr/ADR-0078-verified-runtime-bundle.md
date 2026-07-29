# ADR-0078 — Verified Runtime Registry Bundle

## Status

Proposed for v7.4.5 candidate validation.

## Decision

Candidate packaging may compile governed policy, contract, capability, schema, command-binding, and dependency registries into a deterministic `VerifiedRuntimeBundleV1`. The bundle binds architecture identity, source commit, package version, compiler versions, source-file digests, registry digests, and one bundle digest.

At runtime, Atlas verifies all identities before use. A rejected or missing bundle falls back to canonical source compilation when safe. Atlas fails closed when neither path validates. The bundle is an immutable package optimization artifact and never becomes release, policy, provider, authorization, or execution authority.

Candidate validation must prove byte-semantic equivalence of bundle and source compilation for registry contents, digests, command bindings, dependencies, and policy behavior.
