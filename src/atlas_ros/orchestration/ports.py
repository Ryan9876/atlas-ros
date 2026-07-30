from __future__ import annotations

from typing import Any, Protocol

from atlas_ros.contracts import (
    ErrorClassification,
    ProviderName,
    ProviderOperation,
    ProviderOperationResult,
)


class ProviderExecutionError(RuntimeError):
    """Content-safe provider failure with governed retry metadata."""

    def __init__(
        self,
        classification: ErrorClassification,
        message: str,
        *,
        uncertain_apply: bool = False,
        retry_after_seconds: float | None = None,
    ) -> None:
        super().__init__(message[:1_000])
        self.classification = classification
        self.uncertain_apply = uncertain_apply
        self.retry_after_seconds = (
            retry_after_seconds
            if classification.retryable
            and retry_after_seconds is not None
            and retry_after_seconds >= 0
            else None
        )


class ExecutionProviderPort(Protocol):
    provider_name: ProviderName

    def execute_operation(
        self,
        operation: ProviderOperation,
        context: dict[str, Any],
        *,
        attempt: int,
        simulation: bool = False,
    ) -> ProviderOperationResult: ...

    def readback_before_retry(
        self,
        operation: ProviderOperation,
        context: dict[str, Any],
    ) -> ProviderOperationResult | None: ...

    def compensate_operation(
        self,
        operation: ProviderOperation,
        context: dict[str, Any],
        *,
        attempt: int,
    ) -> ProviderOperationResult: ...


class LegacyTodoistExecutionPort(Protocol):
    def resolve_target(self, project: str, section: str, labels: tuple[str, ...]) -> Any: ...

    def upsert_parent(self, **kwargs: Any) -> Any: ...

    def children_by_content(self, parent_id: str) -> dict[str, Any]: ...

    def upsert_child(self, **kwargs: Any) -> Any: ...

    def verify_tree(self, parent_id: str, expected_titles: list[str]) -> None: ...

    def move_group(self, task_id: str, target_section_id: str) -> None: ...
