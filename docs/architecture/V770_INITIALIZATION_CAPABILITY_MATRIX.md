# Atlas ROS v7.7.0 Initialization Capability Matrix

| State | Permitted capability | Exact target source | External read | Retry eligibility |
|---|---|---|---:|---|
| `READING_AUTHORITY` | `github.authority.read` | Fixed `governance/AUTHORITY.json@HEAD` | 1 | One transient retry |
| `READING_RELEASE_INDEX` | `github.release_index.read` | Path from live authority at `HEAD` | Cold only | One transient retry |
| `READING_IMMUTABLE_MANIFEST` | `github.immutable_manifest.read` | Path and commit from live authority | Cold only | One transient retry |
| `READING_SYSTEM_STATE` | `notion.system_state.read` | URL from live authority | 1 | One transient retry |
| `READING_INTEGRATION_INVENTORY` | `notion.integration_inventory.read` | Reference from immutable manifest | 1 | One transient retry |
| `CHECKING_CONNECTOR_LIVENESS` | `todoist.connector_liveness.read` | Fixed Todoist liveness target | 1 | One transient retry |
| Any terminal state | None | None | 0 | Never |

## Explicitly denied capabilities

The operation denies the following before provider execution in every state unless a future release adds an explicit governed state and target:

- generic GitHub repository search;
- arbitrary GitHub file reads;
- plugin or skill discovery;
- Google Drive reads;
- Notion workspace search;
- Todoist writes;
- email, messaging, calendar, and scheduling;
- credential or connection changes;
- deletion and schema changes;
- publication and authority changes;
- arbitrary web search;
- intent-memory and intent-user-control functions;
- profile loading;
- communication-policy compilation;
- situational-playbook selection;
- provider-backed diagnostics and telemetry.

## Call-budget invariants

| Path | GitHub | Notion | Todoist | Total external reads |
|---|---:|---:|---:|---:|
| Clean cold | 3 | 2 | 1 | 6 maximum and expected |
| Clean warm | 1 | 2 | 1 | 4 expected |
| Warm rejection to cold | 3 | 2 | 1 | 6 expected |
| Any path after terminal | 0 | 0 | 0 | 0 executed |

A single transient retry may increase attempted reads by one. The retry must use the same capability and target, receive no authoritative content on the failed attempt, and occur before terminal state.
