# Classification Intelligence Standard

## Purpose

This standard governs responsibility-first classification, explanation, manager-intent inference, confidence, challenge handling, compatibility, and controlled cutover for ATI-1.

## Classification dimensions

Atlas must represent these dimensions independently:

1. Record classification
2. Responsibility domain
3. Desired outcome
4. Management workstream
5. Activity summary
6. Operating context
7. Provider destination

A technical activity does not establish Operational Stewardship by itself. Atlas first determines why Ryan owns the outcome.

## Evidence and precedence

Evidence is structured as a category, matched signal, weight, and authorized source. Explicit people, project, operational, dependency, development, decision, risk, and ownership evidence outranks inferred operating context. Hierarchy resolves equal responsibility scores in this order: People Leadership, Project Delivery, Operational Stewardship, External Dependency, Capability Building.

Ambiguous or insufficient evidence must produce a governed clarification or compatibility fallback. It must not silently create certainty.

## Explainability

A user-facing explanation must identify the selected workstream, state the decisive evidence in plain language, disclose material ambiguity, avoid unsupported certainty, and avoid exposing hidden chain-of-thought, secrets, credentials, private messages, or unrelated personal context.

Structured decisive evidence is retained separately from the concise explanation for audit and tuning.

## Manager intent

Supported operating contexts are People Leader, Project Manager, Operations Manager, Strategic Planner, Individual Contributor, and Executive. Context has its own confidence and evidence. It is supporting evidence only and cannot independently select a provider destination.

## Challenge lifecycle

A classification may be unchallenged, accepted, challenged, corrected, or unresolved. Corrections append governed evidence and must not destructively rewrite the historical reasoning record.

## Compatibility and activation

Reasoning contract version 2 projects explicitly to version 1. W02 defaults to legacy authority. Shadow and attended modes do not change routing. Semantic mode is development-only until a separately authorized production promotion.
