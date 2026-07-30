"""Provider-free context-aware ambiguity analysis for Atlas ROS v8.1."""
from __future__ import annotations

import re
from dataclasses import dataclass

from atlas_ros.contracts.advisory_v1 import ConfidenceAssessment
from atlas_ros.contracts.operational_awareness.clarification import (
    AmbiguityCategory,
    ClarificationAnalysisV1,
    ClarificationQuestionMode,
    ClarificationResolutionV1,
    InterpretationCandidateV1,
)

_CONNECTOR_RE = re.compile(
    r"^(?P<verb>build|create|prepare|develop|implement)\s+"
    r"(?P<scope>phase\s+\d+)\s+(?P<link>[a-z]+)\s+"
    r"(?P<entity>[a-z][a-z0-9_-]*)$",
    re.IGNORECASE,
)
_FORM_DATE_RE = re.compile(
    r"\bform\s+(?P<date>monday|tuesday|wednesday|thursday|friday|"
    r"saturday|sunday|today|tomorrow)\b",
    re.IGNORECASE,
)
_MOVE_PHASE_RE = re.compile(
    r"^move\s+(?P<scope>phase\s+\d+)\s+to\s+(?P<entity>[a-z][a-z0-9_-]*)$",
    re.IGNORECASE,
)
_MISSING_OWNER_RE = re.compile(
    r"^have\s+(?P<outcome>.+?)\s+completed\s+by\s+"
    r"(?P<date>monday|tuesday|wednesday|thursday|friday|saturday|sunday|"
    r"today|tomorrow|\d{4}-\d{2}-\d{2})$",
    re.IGNORECASE,
)
_CITE_SITE_RE = re.compile(r"\bcite\s+design\b", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class ContextAwareClarificationAnalyzer:
    """Rank narrow interpretations without authorizing planning or execution."""

    def analyze(
        self,
        instruction: str,
        *,
        context_sources_checked: tuple[str, ...] = (),
        known_entities: tuple[str, ...] = (),
        context_terms: tuple[str, ...] = (),
    ) -> ClarificationAnalysisV1:
        text = self._normalize_space(instruction)
        if not text:
            raise ValueError("clarification analysis requires an instruction")

        connector = _CONNECTOR_RE.fullmatch(text)
        if connector is not None and connector.group("link").casefold() == "or":
            return self._connector_error(
                text,
                connector,
                context_sources_checked=context_sources_checked,
            )

        move_phase = _MOVE_PHASE_RE.fullmatch(text)
        if move_phase is not None:
            return self._move_phase_ambiguity(
                text,
                move_phase,
                context_sources_checked=context_sources_checked,
            )

        missing_owner = _MISSING_OWNER_RE.fullmatch(text)
        if missing_owner is not None:
            return self._missing_owner(
                text,
                missing_owner,
                context_sources_checked=context_sources_checked,
            )

        form_date = _FORM_DATE_RE.search(text)
        if form_date is not None:
            return self._form_date_error(
                text,
                form_date,
                context_sources_checked=context_sources_checked,
            )

        if _CITE_SITE_RE.search(text) and self._website_context(
            known_entities=known_entities,
            context_terms=context_terms,
        ):
            return self._cite_site_error(
                text,
                context_sources_checked=context_sources_checked,
            )

        return ClarificationAnalysisV1.create(
            original_instruction=text,
            stable_intent=(text,),
            ambiguity_category=AmbiguityCategory.NONE,
            ambiguous_span=None,
            context_sources_checked=self._dedupe(context_sources_checked),
            candidates=(),
            leading_interpretation=None,
            clarification_required=False,
            question_mode=None,
            clarification_question=None,
            continue_unrelated_work=True,
            downstream_execution_blocked=False,
            confidence=ConfidenceAssessment(
                score=0.95,
                rationale="no material ambiguity rule was triggered",
            ),
            blockers=(),
        )

    def resolve(
        self,
        analysis: ClarificationAnalysisV1,
        *,
        capture_id: str,
        correlation_id: str,
        user_response: str,
        normalized_instruction: str,
    ) -> ClarificationResolutionV1:
        if not analysis.clarification_required or not analysis.clarification_question:
            raise ValueError("only clarification-required analyses can be resolved")
        return ClarificationResolutionV1.create(
            capture_id=capture_id,
            correlation_id=correlation_id,
            analysis_digest=analysis.analysis_digest,
            original_instruction=analysis.original_instruction,
            clarification_question=analysis.clarification_question,
            user_response=self._normalize_space(user_response),
            normalized_instruction=self._normalize_space(normalized_instruction),
            ambiguity_category=analysis.ambiguity_category,
        )

    def _connector_error(
        self,
        text: str,
        match: re.Match[str],
        *,
        context_sources_checked: tuple[str, ...],
    ) -> ClarificationAnalysisV1:
        verb = match.group("verb").capitalize()
        scope = self._title_phase(match.group("scope"))
        entity = self._normalize_entity(match.group("entity"))
        leading = f"{verb} {scope} of {entity}"
        alternative = f"{verb} {scope} for {entity}"
        return ClarificationAnalysisV1.create(
            original_instruction=text,
            stable_intent=(f"{verb} {scope}",),
            ambiguity_category=AmbiguityCategory.CONNECTOR_ERROR,
            ambiguous_span=match.group("link"),
            context_sources_checked=self._dedupe(context_sources_checked),
            candidates=(
                InterpretationCandidateV1(
                    normalized_instruction=leading,
                    rationale=(
                        "the instruction follows an action + phased milestone + relationship + "
                        "target-entity structure, where 'of' is the strongest grammatical fit"
                    ),
                    confidence=0.90,
                ),
                InterpretationCandidateV1(
                    normalized_instruction=alternative,
                    rationale="'for' is grammatical but expresses a less specific relationship",
                    confidence=0.62,
                    material=False,
                ),
            ),
            leading_interpretation=leading,
            clarification_required=True,
            question_mode=ClarificationQuestionMode.CONFIRMATORY,
            clarification_question=(
                f"I understand that you want to {verb.casefold()} {scope}, and {entity} may be "
                f"the application name. Did you mean: \u201c{leading}\u201d?"
            ),
            continue_unrelated_work=True,
            downstream_execution_blocked=True,
            confidence=ConfidenceAssessment(
                score=0.90,
                rationale=(
                    "one connector substitution produces a coherent phased-build instruction "
                    "while preserving the possible entity"
                ),
            ),
            blockers=("Clarification required before downstream routing or execution",),
        )

    def _move_phase_ambiguity(
        self,
        text: str,
        match: re.Match[str],
        *,
        context_sources_checked: tuple[str, ...],
    ) -> ClarificationAnalysisV1:
        scope = self._title_phase(match.group("scope"))
        entity = self._normalize_entity(match.group("entity"))
        schedule = f"Move the {scope} schedule to the {entity} project"
        ownership = f"Transfer {scope} work or ownership to {entity}"
        return ClarificationAnalysisV1.create(
            original_instruction=text,
            stable_intent=(f"Move {scope}",),
            ambiguity_category=AmbiguityCategory.MULTIPLE_TARGETS,
            ambiguous_span=f"to {entity}",
            context_sources_checked=self._dedupe(context_sources_checked),
            candidates=(
                InterpretationCandidateV1(
                    normalized_instruction=schedule,
                    rationale="the target may identify a project or schedule destination",
                    confidence=0.55,
                ),
                InterpretationCandidateV1(
                    normalized_instruction=ownership,
                    rationale="the target may identify a person or team receiving the work",
                    confidence=0.55,
                ),
            ),
            leading_interpretation=None,
            clarification_required=True,
            question_mode=ClarificationQuestionMode.BOUNDED_CHOICE,
            clarification_question=(
                f"I understand that you want to move {scope}. Should it be moved into the "
                f"{entity} project, or should {entity} take ownership of the work?"
            ),
            continue_unrelated_work=True,
            downstream_execution_blocked=True,
            confidence=ConfidenceAssessment(
                score=0.55,
                rationale="two materially different interpretations remain",
            ),
            blockers=("Target relationship must be clarified before downstream execution",),
        )

    def _missing_owner(
        self,
        text: str,
        match: re.Match[str],
        *,
        context_sources_checked: tuple[str, ...],
    ) -> ClarificationAnalysisV1:
        outcome = self._normalize_space(match.group("outcome"))
        date = match.group("date")
        return ClarificationAnalysisV1.create(
            original_instruction=text,
            stable_intent=(f"Complete {outcome} by {date}",),
            ambiguity_category=AmbiguityCategory.MISSING_OWNER,
            ambiguous_span=None,
            context_sources_checked=self._dedupe(context_sources_checked),
            candidates=(),
            leading_interpretation=None,
            clarification_required=True,
            question_mode=ClarificationQuestionMode.INFORMATION_SEEKING,
            clarification_question=(
                f"I understand that {outcome} should be completed by {date}. Who should own "
                "the work?"
            ),
            continue_unrelated_work=True,
            downstream_execution_blocked=True,
            confidence=ConfidenceAssessment(
                score=0.40,
                rationale="the desired outcome and timing are clear, but ownership is absent",
            ),
            blockers=("Owner required before delegation or provider planning",),
        )

    def _form_date_error(
        self,
        text: str,
        match: re.Match[str],
        *,
        context_sources_checked: tuple[str, ...],
    ) -> ClarificationAnalysisV1:
        leading = text[: match.start()] + f"for {match.group('date')}" + text[match.end() :]
        leading = self._sentence_case(leading)
        return self._single_candidate_typo(
            text=text,
            stable_intent=(self._sentence_case(text[: match.start()].strip()),),
            ambiguous_span="form",
            leading=leading,
            question=f"Did you mean: \u201c{leading}\u201d?",
            context_sources_checked=context_sources_checked,
            rationale="'for' is the coherent relationship word before a day or date",
        )

    def _cite_site_error(
        self,
        text: str,
        *,
        context_sources_checked: tuple[str, ...],
    ) -> ClarificationAnalysisV1:
        leading = _CITE_SITE_RE.sub("site design", text)
        leading = self._sentence_case(leading)
        return self._single_candidate_typo(
            text=text,
            stable_intent=("Review a design",),
            ambiguous_span="cite",
            leading=leading,
            question=(
                "I understand that you want to review the design, and the available context "
                f"points to a website. Did you mean: \u201c{leading}\u201d?"
            ),
            context_sources_checked=context_sources_checked,
            rationale="website context supports the cite-to-site transcription correction",
        )

    def _single_candidate_typo(
        self,
        *,
        text: str,
        stable_intent: tuple[str, ...],
        ambiguous_span: str,
        leading: str,
        question: str,
        context_sources_checked: tuple[str, ...],
        rationale: str,
    ) -> ClarificationAnalysisV1:
        return ClarificationAnalysisV1.create(
            original_instruction=text,
            stable_intent=stable_intent,
            ambiguity_category=AmbiguityCategory.TRANSCRIPTION_ERROR,
            ambiguous_span=ambiguous_span,
            context_sources_checked=self._dedupe(context_sources_checked),
            candidates=(
                InterpretationCandidateV1(
                    normalized_instruction=leading,
                    rationale=rationale,
                    confidence=0.88,
                ),
            ),
            leading_interpretation=leading,
            clarification_required=True,
            question_mode=ClarificationQuestionMode.CONFIRMATORY,
            clarification_question=question,
            continue_unrelated_work=True,
            downstream_execution_blocked=True,
            confidence=ConfidenceAssessment(score=0.88, rationale=rationale),
            blockers=("Clarification required before downstream routing or execution",),
        )

    @staticmethod
    def _normalize_space(value: str) -> str:
        return " ".join(value.strip().split())

    @staticmethod
    def _title_phase(value: str) -> str:
        prefix, number = value.split(maxsplit=1)
        return f"{prefix.capitalize()} {number}"

    @staticmethod
    def _normalize_entity(value: str) -> str:
        clean = value.strip()
        if clean.isalpha() and 2 <= len(clean) <= 5:
            return clean.upper()
        return clean[:1].upper() + clean[1:]

    @staticmethod
    def _sentence_case(value: str) -> str:
        clean = value.strip()
        return clean[:1].upper() + clean[1:] if clean else clean

    @staticmethod
    def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(item.strip() for item in values if item.strip()))

    @staticmethod
    def _website_context(
        *,
        known_entities: tuple[str, ...],
        context_terms: tuple[str, ...],
    ) -> bool:
        terms = {item.casefold() for item in (*known_entities, *context_terms)}
        return bool(terms & {"website", "web site", "site", "web design"})
