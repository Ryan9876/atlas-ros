# Governed Candidate Preparation

Milestone 9 adds an evidence-packet layer that determines whether a validated development build may be proposed as a release Candidate.

## Guarantees

- Mandatory validation gates are enumerated by fixed policy.
- Missing, failed, or not-run blocking gates prevent candidate proposal.
- Governed review is explicit and changes-required findings block proposal.
- Independent review remains preferred when another qualified reviewer is available.
- A solo maintainer may satisfy the governed-review gate only through a documented self-review checklist with durable evidence.
- Artifact digests are SHA-256 bound and independently verifiable.
- Candidate evidence packets have deterministic fingerprints.
- A `proposable_candidate` decision never authorizes promotion.

## Governed review paths

### Independent review

An eligible reviewer other than the pull-request author reviews the candidate, records a disposition, documents findings, and supplies a durable evidence reference.

### Solo-maintainer review

When no independent reviewer is reasonably available, the sole maintainer may complete the review. This path is valid only when all of the following are true:

1. The policy explicitly allows solo-maintainer review.
2. The maintainer identity matches the configured authority when an identity is configured.
3. The review disposition is recorded.
4. Checklist evidence is supplied and retained with the candidate evidence packet.
5. The checklist confirms scope review, changed-file review, test and CI results, artifact integrity, secrets and generated-file inspection, rollback readiness, and promotion-boundary confirmation.
6. Any changes-required finding blocks candidate proposal until corrected and reviewed again.

Solo-maintainer review is not independent review and must never be represented as such. It is an explicit governed exception for a single-maintainer repository.

## Decisions

- `blocked`: one or more required gates, reviews, or readiness conditions are unsatisfied.
- `development_complete`: integrated development evidence is complete but candidate policy is not satisfied.
- `proposable_candidate`: all fixed gates and governed-review requirements pass; explicit owner approval is still required.

The engine cannot publish, activate, or promote a release.