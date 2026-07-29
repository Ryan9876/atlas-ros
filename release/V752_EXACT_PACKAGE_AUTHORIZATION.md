# Atlas ROS v7.5.2 Exact-Package Authorization

## Status

`AWAITING RYAN AUTHORIZATION`

This document defines the only package covered by a future promotion authorization. It is not itself authorization.

## Exact authorization block

Authorize the attended promotion of **Atlas ROS v7.5.2** using only the following exact package:

- Package source commit: `b9ff553e7c53d735b91e6d535f8daafa28f97076`
- Pull request: `Ryan9876/atlas-ros#94`
- Candidate workflow run: `30484168542`
- Retained GitHub Actions artifact ID: `8736952867`
- Artifact name: `atlas-ros-v752-clarification-evaluation-b9ff553e7c53d735b91e6d535f8daafa28f97076`
- Artifact archive SHA-256: `e8d5eb816d332874daf214b4e326952d958f2ab7820d46039057dda9149456ee`
- Source distribution: `atlas_ros-7.5.2.tar.gz`
- Source distribution SHA-256: `0b3ba57b26a8d9709a6df6f9b1de0105d0c181e2740d89a9d2dae5c2b4afbca1`
- Wheel: `atlas_ros-7.5.2-py3-none-any.whl`
- Wheel SHA-256: `039221d810850d424c10754a0ba38b60f63f55a32c853f28f7ac6415d8a74281`
- SPDX SBOM SHA-256: `40ca8133d02990cedb30eb364c8e323ecdafc32be6767059c63990db12e47000`
- Source manifest SHA-256: `90da5a0fd71ad10305235f3d5955fb297cf25a349db2cb6132b9f4a27c8b14f8`
- Validation receipt SHA-256: `d021e51abae05e7bab3c1350925fe1547df69926b714affdfbe15123db8dc92d`
- Draft immutable manifest: `release/RELEASE_MANIFEST_V752_DRAFT.md`
- Draft immutable manifest SHA-256: `a1bc6b6a3abae0fdf08202a4e40c520194ca91b09c212f3dbb60d2f1c0c2fabc`
- Proposed post-promotion immediate rollback: Atlas ROS v7.5.1 at `379892900e1c82f84a6716f46a8180d83c836aa7`
- Governing Decision to create: `V752-production-promotion`
- Promotion Review to create: `V752-exact-package-promotion-review`
- Production Notion schema migration: None

The attended promotion may merge the reviewed PR, publish the exact retained artifacts without rebuilding, create the immutable v7.5.2 release tag, verify publication, update GitHub authority and Release Index, update Notion System State after GitHub verification, and perform final live readback.

The authorization does not permit substitutions, rebuilding, changed digests, changed rollback, changed integration scope, credential changes, unrelated provider writes, deletion, messaging, calendar operations, or unattended execution.

## Authorization wording

Ryan may authorize this package by stating:

> I authorize promotion of the exact Atlas ROS v7.5.2 package identified in `release/V752_EXACT_PACKAGE_AUTHORIZATION.md`.

Any change to an identifier or digest above invalidates the authorization.
