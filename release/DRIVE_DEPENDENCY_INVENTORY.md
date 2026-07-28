# Google Drive Dependency Inventory — v7.1 Candidate

The deterministic scanner inventories repository references and classifies each as current runtime, startup authority, release authority, restoration, historical reference, migration tooling, documentation only, or obsolete.

Acceptance requires zero current runtime, startup-authority, and release-authority dependencies. Historical references and migration tooling may remain only when isolated from production runtime and clearly non-authoritative.

The machine-readable inventory is generated during validation at `v710-evidence/DRIVE_DEPENDENCY_INVENTORY.json` and is digest-bound. This report does not authorize Drive retirement, deletion, credential revocation, connector removal, or content migration.
