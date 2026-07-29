# Atlas ROS v7.5 Exact Release-Candidate Manifest

Status: exact validated candidate; not authorized for immutable publication or production activation.

## Exact package identity

- Candidate version: `7.5.0`
- Exact package source commit: `e5b828d40e63e6d3106ae6bddbcc08b48273f74b`
- Full non-publishing validation run: `30461951342`
- Retained evidence artifact: `8728012606`
- Evidence artifact SHA-256: `60f9a02910564ccf066d47136dc910c793b750c43c70ef264fb709dcec660bc1`
- Source distribution SHA-256: `e6327b2f77e293cad543c6b1fec1d2c8ceff5b3321a05828f586c5b9ef52660d`
- Wheel SHA-256: `037b229c0e0e006202c6cceec916c67313664f1e7ae9a1c2e685bfd10bb729bd`
- SPDX SBOM SHA-256: `a7b35c0851bc2a251a4a0e7abe7cff40350493a285b46f1f28bcbeb5b0ce664c`
- Source manifest SHA-256: `560538e715418a80fe2be595489bd419fb036125ff56cdc8e0655049c9ac38ac`
- Full-validation receipt SHA-256: `4b084a6d96324234720a4864eeb25acf2fb65f3c1f62bf0ac5600b0d6ef5970c`
- Build count: `1`
- Independent repository CI run: `30461951173` — passed
- Active baseline resolved from live authority: Atlas ROS v7.4.5 at `88ccec11df6695b91fc2cc703105c42cd21e9f01`
- Immediate rollback resolved from live authority: Atlas ROS v7.4.0 at `6d48b93c195b7b1761df561760d04aea67d28a55`

## Validation result

The exact candidate passed:

1. repository-wide Ruff validation;
2. strict MyPy validation;
3. architecture and development-boundary validation;
4. 760 automated tests with branch-aware coverage above the required 85% threshold;
5. adaptive clarification and execution-boundary regression tests;
6. source secret scanning with zero findings;
7. locked dependency audits against PyPI and OSV with zero vulnerabilities;
8. build-once wheel and source packaging;
9. source manifest and SPDX SBOM generation;
10. clean installation and runtime verification from both wheel and source distribution;
11. checksum validation and clean restoration of Active v7.4.5 and immediate rollback v7.4.0;
12. non-publishing receipt verification with provider writes `0`.

## Scope

Atlas ROS v7.5 introduces Adaptive Clarification and Intent Learning:

1. duplicate decisions require material completion equivalence;
2. explicit related-but-non-equivalent classification;
3. contextual familiarity and evidence-sensitive clarification;
4. targeted attended clarification questions;
5. governed confirmed-interpretation evidence;
6. execution gating while clarification is unresolved;
7. proposal-only historical duplicate review;
8. non-destructive rollback.

## Production integrations

Required production integrations remain exactly GitHub, Notion, and Todoist. No integration-scope expansion is included.

## Schema state

No production Notion schema migration is required for this candidate. Confirmed interpretation evidence and proposal-only historical duplicate-review findings use existing Review Records fields and page content. No property, record, or historical evidence was removed or rewritten.

## Provider-write and activation state

- Provider writes: `0`
- Todoist writes: `0`
- Production schema migrations: `0`
- Authority changes: `0`
- Releases or tags published: `0`
- Integration-scope expansions: `0`
- Credential actions: `0`
- Messages, email, calendar, or scheduled actions: `0`
- Records deleted: `0`
- Feature enabled by default: `false`

## Rollback

Rollback is non-destructive:

1. disable the v7.5 feature policy;
2. restore the v7.4.5 processing path;
3. preserve Review Records and confirmed user evidence;
4. leave any future additive fields unused rather than removing them;
5. preserve all immutable releases and historical records.

Clean restoration of both v7.4.5 and v7.4.0 was validated from their published release assets.

## Promotion boundary

This exact package is ready for governed promotion review only. Do not publish an immutable tag or GitHub Release, merge or activate production authority, change the immediate rollback, update Notion System State, or enable the feature in production without Ryan's separate exact-package authorization covering the package identity above.
