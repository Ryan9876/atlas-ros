from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from atlas_ros.config.loader import load_config
from atlas_ros.contracts import EvidenceSignal
from atlas_ros.domain.models import (
    Classification,
    ManagementWorkstream,
    ResponsibilityDomain,
)


@dataclass(frozen=True)
class ResponsibilityAssessment:
    classification: Classification
    responsibility_domain: ResponsibilityDomain
    workstream: ManagementWorkstream
    confidence: float
    evidence: tuple[EvidenceSignal, ...]
    ambiguities: tuple[str, ...]
    rationale_basis: str


class ResponsibilityClassifier:
    """Deterministically classifies why Ryan owns an outcome before routing it."""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        self._config = config or load_config("classification-intelligence")
        self._validate_config(self._config)

    def classify(self, content: str, additional_context: str = "") -> ResponsibilityAssessment:
        normalized = self._normalize(f"{content}\n{additional_context}")
        domain_scores: dict[str, float] = {}
        domain_evidence: dict[str, list[EvidenceSignal]] = {}
        domain_config = self._config["responsibility_domains"]

        for domain, policy in domain_config.items():
            signals: list[EvidenceSignal] = []
            score = 0.0
            for phrase, weight in policy.get("phrases", {}).items():
                if self._contains_phrase(normalized, str(phrase)):
                    numeric_weight = float(weight)
                    score += numeric_weight
                    signals.append(
                        EvidenceSignal(
                            category=f"responsibility:{domain}",
                            signal=str(phrase),
                            weight=numeric_weight,
                        )
                    )
            for keyword, weight in policy.get("keywords", {}).items():
                if self._contains_word(normalized, str(keyword)):
                    numeric_weight = float(weight)
                    score += numeric_weight
                    signals.append(
                        EvidenceSignal(
                            category=f"responsibility:{domain}",
                            signal=str(keyword),
                            weight=numeric_weight,
                        )
                    )
            domain_scores[domain] = score
            domain_evidence[domain] = signals

        hierarchy = [str(item) for item in self._config["responsibility_hierarchy"]]
        ranked = sorted(
            domain_scores,
            key=lambda domain: (-domain_scores[domain], hierarchy.index(domain)),
        )
        winner = ranked[0]
        winner_score = domain_scores[winner]
        runner_score = domain_scores[ranked[1]] if len(ranked) > 1 else 0.0

        if winner_score <= 0:
            return ResponsibilityAssessment(
                classification=self._classify_record(normalized),
                responsibility_domain=ResponsibilityDomain.UNRESOLVED,
                workstream=ManagementWorkstream.NEEDS_CLARIFICATION,
                confidence=0.4,
                evidence=(),
                ambiguities=("No governed responsibility signal was found.",),
                rationale_basis="the primary responsibility could not be determined",
            )

        margin = winner_score - runner_score
        confidence = self._confidence(winner_score, margin)
        ambiguities: list[str] = []
        ambiguity_margin = float(self._config["confidence"]["ambiguity_margin"])
        if runner_score > 0 and margin < ambiguity_margin:
            ambiguities.append(
                f"Responsibility evidence is close between {winner} and {ranked[1]}."
            )

        policy = domain_config[winner]
        return ResponsibilityAssessment(
            classification=self._classify_record(normalized),
            responsibility_domain=ResponsibilityDomain(winner),
            workstream=ManagementWorkstream(str(policy["workstream"])),
            confidence=confidence,
            evidence=tuple(sorted(domain_evidence[winner], key=lambda item: -item.weight)),
            ambiguities=tuple(ambiguities),
            rationale_basis=str(policy["rationale"]),
        )


    @staticmethod
    def _validate_config(config: dict[str, Any]) -> None:
        required = {
            "version",
            "responsibility_hierarchy",
            "responsibility_domains",
            "record_classification",
            "operating_contexts",
            "confidence",
            "canonical_mode",
            "explanations",
        }
        missing = sorted(required - set(config))
        if missing:
            raise ValueError(f"classification-intelligence policy missing: {', '.join(missing)}")
        domains = config["responsibility_domains"]
        hierarchy = list(config["responsibility_hierarchy"])
        if set(hierarchy) != set(domains):
            raise ValueError(
                "responsibility hierarchy must contain every configured domain exactly once"
            )
        for domain, policy in domains.items():
            try:
                ResponsibilityDomain(str(domain))
                ManagementWorkstream(str(policy["workstream"]))
            except (KeyError, ValueError) as exc:
                raise ValueError(f"invalid responsibility policy for {domain}") from exc
        for key in ("responsibility_minimum", "context_minimum", "canonical_minimum"):
            value = float(config["confidence"][key])
            if not 0 <= value <= 1:
                raise ValueError(f"confidence threshold {key} must be between zero and one")
        allowed = set(config["canonical_mode"]["allowed_responsibility_domains"])
        if not allowed.issubset(set(domains)):
            raise ValueError("canonical-mode allowlist references an unknown responsibility domain")

    def _classify_record(self, normalized: str) -> Classification:
        policy = self._config["record_classification"]
        order = (
            Classification.DECISION,
            Classification.RISK,
            Classification.PROJECT,
            Classification.DELEGATED_WORK,
            Classification.REFERENCE,
        )
        for classification in order:
            phrases = policy.get(classification.value, {}).get("phrases", [])
            if any(self._contains_phrase(normalized, str(phrase)) for phrase in phrases):
                return classification
        return Classification(str(policy.get("default", Classification.ACTION.value)))

    @staticmethod
    def _normalize(value: str) -> str:
        return " ".join(value.casefold().split())

    @staticmethod
    def _contains_phrase(content: str, phrase: str) -> bool:
        normalized_phrase = " ".join(phrase.casefold().split())
        return normalized_phrase in content

    @staticmethod
    def _contains_word(content: str, word: str) -> bool:
        return re.search(rf"(?<!\w){re.escape(word.casefold())}(?!\w)", content) is not None

    @staticmethod
    def _confidence(winner_score: float, margin: float) -> float:
        raw = 0.55 + min(winner_score, 5.0) * 0.08 + min(max(margin, 0), 3.0) * 0.04
        return round(min(raw, 0.99), 4)
