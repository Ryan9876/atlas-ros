from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from atlas_ros.contracts import EvidenceSignal
from atlas_ros.domain.models import OperatingContext, ResponsibilityDomain


@dataclass(frozen=True)
class IntentAssessment:
    context: OperatingContext
    confidence: float
    evidence: tuple[EvidenceSignal, ...]
    ambiguity: str = ""


class ManagerIntentInferer:
    """Infers operating context as a supporting signal, never sole routing authority."""

    def __init__(self, config: dict[str, Any]) -> None:
        self._config = config

    def infer(
        self,
        content: str,
        responsibility_domain: ResponsibilityDomain,
    ) -> IntentAssessment:
        normalized = " ".join(content.casefold().split())
        scores: dict[str, float] = {}
        evidence: dict[str, list[EvidenceSignal]] = {}
        for context, policy in self._config["operating_contexts"].items():
            score = 0.0
            signals: list[EvidenceSignal] = []
            if responsibility_domain.value in policy.get("responsibility_domains", []):
                score += 2.5
                signals.append(
                    EvidenceSignal(
                        category=f"operating_context:{context}",
                        signal=f"responsibility:{responsibility_domain.value}",
                        weight=2.5,
                    )
                )
            for phrase in policy.get("phrases", []):
                normalized_phrase = " ".join(str(phrase).casefold().split())
                if normalized_phrase in normalized:
                    score += 2.0
                    signals.append(
                        EvidenceSignal(
                            category=f"operating_context:{context}",
                            signal=str(phrase),
                            weight=2.0,
                        )
                    )
            scores[context] = score
            evidence[context] = signals

        ranked = sorted(scores, key=lambda item: -scores[item])
        winner = ranked[0]
        winner_score = scores[winner]
        runner_score = scores[ranked[1]] if len(ranked) > 1 else 0.0
        if winner_score <= 0:
            return IntentAssessment(OperatingContext.UNRESOLVED, 0.0, ())

        confidence = round(
            min(
                0.99,
                0.5 + winner_score * 0.1 + (winner_score - runner_score) * 0.05,
            ),
            4,
        )
        minimum = float(self._config["confidence"]["context_minimum"])
        if confidence < minimum:
            return IntentAssessment(
                OperatingContext.UNRESOLVED,
                confidence,
                tuple(evidence[winner]),
                "Operating-context evidence is below the governed confidence threshold.",
            )
        ambiguity = ""
        if runner_score > 0 and winner_score - runner_score < 1.0:
            ambiguity = f"Operating context is close between {winner} and {ranked[1]}."
        return IntentAssessment(
            OperatingContext(winner),
            confidence,
            tuple(evidence[winner]),
            ambiguity,
        )
