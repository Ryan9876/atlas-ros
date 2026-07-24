from __future__ import annotations

from dataclasses import dataclass, field

from atlas_ros.contracts import (
    ClassificationChallenge,
    ClassificationChallengeReceipt,
    EvidenceSignal,
    ReasoningPackageV2,
)


@dataclass
class ClassificationChallengeService:
    """Applies traceable, idempotent challenge events without rewriting prior evidence."""

    _applied: dict[str, tuple[ClassificationChallenge, ReasoningPackageV2]] = field(
        default_factory=dict
    )

    def apply(
        self,
        reasoning: ReasoningPackageV2,
        challenge: ClassificationChallenge,
    ) -> tuple[ReasoningPackageV2, ClassificationChallengeReceipt]:
        if challenge.correlation_id != reasoning.correlation_id:
            raise ValueError("challenge and reasoning correlation ids must match")

        existing = self._applied.get(challenge.challenge_id)
        if existing is not None:
            existing_challenge, existing_reasoning = existing
            if existing_challenge != challenge:
                raise ValueError("challenge id was already used with different content")
            return existing_reasoning, ClassificationChallengeReceipt(
                challenge_id=challenge.challenge_id,
                correlation_id=challenge.correlation_id,
                applied=False,
                idempotent_replay=True,
                prior_status=reasoning.challenge_status,
                resulting_status=existing_reasoning.challenge_status,
                evidence={"challenge_id": challenge.challenge_id},
            )

        update: dict[str, object] = {
            "challenge_status": challenge.status,
            "decisive_evidence": [
                *reasoning.decisive_evidence,
                EvidenceSignal(
                    category="classification_challenge",
                    signal=challenge.reason,
                    weight=1.0,
                    source=f"challenge:{challenge.challenge_id}",
                ),
            ],
        }
        if challenge.status == "corrected":
            update.update(
                {
                    "responsibility_domain": challenge.corrected_responsibility_domain,
                    "workstream": challenge.corrected_workstream,
                    "rationale": [
                        *reasoning.rationale,
                        (
                            f"Corrected to {challenge.corrected_workstream} through governed "
                            f"challenge {challenge.challenge_id}."
                        ),
                    ],
                }
            )
        elif challenge.status in {"challenged", "unresolved"}:
            update.update(
                {
                    "requires_human_decision": True,
                    "fallback_reason": (
                        f"Classification is {challenge.status} through governed challenge "
                        f"{challenge.challenge_id}."
                    ),
                }
            )

        resulting = reasoning.model_copy(update=update)
        self._applied[challenge.challenge_id] = (challenge, resulting)
        return resulting, ClassificationChallengeReceipt(
            challenge_id=challenge.challenge_id,
            correlation_id=challenge.correlation_id,
            applied=True,
            prior_status=reasoning.challenge_status,
            resulting_status=resulting.challenge_status,
            evidence={"challenge_id": challenge.challenge_id},
        )
