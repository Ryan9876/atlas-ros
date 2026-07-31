# ADR-0081: Context-Aware Ambiguity Resolution and Clarification

- **Status:** Proposed for Atlas ROS v8.1.0; not active production authority
- **Date:** 2026-07-30

## Context

Atlas ROS fails closed when an instruction is materially ambiguous, but fail-closed behavior alone does not ensure a high-quality interaction. A generic clarification request can discard valid partial understanding, over-focus on an unfamiliar term, delay resolution until the end of a batch, and place unnecessary reconstruction work on the user.

The governing example was `build phase 1 or lew`. The unfamiliar token `lew` occupied a plausible target-entity position, while the connector `or` was structurally inconsistent. The intended instruction was `Build Phase 1 of LEW`, where LEW is a new application.

## Decision

Introduce a provider-free `ContextAwareClarificationAnalyzer` and immutable clarification-analysis and resolution contracts.

The analyzer:

- extracts stable intent before describing uncertainty;
- preserves unfamiliar terms in plausible entity positions;
- evaluates short relationship words as possible transcription errors;
- uses only bounded, approved authoritative context;
- ranks a leading interpretation and material alternatives;
- selects confirmatory, bounded-choice, or information-seeking question forms;
- blocks downstream execution for only the affected item;
- explicitly allows unrelated independent work to continue;
- binds the user response to the exact capture, correlation identity, and analysis digest;
- records zero provider writes.

The capability is deterministic and narrow. It is not an LLM-only correction layer and does not silently normalize materially ambiguous instructions.

## Consequences

- Clarification questions demonstrate partial understanding and minimize user effort.
- Unknown words are not treated as typos merely because no existing record matches them.
- Connector errors such as `or` versus `of` can be ranked without changing a possible entity.
- The affected item pauses while unrelated independent inbox work continues.
- A leading interpretation remains a proposal and cannot authorize planning or execution.
- Original and normalized instructions remain traceable.
- No integration, provider permission, scheduling, messaging, calendar, credential, deletion, or production-authority scope is expanded.

## Rejected alternatives

- **Ask `What does this mean?`:** rejected because it discards stable intent and shifts all reconstruction effort to the user.
- **Treat the unfamiliar word as the typo:** rejected because it damages valid project, application, person, and acronym names.
- **Silently apply the leading correction:** rejected because materially different interpretations may create different records or provider actions.
- **Pause the full inbox batch:** rejected because one ambiguous item should not block unrelated independent work.
- **Persist the resolution as general intent memory:** rejected because transaction-specific clarification evidence does not authorize persistent behavioral memory.
