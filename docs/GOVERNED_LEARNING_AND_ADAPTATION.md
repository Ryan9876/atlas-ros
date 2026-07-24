# Governed Learning and Adaptation Engine

Milestone 7 adds a bounded, attended learning layer over Canonical Intelligence Records.

## Controls

- Only `LearningEvent` records marked `learning_eligible=true` participate.
- A minimum evidence sample and minimum observed confidence change are required.
- Confidence changes are bounded by policy and clamped to valid probability limits.
- Proposals remain drafts until explicitly approved.
- Applied updates preserve prior values and issue deterministic rollback tokens.
- Rollback never deletes outcome evidence or source learning events.
- Longitudinal quality evaluation reports eligibility, approval, confidence gain, and rollback rates.

This milestone does not autonomously alter production models, policies, integrations, or release authority.
