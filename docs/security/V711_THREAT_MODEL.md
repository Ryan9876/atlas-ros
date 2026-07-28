# Atlas ROS v7.1.1 Fast Initialization Threat Model

## Protected assets

Canonical GitHub authority, immutable release identity, rollback identity, System State, Integration Inventory readiness, cache authentication material, initialization receipt integrity, credentials, authorization, execution intent, and provider state.

## Threats and controls

| Threat | Control |
|---|---|
| Cache poisoning or substitution | Authenticated cache, restricted permissions, exact snapshot kind, payload digest, source digest, repository, commit, path, authority-model and document-digest binding |
| Stale authority replay | `AUTHORITY.json` is always read live; any changed immutable identity invalidates the cache |
| TTL bypass | Expiry is verified on every cache read; expired entries use the canonical cold path |
| Release Index or manifest substitution | Both documents are revalidated against live authority digests and deterministic Release Index rendering after cache retrieval |
| Cached mutable provider truth | Allowed snapshot kind stores only immutable authority material; System State, inventory readiness and liveness remain live |
| Cached authorization or execution intent | Prohibited by cache kind, payload design and negative tests; provider writes remain zero |
| Notion projection drift | Literal schema version, required fields, strict extra-field rejection, and agreement checks against live GitHub authority |
| Inventory data-source substitution | Direct reference is bound by the immutable manifest digest; only `collection://` references are accepted before URL fallback |
| Connector liveness spoofing | GitHub and Notion must complete their required live reads; Todoist returns an exact single-name liveness result |
| Partial connector outage hidden | Any missing, extra or false required liveness result blocks initialization with the exact connector |
| Unsafe cache failure | Cache failures never become authority; they fall back to cold validation or block if canonical validation fails |
| Cross-user cache exposure | Existing directory and file permission restrictions remain enforced; authentication token digest is required |
| Timing or receipt data leakage | Receipt contains identifiers, booleans and durations only; no source documents, tokens, credentials or private signing material |
| Broad exception conceals success | The consolidated operation returns `INITIALIZATION_BLOCKED` with the exact condition and never reports READY after an exception |

## Residual risks

Remote connector latency depends on the hosting surface and cannot be proven by an in-process benchmark. Production adapters must implement compact projections and the Todoist read probe faithfully. A cache authentication token remains an operational secret and must not be committed. SHA-256 collision resistance is assumed by the existing authority model.
