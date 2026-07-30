"""Attended inbox clarification timing and exact-once resumption."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from atlas_ros.capabilities.operational_awareness.clarification import (
    ContextAwareClarificationAnalyzer,
)
from atlas_ros.contracts.operational_awareness.clarification import (
    ClarificationAnalysisV1,
    ClarificationBatchDisposition,
    ClarificationBatchItemResultV1,
    ClarificationBatchPlanV1,
    ClarificationContextV1,
    ClarificationReplayDisposition,
    ClarificationResolutionV1,
    ClarificationResumptionReceiptV1,
)


class ClarificationReplayConflict(ValueError):
    """Raised when a resolved analysis is answered again with conflicting meaning."""


@dataclass(frozen=True, slots=True)
class AttendedInboxItem:
    capture_id: str
    correlation_id: str
    instruction: str
    independent: bool = True

    def __post_init__(self) -> None:
        if not all(
            value.strip()
            for value in (self.capture_id, self.correlation_id, self.instruction)
        ):
            raise ValueError("attended inbox items require capture, correlation, and instruction")


@dataclass(frozen=True, slots=True)
class ClarificationResumeResult:
    resolution: ClarificationResolutionV1
    follow_up_analysis: ClarificationAnalysisV1
    receipt: ClarificationResumptionReceiptV1


@dataclass(frozen=True, slots=True)
class AttendedClarificationWorkflow:
    """Plan the next safe interruption without provider access or execution authority."""

    analyzer: ContextAwareClarificationAnalyzer

    def plan_batch(
        self,
        items: tuple[AttendedInboxItem, ...],
        *,
        contexts: Mapping[str, ClarificationContextV1] | None = None,
    ) -> ClarificationBatchPlanV1:
        if not items:
            raise ValueError("clarification batch requires at least one item")
        context_map = contexts or {}
        results: list[ClarificationBatchItemResultV1] = []
        processed: list[str] = []
        eligible: list[str] = []
        paused: list[str] = []
        interruption_capture: str | None = None
        interruption_question: str | None = None
        interruption_position: int | None = None

        for position, item in enumerate(items, start=1):
            if interruption_capture is not None:
                disposition = ClarificationBatchDisposition.ELIGIBLE_AFTER_INTERRUPTION
                results.append(
                    ClarificationBatchItemResultV1(
                        capture_id=item.capture_id,
                        correlation_id=item.correlation_id,
                        position=position,
                        disposition=disposition,
                    )
                )
                if item.independent:
                    eligible.append(item.capture_id)
                continue

            analysis = self.analyzer.analyze(
                item.instruction,
                context=context_map.get(item.capture_id),
            )
            if analysis.clarification_required:
                interruption_capture = item.capture_id
                interruption_question = analysis.clarification_question
                interruption_position = position
                paused.append(item.capture_id)
                results.append(
                    ClarificationBatchItemResultV1(
                        capture_id=item.capture_id,
                        correlation_id=item.correlation_id,
                        position=position,
                        disposition=(
                            ClarificationBatchDisposition.PAUSED_FOR_CLARIFICATION
                        ),
                        analysis_digest=analysis.analysis_digest,
                        clarification_question=analysis.clarification_question,
                    )
                )
                continue

            processed.append(item.capture_id)
            results.append(
                ClarificationBatchItemResultV1(
                    capture_id=item.capture_id,
                    correlation_id=item.correlation_id,
                    position=position,
                    disposition=(
                        ClarificationBatchDisposition.COMPLETED_BEFORE_INTERRUPTION
                    ),
                    analysis_digest=analysis.analysis_digest,
                )
            )

        if interruption_capture is None:
            results = [
                item.model_copy(
                    update={
                        "disposition": ClarificationBatchDisposition.CLEAR_NO_INTERRUPTION
                    }
                )
                for item in results
            ]
            processed = [item.capture_id for item in items]

        return ClarificationBatchPlanV1.create(
            item_results=tuple(results),
            clarification_capture_id=interruption_capture,
            clarification_question=interruption_question,
            interruption_position=interruption_position,
            interrupt_before_next_item=interruption_capture is not None,
            processed_before_interruption=tuple(processed),
            eligible_after_interruption=tuple(eligible),
            paused_capture_ids=tuple(paused),
        )

    def resume(
        self,
        *,
        item: AttendedInboxItem,
        analysis: ClarificationAnalysisV1,
        user_response: str,
        normalized_instruction: str,
        context: ClarificationContextV1 | None = None,
        existing_resolution: ClarificationResolutionV1 | None = None,
        resolved_at: str | None = None,
    ) -> ClarificationResumeResult:
        if item.capture_id.strip() == "" or item.correlation_id.strip() == "":
            raise ValueError("resume requires exact capture and correlation identity")
        if analysis.original_instruction != " ".join(item.instruction.strip().split()):
            raise ValueError("analysis does not bind to the requested inbox item")

        resolution = self.analyzer.resolve(
            analysis,
            capture_id=item.capture_id,
            correlation_id=item.correlation_id,
            user_response=user_response,
            normalized_instruction=normalized_instruction,
            resolved_at=resolved_at,
        )
        replay = ClarificationReplayDisposition.APPLIED
        reclassification_required = True
        if existing_resolution is not None:
            if (
                existing_resolution.capture_id != item.capture_id
                or existing_resolution.correlation_id != item.correlation_id
                or existing_resolution.analysis_digest != analysis.analysis_digest
            ):
                raise ClarificationReplayConflict(
                    "existing resolution belongs to a different clarification identity"
                )
            if (
                existing_resolution.idempotency_identity
                != resolution.idempotency_identity
            ):
                raise ClarificationReplayConflict(
                    "clarification analysis already has a conflicting resolution"
                )
            resolution = existing_resolution
            replay = ClarificationReplayDisposition.DUPLICATE_IGNORED
            reclassification_required = False

        follow_up = self.analyzer.analyze(
            resolution.normalized_instruction,
            context=context,
        )
        receipt = ClarificationResumptionReceiptV1.create(
            capture_id=item.capture_id,
            correlation_id=item.correlation_id,
            analysis_digest=analysis.analysis_digest,
            resolution_digest=resolution.resolution_digest,
            idempotency_identity=resolution.idempotency_identity,
            replay_disposition=replay,
            normalized_instruction=resolution.normalized_instruction,
            follow_up_analysis_digest=follow_up.analysis_digest,
            remaining_clarification_required=follow_up.clarification_required,
            reclassification_required=reclassification_required,
        )
        return ClarificationResumeResult(
            resolution=resolution,
            follow_up_analysis=follow_up,
            receipt=receipt,
        )
