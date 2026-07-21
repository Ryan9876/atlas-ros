# Threat model

Primary threats are credential disclosure, unauthorized external writes, policy bypass by AI output, sensitive content in telemetry, stale authority data, duplicate writes after ambiguous responses, and rollback corruption. Mitigations are Keychain-only secrets, adapter isolation, default dry-run, structured AI output, deterministic gates, observability allowlists, idempotency IDs, readback, checksum verification, and immutable release/rollback preservation.

