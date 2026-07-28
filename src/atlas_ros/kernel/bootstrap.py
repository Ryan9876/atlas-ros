"""GitHub-first, provider-neutral authority bootstrap verification."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping
from datetime import datetime
from pathlib import PurePosixPath
from time import perf_counter
from typing import Any, Literal, TypeVar

from atlas_ros.contracts.authority import (
    InitializationIntegrationResult,
    InitializationReceipt,
    InitializationStageTiming,
    IntegrationInventorySnapshot,
    SystemStateSnapshot,
)
from atlas_ros.kernel.authority import AuthorityRecord
from atlas_ros.kernel.context import InitializationContext, InitializationResult
from atlas_ros.kernel.digests import sha256_digest
from atlas_ros.ports.authority import (
    AuthorityReader,
    ConnectorLivenessReader,
    DynamicAuthorityReader,
    ImmutableAuthorityCache,
)

_AUTHORITY_PATH = PurePosixPath("governance/AUTHORITY.json")
_RELEASE_INDEX_PATH = PurePosixPath("governance/RELEASE_INDEX.md")
_REQUIRED_V7_INTEGRATIONS = frozenset({"GitHub", "Notion", "Todoist"})
_WARM_CACHE_KEY = "atlas-quick-initialization-immutable-authority-v1"
_WARM_PAYLOAD_SCHEMA = "1.0"
_T = TypeVar("_T")


class InitializationError(ValueError):
    """Raised when authoritative initialization evidence is incomplete or contradictory."""


def render_release_index(authority: AuthorityRecord) -> str:
    """Render the only supported human-readable projection of the authority record."""
    active = authority.active_release
    rollback = authority.immediate_rollback
    return (
        "# Atlas ROS Release Index\n\n"
        "This file is generated from governance/AUTHORITY.json; do not edit it directly.\n\n"
        "## Active Release\n\n"
        f"- Version: {active.version}\n"
        f"- Status: {active.status}\n"
        f"- Immutable commit: {active.immutable_commit}\n"
        f"- Tag: {active.tag}\n"
        f"- Manifest: {active.manifest_path}\n"
        f"- Release: {active.release_url}\n\n"
        "## Immediate Rollback\n\n"
        f"- Version: {rollback.version}\n"
        f"- Immutable commit: {rollback.immutable_commit}\n"
        f"- Tag: {rollback.tag}\n"
        f"- Release: {rollback.release_url}\n"
    )


def _parse_authority(text: str) -> AuthorityRecord:
    try:
        raw: Any = json.loads(text)
    except json.JSONDecodeError as error:
        raise InitializationError("AUTHORITY.json is not valid JSON") from error
    try:
        return AuthorityRecord.model_validate(raw)
    except ValueError as error:
        raise InitializationError(f"AUTHORITY.json is invalid: {error}") from error


def initialize(reader: AuthorityReader) -> InitializationContext:
    """Verify GitHub-controlled authority evidence before dynamic-state reads."""
    authority = _read_live_authority(reader)
    return _read_and_validate_immutable(reader, authority)


def initialize_full(
    authority_reader: AuthorityReader,
    dynamic_reader: DynamicAuthorityReader,
) -> InitializationContext:
    """Verify GitHub authority, System State, and Integration Inventory together."""
    context = initialize(authority_reader)
    system_state = dynamic_reader.read_system_state(context.system_state_url)
    inventory = dynamic_reader.read_integration_inventory(
        context.integration_inventory_url
    )
    _verify_system_state(context, system_state)
    _verify_integration_inventory(inventory)
    return context


def quick_initialize(
    authority_reader: AuthorityReader,
    dynamic_reader: DynamicAuthorityReader,
    liveness_reader: ConnectorLivenessReader,
    *,
    warm_cache: ImmutableAuthorityCache | None = None,
    warm_auth_token: str | None = None,
    timer: Callable[[], float] = perf_counter,
) -> InitializationResult:
    """Run one compact fail-closed Quick Initialization operation."""
    started = timer()
    timings: list[InitializationStageTiming] = []
    warnings: list[str] = []
    cache_hit = False
    cache_rejection_reason: str | None = None
    execution_path: Literal["cold", "warm", "warm_fallback_to_cold"] = "cold"
    authority: AuthorityRecord | None = None
    context: InitializationContext | None = None
    system_state: SystemStateSnapshot | None = None
    inventory: IntegrationInventorySnapshot | None = None
    integration_results: tuple[InitializationIntegrationResult, ...] = ()
    release_index_valid = False
    manifest_valid = False
    system_state_valid = False

    try:
        live_authority = _timed(
            "live_authority_read",
            timer,
            timings,
            lambda: _read_live_authority(authority_reader),
        )
        authority = live_authority
        source_digest = _immutable_source_digest(live_authority)

        if warm_cache is not None and warm_auth_token is not None:
            try:
                context = _timed(
                    "warm_cache_lookup",
                    timer,
                    timings,
                    lambda: _read_cached_immutable(
                        warm_cache,
                        warm_auth_token,
                        source_digest,
                        live_authority,
                    ),
                )
                cache_hit = True
                execution_path = "warm"
                release_index_valid = True
                manifest_valid = True
            except (KeyError, OSError, TypeError, ValueError) as error:
                cache_rejection_reason = str(error)
                if _cache_unavailable(cache_rejection_reason):
                    execution_path = "cold"
                else:
                    execution_path = "warm_fallback_to_cold"
                    if not _cache_expired(cache_rejection_reason):
                        warnings.append(f"warm cache rejected: {cache_rejection_reason}")

        if context is None:
            release_index = _timed(
                "release_index_read_validation",
                timer,
                timings,
                lambda: _read_release_index(authority_reader, live_authority),
            )
            release_index_valid = True
            manifest = _timed(
                "manifest_read_validation",
                timer,
                timings,
                lambda: _read_manifest(authority_reader, live_authority),
            )
            manifest_valid = True
            context = _build_context(live_authority, release_index, manifest)
            if warm_cache is not None and warm_auth_token is not None:
                try:
                    _timed(
                        "warm_cache_store",
                        timer,
                        timings,
                        lambda: warm_cache.put(
                            key=_WARM_CACHE_KEY,
                            kind="immutable_authority_snapshot",
                            payload=_warm_payload(context),
                            source_digest=source_digest,
                            auth_token=warm_auth_token,
                        ),
                    )
                except (OSError, ValueError) as error:
                    warnings.append(f"warm cache store failed: {error}")

        if context is None:
            raise InitializationError("immutable initialization context was not resolved")
        resolved_context = context

        system_state = _timed(
            "system_state_read",
            timer,
            timings,
            lambda: dynamic_reader.read_system_state(resolved_context.system_state_url),
        )
        _verify_system_state(resolved_context, system_state)
        system_state_valid = True

        inventory = _timed(
            "integration_inventory_read",
            timer,
            timings,
            lambda: dynamic_reader.read_integration_inventory(
                resolved_context.integration_inventory_url
            ),
        )
        _verify_integration_inventory(inventory)

        todoist_live = _timed(
            "todoist_liveness_read",
            timer,
            timings,
            lambda: liveness_reader.read_connector_liveness(frozenset({"Todoist"})),
        )
        if set(todoist_live) != {"Todoist"}:
            raise InitializationError(
                "Todoist liveness probe must return exactly the Todoist result"
            )
        live = {"GitHub": True, "Notion": True, **todoist_live}
        integration_results = _verify_connector_liveness(inventory, live)

        status: Literal["READY", "READY_WITH_WARNINGS"] = (
            "READY_WITH_WARNINGS" if warnings else "READY"
        )
        receipt = InitializationReceipt(
            status=status,
            active_version=live_authority.active_release.version,
            active_commit=live_authority.active_release.immutable_commit,
            immediate_rollback_version=live_authority.immediate_rollback.version,
            immediate_rollback_commit=live_authority.immediate_rollback.immutable_commit,
            authority_model_version=live_authority.authority_model_version,
            authority_agreement=True,
            release_index_digest_valid=release_index_valid,
            manifest_digest_valid=manifest_valid,
            system_state_agreement=system_state_valid,
            published_workspace_valid=system_state.published_workspace_valid,
            required_integrations=integration_results,
            execution_path=execution_path,
            cache_hit=cache_hit,
            cache_rejection_reason=cache_rejection_reason,
            stage_timings=tuple(timings),
            total_elapsed_ms=_elapsed_ms(started, timer()),
            authority_last_verified_at=_parse_timestamp(live_authority.last_verified_at),
            system_state_last_verified_at=system_state.last_verified_at,
            inventory_last_verified_at=inventory.last_verified_at,
            warnings=tuple(warnings),
        )
        return InitializationResult(context=resolved_context, receipt=receipt)
    except Exception as error:
        receipt = InitializationReceipt(
            status="INITIALIZATION_BLOCKED",
            active_version=(authority.active_release.version if authority else None),
            active_commit=(authority.active_release.immutable_commit if authority else None),
            immediate_rollback_version=(
                authority.immediate_rollback.version if authority else None
            ),
            immediate_rollback_commit=(
                authority.immediate_rollback.immutable_commit if authority else None
            ),
            authority_model_version=(authority.authority_model_version if authority else None),
            authority_agreement=context is not None,
            release_index_digest_valid=release_index_valid,
            manifest_digest_valid=manifest_valid,
            system_state_agreement=system_state_valid,
            published_workspace_valid=(
                system_state.published_workspace_valid if system_state else False
            ),
            required_integrations=integration_results,
            execution_path=execution_path,
            cache_hit=cache_hit,
            cache_rejection_reason=cache_rejection_reason,
            stage_timings=tuple(timings),
            total_elapsed_ms=_elapsed_ms(started, timer()),
            authority_last_verified_at=(
                _parse_timestamp(authority.last_verified_at) if authority else None
            ),
            system_state_last_verified_at=(
                system_state.last_verified_at if system_state else None
            ),
            inventory_last_verified_at=(
                inventory.last_verified_at if inventory else None
            ),
            warnings=tuple(warnings),
            blocked_condition=str(error),
        )
        return InitializationResult(context=None, receipt=receipt)


def _read_live_authority(reader: AuthorityReader) -> AuthorityRecord:
    authority = _parse_authority(reader.read_text(_AUTHORITY_PATH, ref="HEAD"))
    active = authority.active_release
    if active.tag != f"v{active.version.removeprefix('v')}":
        raise InitializationError("active release version and tag disagree")
    if not str(active.manifest_url).endswith(active.manifest_path):
        raise InitializationError(
            "active manifest URL does not resolve to the declared manifest path"
        )
    return authority


def _read_and_validate_immutable(
    reader: AuthorityReader,
    authority: AuthorityRecord,
) -> InitializationContext:
    release_index = _read_release_index(reader, authority)
    manifest = _read_manifest(reader, authority)
    return _build_context(authority, release_index, manifest)


def _read_release_index(
    reader: AuthorityReader,
    authority: AuthorityRecord,
) -> str:
    release_index = reader.read_text(_RELEASE_INDEX_PATH, ref="HEAD")
    _verify_release_index(authority, release_index)
    return release_index


def _read_manifest(
    reader: AuthorityReader,
    authority: AuthorityRecord,
) -> str:
    active = authority.active_release
    manifest = reader.read_text(
        PurePosixPath(active.manifest_path),
        ref=active.immutable_commit,
    )
    _verify_manifest(authority, manifest)
    return manifest


def _read_cached_immutable(
    cache: ImmutableAuthorityCache,
    auth_token: str,
    source_digest: str,
    authority: AuthorityRecord,
) -> InitializationContext:
    snapshot = cache.get(
        key=_WARM_CACHE_KEY,
        auth_token=auth_token,
        expected_source_digest=source_digest,
    )
    if snapshot.kind != "immutable_authority_snapshot":
        raise InitializationError("warm immutable authority snapshot kind is invalid")
    payload = snapshot.payload
    if not isinstance(payload, dict):
        raise InitializationError("warm immutable authority payload must be an object")
    expected = {
        "schema_version": _WARM_PAYLOAD_SCHEMA,
        "repository": authority.repository,
        "immutable_commit": authority.active_release.immutable_commit,
        "manifest_path": authority.active_release.manifest_path,
        "release_index_sha256": authority.release_index.sha256,
        "manifest_sha256": authority.active_release.manifest_sha256,
    }
    for key, value in expected.items():
        if payload.get(key) != value:
            raise InitializationError(f"warm immutable authority {key} is stale or mismatched")
    release_index = payload.get("release_index_markdown")
    manifest = payload.get("release_manifest_markdown")
    if not isinstance(release_index, str) or not isinstance(manifest, str):
        raise InitializationError("warm immutable authority documents are invalid")
    _verify_release_index(authority, release_index)
    _verify_manifest(authority, manifest)
    return _build_context(authority, release_index, manifest)


def _warm_payload(context: InitializationContext) -> dict[str, str]:
    authority = context.authority
    return {
        "schema_version": _WARM_PAYLOAD_SCHEMA,
        "repository": authority.repository,
        "immutable_commit": authority.active_release.immutable_commit,
        "manifest_path": authority.active_release.manifest_path,
        "release_index_sha256": authority.release_index.sha256,
        "manifest_sha256": authority.active_release.manifest_sha256,
        "release_index_markdown": context.release_index_markdown,
        "release_manifest_markdown": context.release_manifest_markdown,
    }


def _immutable_source_digest(authority: AuthorityRecord) -> str:
    return sha256_digest(
        {
            "schema_version": _WARM_PAYLOAD_SCHEMA,
            "repository": authority.repository,
            "authority_model_version": authority.authority_model_version,
            "immutable_commit": authority.active_release.immutable_commit,
            "manifest_path": authority.active_release.manifest_path,
            "release_index_sha256": authority.release_index.sha256,
            "manifest_sha256": authority.active_release.manifest_sha256,
        }
    )


def _verify_release_index(authority: AuthorityRecord, release_index: str) -> None:
    if sha256_digest(release_index) != authority.release_index.sha256:
        raise InitializationError(
            "generated RELEASE_INDEX.md digest does not match AUTHORITY.json"
        )
    if release_index != render_release_index(authority):
        raise InitializationError("RELEASE_INDEX.md is not the generated authority projection")


def _verify_manifest(authority: AuthorityRecord, manifest: str) -> None:
    active = authority.active_release
    if sha256_digest(manifest) != active.manifest_sha256:
        raise InitializationError("active manifest digest does not match AUTHORITY.json")
    if active.version not in manifest:
        raise InitializationError("active manifest does not identify the authoritative release")


def _build_context(
    authority: AuthorityRecord,
    release_index: str,
    manifest: str,
) -> InitializationContext:
    return InitializationContext(
        authority=authority,
        release_index_markdown=release_index,
        release_manifest_markdown=manifest,
        system_state_url=str(authority.notion_system_state_url),
        integration_inventory_url=_integration_inventory_reference(manifest),
    )


def _verify_system_state(
    context: InitializationContext,
    snapshot: SystemStateSnapshot,
) -> None:
    authority = context.authority
    if snapshot.active_version != authority.active_release.version:
        raise InitializationError("System State active release disagrees with GitHub authority")
    if snapshot.immediate_rollback_version != authority.immediate_rollback.version:
        raise InitializationError("System State rollback disagrees with GitHub authority")
    if snapshot.authority_model_version != authority.authority_model_version:
        raise InitializationError("System State authority-model version is incompatible")
    if not snapshot.published_workspace_valid:
        raise InitializationError("System State does not confirm a valid published workspace")


def _verify_integration_inventory(snapshot: IntegrationInventorySnapshot) -> None:
    required = {item.name for item in snapshot.integrations if item.required}
    if required != _REQUIRED_V7_INTEGRATIONS:
        raise InitializationError(
            "Integration Inventory required set must be GitHub, Notion, and Todoist"
        )
    for item in snapshot.integrations:
        if not item.required:
            continue
        if item.connection_status != "connected":
            raise InitializationError(f"required integration is not connected: {item.name}")
        if item.approval_status != "approved":
            raise InitializationError(f"required integration is not approved: {item.name}")
        if item.acceptance_status != "passed":
            raise InitializationError(f"required integration has not passed: {item.name}")
        if item.lifecycle_status != "production":
            raise InitializationError(f"required integration is not production: {item.name}")
        if not item.current:
            raise InitializationError(f"required integration is not current: {item.name}")
        if not item.least_privilege_verified:
            raise InitializationError(
                f"required integration lacks least-privilege verification: {item.name}"
            )


def _verify_connector_liveness(
    inventory: IntegrationInventorySnapshot,
    live: Mapping[str, bool],
) -> tuple[InitializationIntegrationResult, ...]:
    if set(live) != _REQUIRED_V7_INTEGRATIONS:
        raise InitializationError(
            "connector liveness result must contain exactly GitHub, Notion, and Todoist"
        )
    inventory_by_name = {item.name: item for item in inventory.integrations if item.required}
    results = tuple(
        InitializationIntegrationResult(
            name=name,
            inventory_ready=True,
            live_readable=bool(live[name]),
        )
        for name in sorted(_REQUIRED_V7_INTEGRATIONS)
    )
    for result in results:
        if result.name not in inventory_by_name:
            raise InitializationError(
                f"connector liveness has no required inventory record: {result.name}"
            )
        if not result.live_readable:
            raise InitializationError(f"required connector is not live-readable: {result.name}")
    return results


def _integration_inventory_reference(manifest: str) -> str:
    markers = (
        ("Integration Inventory data source:", "collection://"),
        ("Integration Inventory authority:", "https://"),
    )
    for marker, prefix in markers:
        for line in manifest.splitlines():
            if line.strip().startswith(marker):
                reference = line.split(marker, 1)[1].strip()
                if reference.startswith(prefix):
                    return reference
    raise InitializationError(
        "active manifest does not provide the Integration Inventory reference"
    )


def _timed(
    stage: str,
    timer: Callable[[], float],
    timings: list[InitializationStageTiming],
    operation: Callable[[], _T],
) -> _T:
    started = timer()
    try:
        return operation()
    finally:
        timings.append(
            InitializationStageTiming(
                stage=stage,
                elapsed_ms=_elapsed_ms(started, timer()),
            )
        )


def _elapsed_ms(started: float, finished: float) -> float:
    return max(0.0, (finished - started) * 1000.0)


def _cache_unavailable(reason: str) -> bool:
    return "unavailable" in reason


def _cache_expired(reason: str) -> bool:
    return "expired" in reason


def _parse_timestamp(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise InitializationError("authority last_verified_at is not ISO-8601") from error
