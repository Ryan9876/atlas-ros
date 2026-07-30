# Atlas ROS v8.0.0 Rollback Evidence — Validated Candidate

Status: exact-candidate rollback and restoration evidence passed. This evidence does not authorize publication or activation.

## Authority-bound baseline

The full candidate workflow read live `governance/AUTHORITY.json` from the default branch and resolved:

- Active release: Atlas ROS v7.8.0
- Active immutable commit: `72974d1d7da9f07a4c8a41b73b22c0fae3770268`
- Active manifest: `release/RELEASE_MANIFEST_V780.md`
- Active manifest SHA-256: `6942c315d2379555871af017ed816e207176ff57622f3483d2043dee28310687`
- Active source distribution SHA-256: `c9644b9196fd8d5c43b3fa6211ed1901924401b2f3419711a248dcd8f14105ad`
- Active wheel SHA-256: `c7c8daf6926160334c3947ca7a86496cad9b86c2894abdc4dbe4a56a6cf6125a`
- Current immediate rollback: Atlas ROS v7.7.0
- Rollback immutable commit: `71d849b77a53b8f0ba5a9379ff45b44869756819`

## Verification performed

- Verified `v7.8.0` resolves to the exact Active immutable commit.
- Verified `v7.7.0` resolves to the exact current rollback immutable commit.
- Read the v7.8.0 immutable manifest from its exact commit and verified its authoritative manifest digest.
- Located the v7.7.0 immutable manifest at `release/RELEASE_MANIFEST_V770.md` from its exact commit.
- Downloaded the immutable v7.8.0 and v7.7.0 GitHub Release source and wheel assets.
- Verified the v7.8.0 source and wheel hashes against live authority.
- Verified the v7.7.0 source SHA-256 `4248062fde25dd5ed4cab8700ca7633395bb9bc206986103d4e034089851a715` and wheel SHA-256 `a8c8a56e33e587a491f6dce9ad6e7573371a03d45f8c51bdda6ec97349ce3a38` against its immutable release manifest.
- Recorded exact restoration commits and manifest evidence in retained artifact `8772036696`.

## Result

- v7.8.0 Active restoration verification: **passed**.
- v7.7.0 current rollback-chain verification: **passed**.
- Immutable releases modified: `0`.
- Authority records modified: `0`.
- Provider writes: `0`.

## Activation boundary

Before any future v8.0.0 authority activation, independent publication readback must repeat the v7.8.0 restoration check against the published v8.0.0 package and verify that v7.8.0 becomes the immediate rollback. The additive Notion migration requires no destructive rollback; v7.8.0 ignores the added fields. No v8.0.0 authority activation may occur unless that independent restoration evidence passes.
