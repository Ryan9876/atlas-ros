# Atlas ROS v5.4.0rc1 Release Notes

This release candidate turns the prior Knowledge Composition and Management Structure skeleton
into a governed, versioned, deterministic framework. It adds a complete Team Operating Model with
14 sections, explicit dependency and context handling, per-value and per-section provenance,
completeness and decision-required states, governance and evidence requirements, and stable
package digests.

Existing V1 APIs remain supported. V2 packages can project to V1 only when the projection is
loss-safe. The release remains non-executing and introduces no provider permissions or writes.

Operators should use the Knowledge and Management V2 runbook and migration guide. Rollback is
Atlas ROS v5.3.0; no external data migration is performed.
