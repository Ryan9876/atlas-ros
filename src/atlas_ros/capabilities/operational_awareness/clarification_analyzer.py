"""Final v8.1 analyzer refinements over the deterministic clarification rules."""
from __future__ import annotations

import re

from atlas_ros.contracts.operational_awareness.clarification import (
    AmbiguityCategory,
    ClarificationAnalysisV1,
    ClarificationContextV1,
)

from .clarification import ContextAwareClarificationAnalyzer as _RuleAnalyzer

_PROPER_NOUN_RE = re.compile(
    r"^(?P<verb>(?i:review|prepare|update|assess))\s+(?:the\s+)?"
    r"(?P<entity>[A-Z][A-Za-z0-9_-]*)\s+(?P<object>.+?)[.!?]?$"
)


class ContextAwareClarificationAnalyzer(_RuleAnalyzer):
    """Apply entity-safe normalization while retaining the governed rule engine."""

    def analyze(
        self,
        instruction: str,
        *,
        context: ClarificationContextV1 | None = None,
        context_sources_checked: tuple[str, ...] = (),
        known_entities: tuple[str, ...] = (),
        context_terms: tuple[str, ...] = (),
        candidate_targets: tuple[str, ...] = (),
    ) -> ClarificationAnalysisV1:
        text = self._normalize_space(instruction)
        if not text:
            raise ValueError("clarification analysis requires an instruction")
        proper_noun = _PROPER_NOUN_RE.fullmatch(text)
        if proper_noun is None:
            return super().analyze(
                text,
                context=context,
                context_sources_checked=context_sources_checked,
                known_entities=known_entities,
                context_terms=context_terms,
                candidate_targets=candidate_targets,
            )
        bounded = context or ClarificationContextV1(
            source_refs=self._dedupe(context_sources_checked),
            known_entities=self._dedupe(known_entities),
            context_terms=self._dedupe(context_terms),
            candidate_targets=self._dedupe(candidate_targets),
        )
        entity = self._normalize_entity(proper_noun.group("entity"))
        return self._clear(
            text,
            stable_intent=(self._sentence_case(text.rstrip(".!?")),),
            bounded=bounded,
            category=AmbiguityCategory.POSSIBLE_PROPER_NOUN,
            preserved_entities=(entity,),
            evidence=(
                f"{entity} occupies a grammatically plausible entity position",
                "absence from authoritative context does not prove a typo",
            ),
            score=0.90,
        )

    @staticmethod
    def _normalize_entity(value: str) -> str:
        clean = value.strip()
        if clean.islower() and clean.isalpha() and 2 <= len(clean) <= 5:
            return clean.upper()
        return clean[:1].upper() + clean[1:]
