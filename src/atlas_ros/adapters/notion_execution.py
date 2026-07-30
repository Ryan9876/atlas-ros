from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from atlas_ros.adapters.errors import AdapterError
from atlas_ros.adapters.notion import NotionAdapter, NotionPage
from atlas_ros.contracts import (
    ErrorClassification,
    ProviderName,
    ProviderOperation,
    ProviderOperationResult,
    ProviderOperationType,
)
from atlas_ros.orchestration.ports import ProviderExecutionError


@dataclass(frozen=True)
class NotionMappingContract:
    data_source_id: str
    identity_property: str
    required_properties: tuple[str, ...]
    writable_properties: frozenset[str]

    def validate(self, schema: dict[str, Any]) -> None:
        properties = schema.get("properties", schema)
        if not isinstance(properties, dict):
            raise ProviderExecutionError(
                ErrorClassification.SCHEMA_MISMATCH,
                "Notion data-source schema is malformed",
            )
        missing = set(self.required_properties) - set(properties)
        if missing:
            raise ProviderExecutionError(
                ErrorClassification.SCHEMA_MISMATCH,
                f"Notion schema is missing required properties: {sorted(missing)}",
            )


class NotionExecutionAdapterV2:
    """Provider-specific Notion record operations with caller-owned mapping policy."""

    provider_name = ProviderName.NOTION

    def __init__(self, provider: NotionAdapter, mapping: NotionMappingContract) -> None:
        self._provider = provider
        self._mapping = mapping

    def _validate_schema(self) -> None:
        try:
            self._mapping.validate(self._provider.fetch_data_source(self._mapping.data_source_id))
        except KeyError as exc:
            raise ProviderExecutionError(
                ErrorClassification.SCHEMA_MISMATCH,
                "Notion data source is unavailable",
            ) from exc

    def _properties(self, operation: ProviderOperation) -> dict[str, Any]:
        raw = operation.payload.get("properties", {})
        if not isinstance(raw, dict):
            raise ProviderExecutionError(
                ErrorClassification.VALIDATION_FAILURE,
                "Notion properties must be an object",
            )
        unknown = set(raw) - self._mapping.writable_properties
        if unknown:
            raise ProviderExecutionError(
                ErrorClassification.VALIDATION_FAILURE,
                f"Notion operation contains unmapped properties: {sorted(unknown)}",
            )
        return dict(raw)

    @staticmethod
    def _verify(page: NotionPage, properties: dict[str, Any]) -> None:
        if any(page.properties.get(key) != value for key, value in properties.items()):
            raise ProviderExecutionError(
                ErrorClassification.READBACK_MISMATCH,
                "Notion readback did not match requested properties",
            )

    def _find(self, identity: Any) -> NotionPage | None:
        pages = self._provider.query_pages(
            self._mapping.data_source_id,
            {
                "filter": {
                    "property": self._mapping.identity_property,
                    "rich_text": {"equals": identity},
                }
            },
        )
        if len(pages) > 1:
            raise ProviderExecutionError(
                ErrorClassification.SCHEMA_MISMATCH,
                "Notion authoritative identity is not unique",
            )
        return pages[0] if pages else None

    def execute_operation(
        self,
        operation: ProviderOperation,
        context: dict[str, Any],
        *,
        attempt: int,
        simulation: bool = False,
    ) -> ProviderOperationResult:
        if operation.provider != self.provider_name:
            raise ProviderExecutionError(
                ErrorClassification.VALIDATION_FAILURE,
                "Notion adapter received an operation for another provider",
            )
        self._validate_schema()
        if simulation:
            return ProviderOperationResult(
                operation_id=operation.operation_id,
                provider=self.provider_name,
                operation_type=operation.operation_type,
                attempt=attempt,
                readback_verified=False,
                evidence={"simulation": "true"},
            )
        try:
            identity = operation.payload.get("identity")
            if operation.operation_type == ProviderOperationType.FIND_RECORD:
                page = self._find(identity)
                if page is not None:
                    context["notion_page"] = page
                return ProviderOperationResult(
                    operation_id=operation.operation_id,
                    provider=self.provider_name,
                    operation_type=operation.operation_type,
                    attempt=attempt,
                    readback_verified=True,
                    provider_object_references=(page.id,) if page else (),
                )
            if operation.operation_type in {
                ProviderOperationType.UPSERT_RECORD,
                ProviderOperationType.WRITE_LINK,
            }:
                properties = self._properties(operation)
                existing = context.get("notion_page") or self._find(identity)
                page = (
                    self._provider.update_page(existing.id, properties)
                    if isinstance(existing, NotionPage)
                    else self._provider.create_page(self._mapping.data_source_id, properties)
                )
                readback = self._provider.get_page(page.id)
                self._verify(readback, properties)
                context["notion_page"] = readback
                return ProviderOperationResult(
                    operation_id=operation.operation_id,
                    provider=self.provider_name,
                    operation_type=operation.operation_type,
                    attempt=attempt,
                    applied=True,
                    readback_verified=True,
                    provider_object_references=(readback.id,),
                )
            if operation.operation_type == ProviderOperationType.VERIFY_RECORD:
                page = context.get("notion_page")
                if not isinstance(page, NotionPage):
                    raise ProviderExecutionError(
                        ErrorClassification.READBACK_MISMATCH,
                        "Notion verification has no applied record",
                    )
                expected = self._properties(operation)
                readback = self._provider.get_page(page.id)
                self._verify(readback, expected)
                return ProviderOperationResult(
                    operation_id=operation.operation_id,
                    provider=self.provider_name,
                    operation_type=operation.operation_type,
                    attempt=attempt,
                    readback_verified=True,
                    provider_object_references=(page.id,),
                )
        except AdapterError as exc:
            classification = (
                ErrorClassification.RETRYABLE_PROVIDER_5XX
                if exc.retryable
                else ErrorClassification.PERMISSION_FAILURE
            )
            raise ProviderExecutionError(
                classification,
                str(exc),
                retry_after_seconds=exc.retry_after_seconds,
            ) from exc
        raise ProviderExecutionError(
            ErrorClassification.VALIDATION_FAILURE,
            f"unsupported Notion execution operation: {operation.operation_type}",
        )

    def readback_before_retry(
        self,
        operation: ProviderOperation,
        context: dict[str, Any],
    ) -> ProviderOperationResult | None:
        identity = operation.payload.get("identity")
        page = self._find(identity)
        if page is None:
            return None
        expected = self._properties(operation)
        self._verify(page, expected)
        context["notion_page"] = page
        return ProviderOperationResult(
            operation_id=operation.operation_id,
            provider=self.provider_name,
            operation_type=operation.operation_type,
            attempt=1,
            applied=True,
            readback_verified=True,
            provider_object_references=(page.id,),
            evidence={"recovered_by_readback": "true"},
        )

    def compensate_operation(
        self,
        operation: ProviderOperation,
        context: dict[str, Any],
        *,
        attempt: int,
    ) -> ProviderOperationResult:
        del context
        raise ProviderExecutionError(
            ErrorClassification.UNKNOWN_REVIEW,
            f"Notion operation {operation.operation_id} requires manual recovery",
        )
