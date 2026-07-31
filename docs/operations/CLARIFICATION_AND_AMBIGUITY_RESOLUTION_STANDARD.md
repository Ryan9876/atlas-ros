# Clarification and Ambiguity Resolution Standard

Status: v8.1.0 candidate standard; not production-active.

## Purpose

Atlas ROS must demonstrate what it understands before asking the user to clarify an ambiguous instruction. The system must isolate the smallest uncertainty, preserve plausible user-defined entities, propose the strongest supported interpretation, and pause only the affected item.

This standard changes interpretation and attended-workflow behavior. It does not grant planning, provider-write, delegation, scheduling, messaging, or production authority.

## Required analysis

For each potentially ambiguous instruction, determine:

1. Stable intent that can be retained with confidence.
2. The exact token, relationship, entity, owner, outcome, date, or scope that prevents safe processing.
3. The leading complete interpretation supported by grammar and authoritative context.
4. Any materially different alternatives.
5. The smallest question that allows the user to confirm or correct the interpretation.

Do not label the entire instruction ambiguous when only one component is uncertain.

## Entity preservation

An unfamiliar word is not automatically a typo. Preserve it as a possible application, project, program, acronym, person, team, customer, vendor, product, location, workstream, or internal system when it occupies a plausible entity position.

The absence of an authoritative record does not prove that the entity is invalid. It may be new.

## Function-word scrutiny

Evaluate short relationship words such as `of`, `or`, `for`, `to`, `from`, `on`, `in`, `with`, and `and`. A malformed connector may explain the instruction without changing the user-defined entity.

## Bounded context check

Before interrupting the user, check only the approved authoritative sources relevant to the instruction, such as Portfolio Projects, Action Records, Delegated Work, recent inbox captures, people records, and repository terminology.

Do not use Google Drive as authority. Do not conduct an unbounded search. A missing match does not invalidate a possible entity.

## Interpretation ranking

Rank interpretations as:

1. Leading interpretation.
2. Material alternatives.
3. Unsupported possibilities that must not be shown to the user.

Do not manufacture choices merely because other meanings are imaginable.

## Clarification question forms

When one interpretation clearly leads:

> I understand that [stable meaning]. [Entity or term] may be [likely role]. Did you mean: “[normalized instruction]”?

When two interpretations remain materially plausible:

> I understand that [stable meaning]. Did you mean [interpretation A], or [interpretation B]?

When one required fact is missing:

> I understand that [stable meaning]. Which [specific missing field] should I use?

A clarification question must state what ROS understands, identify one material uncertainty, preserve possible entities, minimize user effort, and avoid vague requests to restate the full instruction.

## Timing and partial-item pause

When material ambiguity is identified during attended inbox processing:

1. Bind the analysis to the capture and correlation identity.
2. Mark only that item as requiring clarification.
3. Complete the bounded analysis.
4. Ask at the next safe user-visible interruption.
5. Continue unrelated independent items when safe.
6. Do not wait until the final batch summary unless an atomic transaction must finish first.
7. Do not create downstream execution objects for the affected item.

Clarification is a partial-item pause, not a full-inbox pause.

## Resumption

After the user answers:

1. Read the latest affected record.
2. Bind the answer to the exact capture and analysis digest.
3. Preserve the original instruction unchanged.
4. Record the question, answer, and normalized instruction.
5. Re-run classification and duplicate detection.
6. Route only through the currently approved attended workflow.
7. Reconcile and read back any authorized downstream writes.

Clarification resolves only the identified uncertainty. It is not broader execution authorization.

## Confidence

- High: one interpretation is strongly supported and alternatives do not materially change processing.
- Medium: one interpretation leads, but confirmation is required before downstream action.
- Low: multiple material interpretations remain or required information is missing.

A leading interpretation must never be converted into execution authorization.

## Governing example

Original capture:

> build phase 1 or lew

Required analysis:

- Stable intent: Build Phase 1.
- Possible entity: LEW.
- Ambiguous token: `or`.
- Leading interpretation: Build Phase 1 of LEW.

Required question:

> I understand that you want to build Phase 1, and LEW may be the application name. Did you mean: “Build Phase 1 of LEW”?

The system must not assume `LEW` is the typo merely because it is unfamiliar.

## Preserved boundaries

This capability remains provider-free and attended. It must not:

- create provider writes during analysis;
- infer ownership, due dates, completion criteria, or authorization;
- treat clarification as delegation;
- block unrelated independent items;
- silently rewrite the original capture;
- persist user intent memory without separate authorization;
- modify production authority or immutable releases.
