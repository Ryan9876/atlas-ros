# Atlas ROS v7.7.0 Initialization Circuit Breaker Threat Model

## Assets

- Canonical Active and rollback identities.
- Immutable Release Index and manifest integrity.
- Current Notion System State and Integration Inventory.
- Required connector readiness.
- The guarantee that Quick Initialization performs no unauthorized external call or provider write.
- Deterministic receipt evidence used by operators and release validation.

## Trust boundaries

1. Orchestration to operation-scoped authorization.
2. Operation-scoped authorization to provider adapter.
3. Provider response to local validation.
4. Authenticated local cache to immutable validation.
5. Terminal result to downstream rendering, diagnostics, adapters, and agents.

## Threats and controls

### Call injection by orchestration or natural language

**Threat:** A planner, adapter, prompt, or user instruction requests an extra read or a prohibited capability.

**Control:** Capability and state matching occur in code before provider invocation. Unauthorized attempts are rejected and traced with `provider_invoked=false`.

### Target substitution

**Threat:** An approved capability is pointed at an arbitrary repository file, Notion page, or alternate connector target.

**Control:** Exact targets are bound from live authority and the immutable manifest. String mismatch fails closed before invocation.

### Out-of-order authority reads

**Threat:** Dynamic state or liveness is read before immutable identity is established.

**Control:** Explicit transition graph and per-state capability mapping. Invalid transition blocks the operation.

### Budget bypass through retries

**Threat:** Retry loops multiply calls or switch targets.

**Control:** One operation-level retry budget, same call closure and exact target, transient exception allowlist, and pre-call budget enforcement.

### Retrying contradictory content

**Threat:** A digest mismatch or authority contradiction causes repeated provider reads or substitution.

**Control:** Content validation occurs after a successful raw read and is not retry-eligible. The operation blocks.

### Warm-cache poisoning or staleness

**Threat:** Cached immutable documents differ from live authority or accepted schema.

**Control:** Auth token, live source digest, repository, commit, path, and both document digests must match. The documents are revalidated locally. Rejection allows one cold fallback only.

### Post-terminal call

**Threat:** Receipt rendering, telemetry, diagnostics, response generation, or an agent issues another external call after `READY`, `READY_WITH_WARNINGS`, or `INITIALIZATION_BLOCKED`.

**Control:** Terminal states are irreversible. `InitializationAlreadyTerminal` is raised before provider invocation and records operation ID, terminal status, capability, target, reason, and sequence.

### Search-based authority substitution

**Threat:** Failed authority reads fall back to web, repository search, Notion search, Google Drive, memory, or chat history.

**Control:** Those capabilities are absent from the allowed state matrix and explicitly tested as denied.

### Side-effect escalation

**Threat:** Initialization triggers Todoist writes, schema changes, publication, credentials, messages, schedules, or deletion.

**Control:** Read-only ports, explicit denied capabilities, zero-provider-write validation, and package workflow permissions limited to contents/actions read.

### Profile or intent-memory coupling

**Threat:** v7.6 or v7.6.1 adaptive surfaces load during Quick Initialization and broaden behavior or data access.

**Control:** The bootstrap imports only authority contracts, context, digests, circuit-breaker types, and read-only ports. Architecture tests and module-load tests prohibit memory, profile, policy, and playbook imports.

## Residual risks

- A provider implementation could perform hidden side effects inside an ostensibly read-only method. Integration acceptance and least-privilege verification remain required controls outside the package boundary.
- A process crash before receipt emission can prevent a receipt, although the pre-provider trace still constrains calls made through the operation object.
- Clock timing is informational; correctness depends on trace and call counts, not elapsed-time thresholds.

## Security acceptance

Release validation must prove all denied calls are rejected before invocation and that clean cold, warm, blocked, and terminal paths report zero provider writes, zero Google Drive reads, and zero post-terminal executed calls.
