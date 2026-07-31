# Atlas ROS v8.0.0 Delegation and Follow-up Cookbook

## Version boundary

This section applies only to the Atlas ROS v8.0.0 candidate and later releases that explicitly retain the contract. Atlas ROS v7.8.0 remains the Active authority until v8.0.0 is published, independently verified, and separately activated.

## Safety boundary

Interpretation does not authorize execution. Planning does not authorize execution. Adapters cannot create execution intent. Provider writes require the existing attended and governed authorization path. Natural-language inference does not expand permissions or execution scope. The normalizer produces only a typed proposed lifecycle command and cannot invoke Notion, Todoist, or any other provider.

## Explicit command syntax

Existing explicit commands remain supported unchanged:

```text
@atlas delegate: Tina
outcome: Provide firewall findings
done-when: Findings documented
follow-up: Friday
```

Optional separate delivery timing is expressed as `delegate-due:`. `follow-up:` is always Ryan's checkpoint and is never silently substituted for the delegate's delivery due date.

## Natural task-update syntax

A natural update qualifies only when it contains explicit ownership language, one uniquely identifiable responsible person, an expected outcome, and completion criteria. Recognizing a written name is not identity resolution: the name must resolve to exactly one governed person identity in the authoritative operational snapshot before provider planning can proceed.

```text
Bill J is handling Workday access request 276412207.
Expected outcome: Access is approved.
Done when: Bill confirms completion.
Follow up Monday.
```

The normalized proposal is an existing typed `delegate` command. The current `CommandLifecycleService`, Delegated Work planning, Todoist checkpoint planning, idempotency, reconciliation, authorization, execution, and readback paths remain authoritative.

## Required minimum information

A qualified delegation requires:

1. Explicit ownership evidence such as `delegated to`, `assigned to`, `owns`, `is handling`, or `responsible for`.
2. A uniquely identifiable responsible person whose governed provider identity resolves exactly once.
3. The expected outcome.
4. Completion criteria, normally introduced by `Done when:` or `Completion criteria:`.

A person's name alone is not ownership evidence, and a capitalized name alone is not a resolved provider identity. Unresolved or multiply matched identities fail closed.

## Delegate and accountable owner

The **delegate** is responsible for producing the delegated outcome. The **accountable owner** remains accountable for the parent outcome and management follow-through. Natural-language recognition does not transfer Ryan's accountability or close the parent Action Record.

## Delegate due date and Ryan follow-up date

These are separate typed fields:

```text
Bill is handling Workday access request 276412207.
Expected outcome: Access is approved.
Done when: Bill confirms completion.
Bill due: Friday
Follow up: Thursday
```

The delegated outcome due date is Friday. The Ryan-owned Todoist checkpoint is due Thursday. When one date is present and its meaning is not explicitly established, Atlas fails closed and requests clarification. When the compiled policy explicitly allows an undated follow-up, the Todoist checkpoint may remain undated; the delegate due date is still not copied into it.

## Positive examples

The following normalize to `delegate`:

```text
Bill J is handling Workday access request 276412207.
Expected outcome: Access is approved.
Done when: Bill confirms completion.
Follow up Monday.
```

```text
Bill is handling Workday access request 276412207.
Expected outcome: Access is approved.
Done when: Bill confirms completion.
Bill due: Friday
Follow up: Thursday
```

```text
Delegated to Bill.
Expected outcome: Workday access is approved.
Done when: Bill confirms the approval is complete.
Follow up: Monday
```

## Negative examples

The following do not establish delegation and produce no provider plan:

```text
Bill reviewed the request.
```

```text
Discussed the request with Bill.
```

```text
Bill may be able to handle this.
```

```text
Bill may take this.
```

`Waiting for Bill to respond.` normally normalizes to `waiting-on`, not `delegate`.

## Clarification behavior

`Delegated to Bill.` is blocked because the expected outcome and completion criteria are missing. `Bill may take this.` is tentative and produces no delegation transition. A sentence containing an unlabeled date is blocked when Atlas cannot determine whether it is the delegate due date or Ryan follow-up checkpoint. Provider planning remains zero until every material blocker is resolved.

## Generated Delegated Work record

A qualified delegation plans one authoritative Notion Delegated Work upsert containing the delegate, governed delegate identity, accountable owner, governed accountable-owner identity, expected outcome, completion criteria, delegated date, delegate due date, Ryan follow-up checkpoint, acceptance status, effective state, parent Action Record, source update, provenance, command digest, idempotency identity, Todoist checkpoint identity and URL after readback, and latest reconciliation state. Notion remains the system of record for management state.

The v8.0.0 migration is additive and remains unapplied until the exact release is authorized and activated. Existing v7.8.0 production schemas remain unchanged before activation.

## Generated Todoist checkpoint

A planned checkpoint remains Ryan-owned and names the followed parent outcome:

```text
Follow up with Bill J on Workday access request 276412207
```

A generic task such as `Follow up with Bill J` is invalid. The checkpoint uses the explicit Ryan follow-up date and is mapped only after the actual Delegated Work URL is returned by Notion readback. The Todoist description links that verified Notion URL; a parent Action Record URL or predicted URL is not an acceptable substitute. The checkpoint remains undated only when compiled policy permits it.

## One-active-checkpoint rule

The planner closes the obsolete active Ryan checkpoint before upserting its successor. The resulting projection permits at most one active Ryan-owned checkpoint for the delegated outcome. The parent outcome remains open.

## Idempotency and replay

The normalized command is digest-bound to the exact source record, source revision, source update, lifecycle fields, and ambiguity state. Replaying the same update produces the same command digest, provider operation identities, and zero duplicate provider writes. A changed follow-up checkpoint creates a successor projection and replaces the obsolete checkpoint rather than adding an uncontrolled duplicate.

## Reconciliation

Readback verifies the Notion record identity and actual URL, command digest, idempotency identity, Todoist parent identity, checkpoint content, due date, and exact authoritative-record URL link. After a partial failure, reconciliation reads back by stable identities before retrying. A write that may already have succeeded is never repeated merely because readback failed.

## Provider-write plan example

A qualified update may produce an unexecuted plan with:

1. `notion:upsert_delegated_work` for the stable Delegated Work identity.
2. Zero or more `todoist:complete_obsolete_checkpoint` operations for known obsolete checkpoints.
3. One `todoist:upsert_current_checkpoint` operation containing the parent outcome and explicit follow-up due date.

The plan has no execution authority. An exact attended authorization must bind the plan before adapters may write.

## No-provider-write examples

No provider write is allowed when ownership is tentative, a person is merely mentioned, the responsible identity is unresolved, the expected outcome is absent, completion criteria are absent, a material date meaning is ambiguous, the parent outcome is unresolved, or attended authorization is absent.

## Candidate expansion beyond v8.0.0

The development candidate adds ordinary Todoist comment ingestion and bounded phrases such as `Kweku is going to document what happened` and `I need to follow up with him on Monday`. Same-comment pronouns require exactly one antecedent. Derived outcomes, completion criteria, and dates are labeled by origin and require attended approval. This section is not v8.0.0 production authority.
