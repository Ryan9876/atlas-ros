"""Provider-free context-aware ambiguity analysis for Atlas ROS v8.1."""
from __future__ import annotations

import re
from dataclasses import dataclass

from atlas_ros.contracts.advisory_v1 import ConfidenceAssessment
from atlas_ros.contracts.operational_awareness.clarification import (
    AmbiguityCategory,
    ClarificationAnalysisV1,
    ClarificationContextV1,
    ClarificationQuestionMode,
    ClarificationResolutionV1,
    InterpretationCandidateV1,
)

_DATE = (
    r"monday|tuesday|wednesday|thursday|friday|saturday|sunday|"
    r"today|tomorrow|next\s+week|next\s+month|\d{4}-\d{2}-\d{2}"
)
_CONNECTOR_RE = re.compile(
    r"^(?P<verb>build|create|prepare|develop|implement)\s+"
    r"(?P<scope>phase\s+\d+)\s+(?P<link>[a-z]+)\s+"
    r"(?P<entity>[a-z][a-z0-9_-]*)[.!?]?$",
    re.IGNORECASE,
)
_PHASE_TARGET_RE = re.compile(
    r"^(?P<verb>build|create|develop|implement)\s+"
    r"(?P<scope>phase\s+\d+)\s+(?P<link>of|for)\s+"
    r"(?P<entity>[a-z][a-z0-9_-]*)[.!?]?$",
    re.IGNORECASE,
)
_MISSING_ENTITY_RE = re.compile(
    r"^(?P<verb>build|create|develop|implement)\s+"
    r"(?P<scope>phase\s+\d+)\s+(?:of|for|to)\s*[.!?]?$",
    re.IGNORECASE,
)
_FORM_DATE_RE = re.compile(rf"\bform\s+(?P<date>{_DATE})\b", re.IGNORECASE)
_MOVE_PHASE_RE = re.compile(
    r"^move\s+(?P<scope>phase\s+\d+)\s+to\s+(?P<entity>[a-z][a-z0-9_-]*)[.!?]?$",
    re.IGNORECASE,
)
_MISSING_OWNER_RE = re.compile(
    rf"^have\s+(?P<outcome>.+?)\s+completed\s+by\s+(?P<date>{_DATE})[.!?]?$",
    re.IGNORECASE,
)
_CONFLICTING_DATES_RE = re.compile(
    rf"\b(?:by|due)\s+(?P<first>{_DATE})\b.+\b(?:by|due)\s+(?P<second>{_DATE})\b",
    re.IGNORECASE,
)
_PRIORITY_RE = re.compile(
    r"\b(?P<priority>p[0-4]|critical|high|medium|normal|low)\s*(?:priority)?\b",
    re.IGNORECASE,
)
_PRONOUN_TARGET_RE = re.compile(
    r"^(?P<verb>review|update|move|prepare|complete|delete|archive)\s+"
    r"(?P<pronoun>it|this|that|them|those)[.!?]?$",
    re.IGNORECASE,
)
_TENTATIVE_DELEGATION_RE = re.compile(
    r"^(?P<person>[A-Z][A-Za-z'’-]*(?:\s+[A-Z][A-Za-z'’-]*){0,3})\s+"
    r"(?P<modal>can|could|might|may|should)\s+"
    r"(?P<verb>handle|own|complete|deliver|manage)\s+(?P<outcome>.+?)[.!?]?$"
)
_EXPLICIT_DELEGATION_RE = re.compile(
    rf"^(?:assign|delegate)\s+(?P<outcome>.+?)\s+to\s+"
    rf"(?P<person>[A-Z][A-Za-z'’-]*(?:\s+[A-Z][A-Za-z'’-]*){{0,3}})"
    rf"(?:\s+by\s+(?P<date>{_DATE}))?[.!?]?$",
    re.IGNORECASE,
)
_PERSON_HANDLES_RE = re.compile(
    rf"^(?P<person>[A-Z][A-Za-z'’-]*(?:\s+[A-Z][A-Za-z'’-]*){{0,3}})\s+"
    rf"(?:will|is\s+handling|owns|is\s+responsible\s+for)\s+"
    rf"(?P<outcome>.+?)(?:\s+by\s+(?P<date>{_DATE}))?[.!?]?$"
)
_OWNER_WITHOUT_OUTCOME_RE = re.compile(
    r"^(?P<person>[A-Z][A-Za-z'’-]*(?:\s+[A-Z][A-Za-z'’-]*){0,3})\s+"
    r"(?:owns|is\s+responsible\s+for|will\s+handle|is\s+handling)\s+"
    r"(?:this|it)?[.!?]?$"
)
_MISSING_TARGET_RE = re.compile(
    r"^(?P<verb>review|update|move|prepare|build|create|implement|complete)\s*[.!?]?$",
    re.IGNORECASE,
)
_PROPER_NOUN_RE = re.compile(
    r"^(?P<verb>review|prepare|update|assess)\s+(?:the\s+)?"
    r"(?P<entity>[A-Z][A-Za-z0-9_-]*)\s+(?P<object>.+?)[.!?]?$"
)
_CITE_SITE_RE = re.compile(r"\bcite\s+design\b", re.IGNORECASE)
_STATUS_NOTE_RE = re.compile(
    r"^(?P<subject>.+?)\s+(?P<status>is\s+delayed|was\s+delayed|"
    r"is\s+blocked|was\s+blocked|failed|completed|is\s+complete)[.!?]?$",
    re.IGNORECASE,
)
_CLEAR_TASK_RE = re.compile(
    r"^add\s+[“\"]?(?P<title>.+?)[”\"]?\s+to\s+my\s+"
    r"(?P<destination>work|personal)\s+tasks[.!?]?$",
    re.IGNORECASE,
)
_COMPLETION_MARKER_RE = re.compile(
    r"(?i)\b(?:done\s+when|completion\s+criteria|complete\s+when|finished\s+when)\b"
)


@dataclass(frozen=True, slots=True)
class ContextAwareClarificationAnalyzer:
    """Rank narrow interpretations without authorizing routing or execution."""

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
        bounded = context or ClarificationContextV1(
            source_refs=self._dedupe(context_sources_checked),
            known_entities=self._dedupe(known_entities),
            context_terms=self._dedupe(context_terms),
            candidate_targets=self._dedupe(candidate_targets),
        )

        connector = _CONNECTOR_RE.fullmatch(text)
        if connector is not None and connector.group("link").casefold() == "or":
            return self._connector_error(text, connector, bounded)

        missing_entity = _MISSING_ENTITY_RE.fullmatch(text)
        if missing_entity is not None:
            return self._missing_entity(text, missing_entity, bounded)

        phase_target = _PHASE_TARGET_RE.fullmatch(text)
        if phase_target is not None:
            return self._action_versus_project(text, phase_target, bounded)

        move_phase = _MOVE_PHASE_RE.fullmatch(text)
        if move_phase is not None:
            return self._move_phase_ambiguity(text, move_phase, bounded)

        date_conflict = _CONFLICTING_DATES_RE.search(text)
        if date_conflict is not None:
            first = self._normalize_space(date_conflict.group("first"))
            second = self._normalize_space(date_conflict.group("second"))
            if first.casefold() != second.casefold():
                return self._conflicting_dates(text, first, second, bounded)

        priorities = tuple(
            dict.fromkeys(
                match.group("priority").casefold()
                for match in _PRIORITY_RE.finditer(text)
            )
        )
        if len(priorities) > 1:
            return self._conflicting_priorities(text, priorities, bounded)

        pronoun = _PRONOUN_TARGET_RE.fullmatch(text)
        if pronoun is not None:
            return self._pronoun_target(text, pronoun, bounded)

        missing_owner = _MISSING_OWNER_RE.fullmatch(text)
        if missing_owner is not None:
            return self._missing_owner(text, missing_owner, bounded)

        tentative = _TENTATIVE_DELEGATION_RE.fullmatch(text)
        if tentative is not None:
            return self._ambiguous_delegation(text, tentative, bounded)

        owner_without_outcome = _OWNER_WITHOUT_OUTCOME_RE.fullmatch(text)
        if owner_without_outcome is not None:
            return self._missing_outcome(text, owner_without_outcome, bounded)

        explicit_delegation = _EXPLICIT_DELEGATION_RE.fullmatch(text)
        if explicit_delegation is not None and not _COMPLETION_MARKER_RE.search(text):
            return self._missing_completion_criteria(text, explicit_delegation, bounded)

        person_handles = _PERSON_HANDLES_RE.fullmatch(text)
        if person_handles is not None and not _COMPLETION_MARKER_RE.search(text):
            return self._missing_completion_criteria(text, person_handles, bounded)

        missing_target = _MISSING_TARGET_RE.fullmatch(text)
        if missing_target is not None:
            return self._missing_target(text, missing_target, bounded)

        form_date = _FORM_DATE_RE.search(text)
        if form_date is not None:
            return self._form_date_error(text, form_date, bounded)

        if _CITE_SITE_RE.search(text) and self._website_context(bounded):
            return self._cite_site_error(text, bounded)

        clear_task = _CLEAR_TASK_RE.fullmatch(text)
        if clear_task is not None:
            return self._clear(
                text,
                stable_intent=(
                    f"Add {self._strip_quotes(clear_task.group('title'))} "
                    f"to {clear_task.group('destination').capitalize()} tasks",
                ),
                bounded=bounded,
                evidence=("destination and task ownership are explicit",),
            )

        proper_noun = _PROPER_NOUN_RE.fullmatch(text)
        if proper_noun is not None:
            entity = self._normalize_entity(proper_noun.group("entity"))
            return self._clear(
                text,
                stable_intent=(self._sentence_case(text.rstrip(".!?")),),
                bounded=bounded,
                category=AmbiguityCategory.POSSIBLE_PROPER_NOUN,
                preserved_entities=(entity,),
                evidence=(
                    f"{entity} occupies a grammatically plausible entity position",
                    "absence from authoritative context would not prove a typo",
                ),
                score=0.90,
            )

        status_note = _STATUS_NOTE_RE.fullmatch(text)
        if status_note is not None:
            return self._request_versus_note(text, status_note, bounded)

        return self._clear(
            text,
            stable_intent=(self._sentence_case(text.rstrip(".!?")),),
            bounded=bounded,
            evidence=("no material ambiguity rule was triggered",),
        )

    def resolve(
        self,
        analysis: ClarificationAnalysisV1,
        *,
        capture_id: str,
        correlation_id: str,
        user_response: str,
        normalized_instruction: str,
        resolved_at: str | None = None,
    ) -> ClarificationResolutionV1:
        if not analysis.clarification_required or not analysis.clarification_question:
            raise ValueError("only clarification-required analyses can be resolved")
        response = self._normalize_space(user_response)
        normalized = self._normalize_space(normalized_instruction)
        if not response or not normalized:
            raise ValueError(
                "clarification resolution requires an answer and normalized instruction"
            )
        return ClarificationResolutionV1.create(
            capture_id=capture_id,
            correlation_id=correlation_id,
            analysis_digest=analysis.analysis_digest,
            original_instruction=analysis.original_instruction,
            clarification_question=analysis.clarification_question,
            user_response=response,
            normalized_instruction=normalized,
            ambiguity_category=analysis.ambiguity_category,
            resolved_at=resolved_at,
        )

    def _connector_error(
        self,
        text: str,
        match: re.Match[str],
        bounded: ClarificationContextV1,
    ) -> ClarificationAnalysisV1:
        verb = match.group("verb").capitalize()
        scope = self._title_phase(match.group("scope"))
        entity = self._normalize_entity(match.group("entity"))
        leading = f"{verb} {scope} of {entity}"
        alternative = f"{verb} {scope} for {entity}"
        return self._question(
            text=text,
            stable_intent=(f"{verb} {scope}",),
            category=AmbiguityCategory.CONNECTOR_ERROR,
            ambiguous_span=match.group("link"),
            preserved_entities=(entity,),
            bounded=bounded,
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
            leading=leading,
            mode=ClarificationQuestionMode.CONFIRMATORY,
            question=(
                f"I understand that you want to {verb.casefold()} {scope}, and {entity} may be "
                f"the application name. Did you mean: “{leading}”?"
            ),
            question_basis=(
                f"'{match.group('link')}' is structurally inconsistent while {entity} is "
                "plausible as a target entity"
            ),
            evidence=(
                "function-word substitution preserves the possible entity",
                "of is the strongest grammatical relationship for a phased milestone",
            ),
            score=0.90,
            rationale=(
                "one connector substitution produces a coherent phased-build instruction "
                "without changing the possible entity"
            ),
            blocker="Clarification required before downstream routing or execution",
        )

    def _missing_entity(
        self,
        text: str,
        match: re.Match[str],
        bounded: ClarificationContextV1,
    ) -> ClarificationAnalysisV1:
        verb = match.group("verb").capitalize()
        scope = self._title_phase(match.group("scope"))
        return self._question(
            text=text,
            stable_intent=(f"{verb} {scope}",),
            category=AmbiguityCategory.MISSING_ENTITY,
            ambiguous_span=None,
            bounded=bounded,
            candidates=(),
            leading=None,
            mode=ClarificationQuestionMode.INFORMATION_SEEKING,
            question=(
                f"I understand that you want to {verb.casefold()} {scope}. "
                "Which application or project is Phase 1 for?"
            ),
            question_basis="the target entity is absent",
            evidence=("action and phased milestone are clear",),
            score=0.35,
            rationale="the action and phase are known, but the target entity is missing",
            blocker="Target entity required before classification",
        )

    def _action_versus_project(
        self,
        text: str,
        match: re.Match[str],
        bounded: ClarificationContextV1,
    ) -> ClarificationAnalysisV1:
        verb = match.group("verb").capitalize()
        scope = self._title_phase(match.group("scope"))
        entity = self._normalize_entity(match.group("entity"))
        normalized = f"{verb} {scope} {match.group('link').casefold()} {entity}"
        return self._question(
            text=text,
            stable_intent=(normalized,),
            category=AmbiguityCategory.ACTION_VERSUS_PROJECT,
            ambiguous_span=f"{verb} {scope}",
            preserved_entities=(entity,),
            bounded=bounded,
            candidates=(),
            leading=None,
            mode=ClarificationQuestionMode.INFORMATION_SEEKING,
            question=(
                f"I understand that {scope} belongs to {entity}. "
                f"What outcome should mark {scope} complete?"
            ),
            question_basis=(
                "building a phase normally contains multiple actions, so a completion outcome "
                "is required before creating a project or next action"
            ),
            evidence=(
                f"{entity} is preserved as the target entity",
                "the phrase describes a multi-step phase rather than one physical action",
            ),
            score=0.45,
            rationale="target and phase are clear, but the Phase 1 completion boundary is absent",
            blocker="Phase outcome required before Action versus Project routing",
        )

    def _move_phase_ambiguity(
        self,
        text: str,
        match: re.Match[str],
        bounded: ClarificationContextV1,
    ) -> ClarificationAnalysisV1:
        scope = self._title_phase(match.group("scope"))
        entity = self._normalize_entity(match.group("entity"))
        schedule = f"Move the {scope} schedule to the {entity} project"
        ownership = f"Transfer {scope} work or ownership to {entity}"
        return self._question(
            text=text,
            stable_intent=(f"Move {scope}",),
            category=AmbiguityCategory.MULTIPLE_TARGETS,
            ambiguous_span=f"to {entity}",
            preserved_entities=(entity,),
            bounded=bounded,
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
            leading=None,
            mode=ClarificationQuestionMode.BOUNDED_CHOICE,
            question=(
                f"I understand that you want to move {scope}. Should it be moved into the "
                f"{entity} project, or should {entity} take ownership of the work?"
            ),
            question_basis="'to Orion' can identify either a destination or a new owner",
            evidence=("two interpretations would create different records and ownership",),
            score=0.55,
            rationale="two materially different target relationships remain",
            blocker="Target relationship must be clarified before downstream execution",
        )

    def _conflicting_dates(
        self,
        text: str,
        first: str,
        second: str,
        bounded: ClarificationContextV1,
    ) -> ClarificationAnalysisV1:
        return self._question(
            text=text,
            stable_intent=(self._without_date_phrases(text),),
            category=AmbiguityCategory.CONFLICTING_DATES,
            ambiguous_span=f"{first} / {second}",
            bounded=bounded,
            candidates=(),
            leading=None,
            mode=ClarificationQuestionMode.BOUNDED_CHOICE,
            question=(
                f"I understand the requested work, but I found two dates: {first} and {second}. "
                "Which date should control completion?"
            ),
            question_basis="two different completion dates are present",
            evidence=(f"date evidence: {first}", f"date evidence: {second}"),
            score=0.30,
            rationale="different dates would change sequencing and commitments",
            blocker="Controlling date must be clarified",
        )

    def _conflicting_priorities(
        self,
        text: str,
        priorities: tuple[str, ...],
        bounded: ClarificationContextV1,
    ) -> ClarificationAnalysisV1:
        display = tuple(item.upper() if item.startswith("p") else item for item in priorities)
        return self._question(
            text=text,
            stable_intent=(self._without_priority_words(text),),
            category=AmbiguityCategory.CONFLICTING_PRIORITIES,
            ambiguous_span=" / ".join(display),
            bounded=bounded,
            candidates=(),
            leading=None,
            mode=ClarificationQuestionMode.BOUNDED_CHOICE,
            question=(
                f"I understand the requested work, but both {display[0]} and {display[1]} "
                "are specified. Which priority should apply?"
            ),
            question_basis="two different priorities are present",
            evidence=tuple(f"priority evidence: {item}" for item in display),
            score=0.30,
            rationale="different priorities would change execution ordering",
            blocker="Controlling priority must be clarified",
        )

    def _pronoun_target(
        self,
        text: str,
        match: re.Match[str],
        bounded: ClarificationContextV1,
    ) -> ClarificationAnalysisV1:
        verb = match.group("verb").capitalize()
        targets = bounded.candidate_targets
        if len(targets) == 1:
            target = targets[0]
            normalized = f"{verb} {target}"
            return self._clear(
                text,
                stable_intent=(normalized,),
                bounded=bounded,
                evidence=(f"pronoun uniquely resolves to authoritative target {target}",),
                score=0.90,
            )
        alternatives = tuple(
            InterpretationCandidateV1(
                normalized_instruction=f"{verb} {target}",
                rationale="authoritative context contains this possible pronoun target",
                confidence=0.55,
            )
            for target in targets[:2]
        )
        return self._question(
            text=text,
            stable_intent=(verb,),
            category=AmbiguityCategory.AMBIGUOUS_PRONOUN,
            ambiguous_span=match.group("pronoun"),
            bounded=bounded,
            candidates=alternatives,
            leading=None,
            mode=(
                ClarificationQuestionMode.BOUNDED_CHOICE
                if len(alternatives) == 2
                else ClarificationQuestionMode.INFORMATION_SEEKING
            ),
            question=(
                f"I understand that you want to {verb.casefold()} something. "
                + (
                    f"Did you mean {targets[0]}, or {targets[1]}?"
                    if len(alternatives) == 2
                    else "Which item should I use?"
                )
            ),
            question_basis="the pronoun does not resolve to one authoritative target",
            evidence=tuple(f"possible target: {target}" for target in targets[:2]),
            score=0.35,
            rationale="the requested action is clear, but its target is not unique",
            blocker="Unique target required before routing",
        )

    def _missing_owner(
        self,
        text: str,
        match: re.Match[str],
        bounded: ClarificationContextV1,
    ) -> ClarificationAnalysisV1:
        outcome = self._normalize_space(match.group("outcome"))
        date = self._normalize_space(match.group("date"))
        return self._question(
            text=text,
            stable_intent=(f"Complete {outcome} by {date}",),
            category=AmbiguityCategory.MISSING_OWNER,
            ambiguous_span=None,
            bounded=bounded,
            candidates=(),
            leading=None,
            mode=ClarificationQuestionMode.INFORMATION_SEEKING,
            question=(
                f"I understand that {outcome} should be completed by {date}. "
                "Who should own the work?"
            ),
            question_basis="the desired outcome and date are explicit, but ownership is absent",
            evidence=(f"outcome: {outcome}", f"date: {date}"),
            score=0.40,
            rationale="the desired outcome and timing are clear, but ownership is absent",
            blocker="Owner required before delegation or provider planning",
        )

    def _ambiguous_delegation(
        self,
        text: str,
        match: re.Match[str],
        bounded: ClarificationContextV1,
    ) -> ClarificationAnalysisV1:
        person = self._normalize_person(match.group("person"))
        outcome = self._normalize_space(match.group("outcome"))
        assign = f"Assign {outcome} to {person}"
        suggestion = f"Record {person} as a possible owner for {outcome}"
        return self._question(
            text=text,
            stable_intent=(outcome,),
            category=AmbiguityCategory.AMBIGUOUS_DELEGATION,
            ambiguous_span=f"{person} {match.group('modal')}",
            preserved_entities=(person,),
            bounded=bounded,
            candidates=(
                InterpretationCandidateV1(
                    normalized_instruction=assign,
                    rationale="the statement may be intended as an assignment",
                    confidence=0.50,
                ),
                InterpretationCandidateV1(
                    normalized_instruction=suggestion,
                    rationale="the modal may only describe capability or a suggestion",
                    confidence=0.50,
                ),
            ),
            leading=None,
            mode=ClarificationQuestionMode.BOUNDED_CHOICE,
            question=(
                f"I understand that {person} may handle {outcome}. "
                f"Are you assigning the work to {person}, or only suggesting {person} as an option?"
            ),
            question_basis=(
                "a person-name mention plus tentative modal does not establish delegation"
            ),
            evidence=(f"tentative ownership language: {match.group('modal')}",),
            score=0.35,
            rationale="ownership intent is materially ambiguous",
            blocker="Explicit delegation intent required before ownership changes",
        )

    def _missing_outcome(
        self,
        text: str,
        match: re.Match[str],
        bounded: ClarificationContextV1,
    ) -> ClarificationAnalysisV1:
        person = self._normalize_person(match.group("person"))
        return self._question(
            text=text,
            stable_intent=(f"{person} owns work",),
            category=AmbiguityCategory.MISSING_OUTCOME,
            ambiguous_span=None,
            preserved_entities=(person,),
            bounded=bounded,
            candidates=(),
            leading=None,
            mode=ClarificationQuestionMode.INFORMATION_SEEKING,
            question=(
                f"I understand that {person} is intended to own work. "
                "What specific outcome should they deliver?"
            ),
            question_basis="ownership is stated without an expected outcome",
            evidence=(f"possible owner: {person}",),
            score=0.30,
            rationale="owner is present, but expected outcome is missing",
            blocker="Expected outcome required before delegation",
        )

    def _missing_completion_criteria(
        self,
        text: str,
        match: re.Match[str],
        bounded: ClarificationContextV1,
    ) -> ClarificationAnalysisV1:
        person = self._normalize_person(match.group("person"))
        outcome = self._normalize_space(match.group("outcome"))
        date = match.groupdict().get("date")
        stable = f"{person} owns {outcome}"
        if date:
            stable += f" by {self._normalize_space(date)}"
        return self._question(
            text=text,
            stable_intent=(stable,),
            category=AmbiguityCategory.MISSING_COMPLETION_CRITERIA,
            ambiguous_span=None,
            preserved_entities=(person,),
            bounded=bounded,
            candidates=(),
            leading=None,
            mode=ClarificationQuestionMode.INFORMATION_SEEKING,
            question=(
                f"I understand that {person} should deliver {outcome}. "
                "What result will confirm the work is complete?"
            ),
            question_basis="qualified delegation requires explicit completion criteria",
            evidence=(f"owner: {person}", f"outcome: {outcome}"),
            score=0.45,
            rationale="ownership and outcome are clear, but completion evidence is missing",
            blocker="Completion criteria required before delegation planning",
        )

    def _missing_target(
        self,
        text: str,
        match: re.Match[str],
        bounded: ClarificationContextV1,
    ) -> ClarificationAnalysisV1:
        verb = match.group("verb").capitalize()
        return self._question(
            text=text,
            stable_intent=(verb,),
            category=AmbiguityCategory.MISSING_TARGET,
            ambiguous_span=None,
            bounded=bounded,
            candidates=(),
            leading=None,
            mode=ClarificationQuestionMode.INFORMATION_SEEKING,
            question=(
                f"I understand that you want to {verb.casefold()} something. "
                "Which item should I use?"
            ),
            question_basis="the action is explicit, but its target is absent",
            evidence=(f"action: {verb}",),
            score=0.25,
            rationale="the action is known, but the object is missing",
            blocker="Target required before classification",
        )

    def _form_date_error(
        self,
        text: str,
        match: re.Match[str],
        bounded: ClarificationContextV1,
    ) -> ClarificationAnalysisV1:
        leading = text[: match.start()] + f"for {match.group('date')}" + text[match.end() :]
        leading = self._sentence_case(leading.rstrip(".!?"))
        return self._single_candidate_typo(
            text=text,
            stable_intent=(self._sentence_case(text[: match.start()].strip()),),
            ambiguous_span="form",
            leading=leading,
            question=(
                f"I understand that you want to prepare the review for the named target. "
                f"Did you mean: “{leading}”?"
            ),
            bounded=bounded,
            rationale="'for' is the coherent relationship word before a day or date",
        )

    def _cite_site_error(
        self,
        text: str,
        bounded: ClarificationContextV1,
    ) -> ClarificationAnalysisV1:
        leading = _CITE_SITE_RE.sub("site design", text)
        leading = self._sentence_case(leading.rstrip(".!?"))
        return self._single_candidate_typo(
            text=text,
            stable_intent=("Review a design",),
            ambiguous_span="cite",
            leading=leading,
            question=(
                "I understand that you want to review the design, and the available context "
                f"points to a website. Did you mean: “{leading}”?"
            ),
            bounded=bounded,
            rationale="website context supports the cite-to-site transcription correction",
        )

    def _request_versus_note(
        self,
        text: str,
        match: re.Match[str],
        bounded: ClarificationContextV1,
    ) -> ClarificationAnalysisV1:
        subject = self._normalize_space(match.group("subject"))
        status = self._normalize_space(match.group("status"))
        informational = f"Record that {subject} {status}"
        action = f"Create a follow-up action for {subject} because it {status}"
        return self._question(
            text=text,
            stable_intent=(f"{subject} {status}",),
            category=AmbiguityCategory.REQUEST_VERSUS_NOTE,
            ambiguous_span=None,
            bounded=bounded,
            candidates=(
                InterpretationCandidateV1(
                    normalized_instruction=informational,
                    rationale="the statement may be an informational status update",
                    confidence=0.50,
                ),
                InterpretationCandidateV1(
                    normalized_instruction=action,
                    rationale="the statement may imply that follow-up work is requested",
                    confidence=0.50,
                ),
            ),
            leading=None,
            mode=ClarificationQuestionMode.BOUNDED_CHOICE,
            question=(
                f"I understand that {subject} {status}. "
                "Should I record this as an informational update, or create a follow-up action?"
            ),
            question_basis=(
                "the statement contains status evidence but no explicit requested action"
            ),
            evidence=("status is clear", "request type is not explicit"),
            score=0.40,
            rationale="informational and actionable interpretations would route differently",
            blocker="Request type must be clarified before record routing",
        )

    def _single_candidate_typo(
        self,
        *,
        text: str,
        stable_intent: tuple[str, ...],
        ambiguous_span: str,
        leading: str,
        question: str,
        bounded: ClarificationContextV1,
        rationale: str,
    ) -> ClarificationAnalysisV1:
        return self._question(
            text=text,
            stable_intent=stable_intent,
            category=AmbiguityCategory.TRANSCRIPTION_ERROR,
            ambiguous_span=ambiguous_span,
            bounded=bounded,
            candidates=(
                InterpretationCandidateV1(
                    normalized_instruction=leading,
                    rationale=rationale,
                    confidence=0.88,
                ),
            ),
            leading=leading,
            mode=ClarificationQuestionMode.CONFIRMATORY,
            question=question,
            question_basis=rationale,
            evidence=("one local transcription correction preserves the remaining instruction",),
            score=0.88,
            rationale=rationale,
            blocker="Clarification required before downstream routing or execution",
        )

    def _question(
        self,
        *,
        text: str,
        stable_intent: tuple[str, ...],
        category: AmbiguityCategory,
        ambiguous_span: str | None,
        bounded: ClarificationContextV1,
        candidates: tuple[InterpretationCandidateV1, ...],
        leading: str | None,
        mode: ClarificationQuestionMode,
        question: str,
        question_basis: str,
        evidence: tuple[str, ...],
        score: float,
        rationale: str,
        blocker: str,
        preserved_entities: tuple[str, ...] = (),
    ) -> ClarificationAnalysisV1:
        return ClarificationAnalysisV1.create(
            original_instruction=text,
            stable_intent=stable_intent,
            ambiguity_category=category,
            ambiguous_span=ambiguous_span,
            preserved_entities=self._dedupe(preserved_entities),
            context_sources_checked=self._dedupe(bounded.source_refs),
            authoritative_context_digest=bounded.authoritative_snapshot_digest,
            evidence=self._dedupe(evidence),
            candidates=candidates,
            leading_interpretation=leading,
            clarification_required=True,
            question_mode=mode,
            clarification_question=question,
            question_basis=question_basis,
            continue_unrelated_work=True,
            downstream_execution_blocked=True,
            confidence=ConfidenceAssessment(score=score, rationale=rationale),
            blockers=(blocker,),
        )

    def _clear(
        self,
        text: str,
        *,
        stable_intent: tuple[str, ...],
        bounded: ClarificationContextV1,
        category: AmbiguityCategory = AmbiguityCategory.NONE,
        preserved_entities: tuple[str, ...] = (),
        evidence: tuple[str, ...] = (),
        score: float = 0.95,
    ) -> ClarificationAnalysisV1:
        return ClarificationAnalysisV1.create(
            original_instruction=text,
            stable_intent=stable_intent,
            ambiguity_category=category,
            ambiguous_span=None,
            preserved_entities=self._dedupe(preserved_entities),
            context_sources_checked=self._dedupe(bounded.source_refs),
            authoritative_context_digest=bounded.authoritative_snapshot_digest,
            evidence=self._dedupe(evidence),
            candidates=(),
            leading_interpretation=None,
            clarification_required=False,
            question_mode=None,
            clarification_question=None,
            question_basis=None,
            continue_unrelated_work=True,
            downstream_execution_blocked=False,
            confidence=ConfidenceAssessment(
                score=score,
                rationale=(
                    "no material ambiguity requires user interruption"
                    if category == AmbiguityCategory.NONE
                    else "the possible proper noun is preserved without treating it as a typo"
                ),
            ),
            blockers=(),
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
    def _normalize_person(value: str) -> str:
        return " ".join(part[:1].upper() + part[1:] for part in value.strip().split())

    @staticmethod
    def _sentence_case(value: str) -> str:
        clean = value.strip()
        return clean[:1].upper() + clean[1:] if clean else clean

    @staticmethod
    def _dedupe(values: tuple[str, ...]) -> tuple[str, ...]:
        return tuple(dict.fromkeys(item.strip() for item in values if item.strip()))

    @staticmethod
    def _strip_quotes(value: str) -> str:
        return value.strip().strip("“”\"'")

    @staticmethod
    def _website_context(bounded: ClarificationContextV1) -> bool:
        terms = {
            item.casefold()
            for item in (*bounded.known_entities, *bounded.context_terms)
        }
        return bool(terms & {"website", "web site", "site", "web design"})

    @staticmethod
    def _without_date_phrases(text: str) -> str:
        scrubbed = re.sub(rf"\b(?:by|due)\s+(?:{_DATE})\b", "", text, flags=re.IGNORECASE)
        return " ".join(scrubbed.strip(" .;,").split())

    @staticmethod
    def _without_priority_words(text: str) -> str:
        scrubbed = _PRIORITY_RE.sub("", text)
        return " ".join(scrubbed.strip(" .;,").split())
