# v8.3.0 Event Reconciliation Security and Privacy

| Threat | Control |
|---|---|
| Forged or modified webhook | Raw-byte HMAC verification, constant-time comparison, known integration, body-size limit, fail closed |
| Replay or duplicate delivery | Provider delivery identity, canonical identity, semantic snapshot digest, stable idempotency, retained evidence |
| Event ordering or loss | Current-object retrieval, object version/timestamp evidence, bounded incremental backstop |
| Infinite feedback loop | Outbound fingerprint and expected snapshot, causal depth limit, mismatch re-enters reconciliation |
| Privilege or intent escalation | Versioned policy, field authority, exact plan, attended approval binding, adapters cannot authorize |
| Cross-person or shared-workspace impact | Ryan-owned destination checks; delegation and shared work require attended approval |
| Partial provider transaction | Per-mutation receipt/readback, checkpoint preservation, explicit recovery, no false atomicity |
| Secret or sensitive-content exposure | Runtime secret store, no secret/full-comment logging, payload digests instead of durable raw bodies |
| Poison event or worker crash | Durable acceptance, expiring lease, bounded retries, jitter in deployed worker, dead-letter isolation |
| Authority or historical-target drift | Live authority gate and permanent W04 database/data-source rejection |

Retention must be approved before deployment. The recommended baseline is minimum provider metadata and cryptographic digests for audit/replay evidence, with raw bodies held only transiently for verification and parsing. Backup encryption, restore tests, access logging, secret rotation, deletion/retention schedules, and operational ownership are production-activation prerequisites.
