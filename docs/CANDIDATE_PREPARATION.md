# Governed Candidate Preparation

Milestone 9 adds an evidence-packet layer that determines whether a validated development build may be proposed as a release Candidate.

## Guarantees

- Mandatory validation gates are enumerated by fixed policy.
- Missing, failed, or not-run blocking gates prevent candidate proposal.
- Independent review is explicit and changes-required findings block proposal.
- Artifact digests are SHA-256 bound and independently verifiable.
- Candidate evidence packets have deterministic fingerprints.
- A `proposable_candidate` decision never authorizes promotion.

## Decisions

- `blocked`: one or more required gates, reviews, or readiness conditions are unsatisfied.
- `development_complete`: integrated development evidence is complete but candidate policy is not satisfied.
- `proposable_candidate`: all fixed gates and review requirements pass; explicit owner approval is still required.

The engine cannot publish, activate, or promote a release.
