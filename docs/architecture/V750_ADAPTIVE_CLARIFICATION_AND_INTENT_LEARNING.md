# Atlas ROS v7.5 Adaptive Clarification and Intent Learning

## Governing principle

Do not confuse shared subject matter with shared completion.

A duplicate may be declared only when the proposed and existing work are substantially equivalent across intended outcome, scope, Definition of Done, accountable owner, current Ryan-owned management action, execution evidence, and completion boundary. The decisive test is: **Would completing the existing record necessarily satisfy the new capture?**

## Relationship classifications

- `exact_duplicate`
- `paraphrased_duplicate`
- `related_but_non_equivalent`
- `materially_distinct_outcome`
- `needs_clarification`

Shared project, systems, devices, wording, stakeholders, or technical implementation are evidence of relationship, not proof of duplication.

## Adaptive clarification

Clarification is an attended reasoning mechanism. Contextual familiarity is assessed separately for user, domain, project, terminology, evidence recency, and interpretation consistency. A generally familiar user does not imply familiarity with a new project, vendor, term, responsibility boundary, or request type.

Evidence behavior:

1. **Minimal:** ask before routing when ambiguity affects the outcome.
2. **Partial:** state the likely interpretation and ask for confirmation when consequential.
3. **Strong:** infer from attributable, relevant, recent, consistent evidence unless material ambiguity remains.
4. **Confirmed pattern:** proceed for low-risk reversible cases; clarify contradictions, exceptions, new outcomes, and consequential changes.

User corrections are high-value evidence. Current explicit instruction and live authority always outrank learned patterns. Stale, contradictory, unrelated, or speculative personal evidence is excluded.

## Clarification processing

When clarification is required Atlas:

1. preserves the original capture;
2. links related records;
3. does not mark it duplicate;
4. assigns `Needs Clarification` or the governed equivalent;
5. records the unresolved material distinction;
6. asks one focused question that demonstrates existing understanding;
7. prohibits Todoist creation and execution authorization;
8. resumes classification only after a confirmed response;
9. stores the confirmed interpretation as attributable contextual evidence.

Clarification never authorizes execution. Adapters cannot plan or authorize. Planning cannot authorize. Reconciliation cannot create successor intent.

## ANX regression case

Existing work:

1. Define a standard naming convention for ANX customer devices.
2. Install SNMP discovery probes in LIT and ALL to capture customer-device information in the CMDB.

New capture: `centrally manage ANX customer devices`.

Required result: link both existing records as related evidence, preserve the capture, classify it as `needs_clarification`, and ask whether centralized management is a separate outcome covering configuration, lifecycle, access, operational control, platform evaluation, automation, or monitoring beyond inventory discovery. Naming and discovery do not necessarily satisfy centralized management.

## Observability

Every decision records the original capture, related records, candidate interpretations, material distinction, evidence level, contextual familiarity, consequence and reversibility, clarification status and question, confirmed response, final classification, resulting governed records, and provider-write count. Planning and validation evidence must remain deterministic and provider-write free.

## Schema proposal

No production schema mutation is included in the candidate implementation. The minimum proposed additive fields for a separately authorized migration are:

### Universal Inbox

- `Relationship Classification` — select
- `Related Record URLs` — rich text or relation
- `Clarification Status` — select
- `Clarification Question` — rich text
- `Clarification Reason` — rich text
- `Interpretation Evidence` — rich text

### Review Records or operational evidence store

- `Evidence Strength` — select
- `Context Familiarity` — rich text or deterministic JSON attachment
- `Clarification Response` — rich text
- `Clarification Confirmed At` — date
- `Final Classification` — select

Do not add all proposed fields automatically. Final field placement and types require live schema review, exact migration authorization, additive application, and readback.

## Historical review

Previously archived captures are not reopened automatically. A future attended read-only/proposal-only review may identify candidates whose duplicate rationale lacks completion-equivalence evidence. Any record modification requires separate authorization.

## Rollback

Rollback is non-destructive:

1. disable the v7.5 clarification policy and restore the v7.4.5 decision path;
2. retain all clarification evidence and confirmed responses;
3. leave additive fields unused if a later migration was separately approved;
4. preserve all records and immutable release history;
5. verify v7.4.5 clean restoration and provider-write count zero.
