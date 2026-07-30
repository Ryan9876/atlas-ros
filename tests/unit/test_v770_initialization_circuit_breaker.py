from __future__ import annotations

import ast
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath

import pytest

from atlas_ros.contracts.authority import (
    IntegrationInventorySnapshot,
    IntegrationStatusSnapshot,
    SystemStateSnapshot,
)
from atlas_ros.kernel.bootstrap import quick_initialize
from atlas_ros.kernel.digests import sha256_digest
from atlas_ros.kernel.initialization_circuit_breaker import (
    InitializationAlreadyTerminal,
    InitializationCallRejected,
    InitializationCapability,
    InitializationOperation,
    InitializationState,
    InitializationTargetBindings,
    InitializationTransitionError,
    TransientInitializationReadError,
)
from atlas_ros.runtime.warm import WarmRuntimeCache, WarmRuntimeConfig
from tools.release.authority_compiler import (
    ActiveReleaseSpec,
    AuthorityCompilationSpec,
    RollbackReleaseSpec,
    compile_authority,
)


class FakeAuthorityReader:
    def __init__(
        self,
        values: dict[tuple[str, str], str],
        *,
        transient_failures: int = 0,
    ) -> None:
        self.values = values
        self.transient_failures = transient_failures
        self.reads: list[tuple[str, str]] = []

    def read_text(self, path: PurePosixPath, *, ref: str) -> str:
        key = (path.as_posix(), ref)
        self.reads.append(key)
        if self.transient_failures:
            self.transient_failures -= 1
            raise TransientInitializationReadError("temporary connector timeout")
        return self.values[key]


class FakeDynamicReader:
    def __init__(self) -> None:
        now = datetime(2026, 7, 29, 20, 0, tzinfo=UTC)
        self.system_state = SystemStateSnapshot(
            active_version="7.6.1",
            immediate_rollback_version="7.6.0",
            authority_model_version="7.0",
            published_workspace_valid=True,
            last_verified_at=now,
        )
        self.inventory = IntegrationInventorySnapshot(
            integrations=tuple(_integration(name) for name in ("GitHub", "Notion", "Todoist")),
            last_verified_at=now,
        )
        self.calls: list[tuple[str, str]] = []

    def read_system_state(self, url: str) -> SystemStateSnapshot:
        self.calls.append(("system_state", url))
        return self.system_state

    def read_integration_inventory(self, reference: str) -> IntegrationInventorySnapshot:
        self.calls.append(("inventory", reference))
        return self.inventory


class FakeLivenessReader:
    def __init__(self, *, live: bool = True) -> None:
        self.live = live
        self.calls = 0

    def read_connector_liveness(self, names: frozenset[str]) -> dict[str, bool]:
        self.calls += 1
        assert names == frozenset({"Todoist"})
        return {"Todoist": self.live}


def _integration(name: str) -> IntegrationStatusSnapshot:
    return IntegrationStatusSnapshot(
        name=name,
        required=True,
        connection_status="connected",
        approval_status="approved",
        acceptance_status="passed",
        lifecycle_status="production",
        current=True,
        least_privilege_verified=True,
    )


def _compiled_reader(*, transient_failures: int = 0) -> FakeAuthorityReader:
    commit = "a" * 40
    manifest_path = "release/RELEASE_MANIFEST_V761.md"
    manifest = (
        "# Atlas ROS v7.6.1\n"
        "Integration Inventory authority: https://app.notion.com/p/inventory\n"
        "Integration Inventory data source: collection://inventory-source\n"
    )
    compiled = compile_authority(
        AuthorityCompilationSpec(
            active=ActiveReleaseSpec(
                version="7.6.1",
                immutable_commit=commit,
                tag="v7.6.1",
                manifest_path=manifest_path,
                manifest_url=(
                    f"https://github.com/Ryan9876/atlas-ros/blob/{commit}/{manifest_path}"
                ),
                manifest_sha256=sha256_digest(manifest),
                release_url="https://github.com/Ryan9876/atlas-ros/releases/tag/v7.6.1",
                source_sha256="b" * 64,
                wheel_sha256="c" * 64,
            ),
            rollback=RollbackReleaseSpec(
                version="7.6.0",
                immutable_commit="d" * 40,
                tag="v7.6.0",
                release_url="https://github.com/Ryan9876/atlas-ros/releases/tag/v7.6.0",
            ),
            notion_system_state_url="https://app.notion.com/p/system-state",
            last_promotion_transaction_id="promotion-v7.6.1",
            last_verified_at="2026-07-29T19:40:00Z",
        )
    )
    return FakeAuthorityReader(
        {
            ("governance/AUTHORITY.json", "HEAD"): compiled.authority_json,
            ("governance/RELEASE_INDEX.md", "HEAD"): compiled.release_index_markdown,
            (manifest_path, commit): manifest,
        },
        transient_failures=transient_failures,
    )


def _cache(tmp_path: Path) -> WarmRuntimeCache:
    return WarmRuntimeCache(
        WarmRuntimeConfig(
            root=tmp_path / "warm",
            auth_token_sha256=hashlib.sha256(b"secret").hexdigest(),
            ttl_seconds=300,
            max_entries=2,
        )
    )


def _run(
    *,
    authority: FakeAuthorityReader | None = None,
    dynamic: FakeDynamicReader | None = None,
    liveness: FakeLivenessReader | None = None,
    operation: InitializationOperation | None = None,
    cache: WarmRuntimeCache | None = None,
):
    return quick_initialize(
        authority or _compiled_reader(),
        dynamic or FakeDynamicReader(),
        liveness or FakeLivenessReader(),
        operation=operation,
        warm_cache=cache,
        warm_auth_token="secret" if cache else None,
    )


def test_clean_cold_path_executes_exactly_six_ordered_external_reads() -> None:
    operation = InitializationOperation(operation_id="cold-six")
    result = _run(operation=operation)

    assert result.receipt.status == "READY"
    assert result.receipt.schema_version == "2.0"
    assert result.receipt.operation_id == "cold-six"
    assert result.receipt.external_read_count == 6
    assert result.receipt.read_budget is not None
    assert result.receipt.read_budget.expected_external_reads == 6
    assert result.receipt.read_budget.attempted_external_reads == 6
    assert result.receipt.read_budget.budget_passed is True
    assert result.receipt.terminal_lock_activated is True
    assert result.receipt.post_terminal_executed_calls == 0
    assert len(result.receipt.expected_read_plan) == 6
    completed = [item for item in result.receipt.actual_trace if item.outcome == "completed"]
    assert [item.capability for item in completed] == [
        InitializationCapability.GITHUB_AUTHORITY_READ.value,
        InitializationCapability.GITHUB_RELEASE_INDEX_READ.value,
        InitializationCapability.GITHUB_IMMUTABLE_MANIFEST_READ.value,
        InitializationCapability.NOTION_SYSTEM_STATE_READ.value,
        InitializationCapability.NOTION_INTEGRATION_INVENTORY_READ.value,
        InitializationCapability.TODOIST_LIVENESS_READ.value,
    ]


def test_clean_warm_path_executes_four_external_reads(tmp_path: Path) -> None:
    cache = _cache(tmp_path)
    _run(cache=cache)
    operation = InitializationOperation(operation_id="warm-four")
    result = _run(cache=cache, operation=operation)

    assert result.receipt.execution_path == "warm"
    assert result.receipt.external_read_count == 4
    assert result.receipt.read_budget is not None
    assert result.receipt.read_budget.expected_external_reads == 4
    assert result.receipt.read_budget.cache_reads == 1
    assert result.receipt.read_budget.cache_rejections == 0
    assert len(result.receipt.expected_read_plan) == 4
    assert all("release_index" not in item for item in result.receipt.expected_read_plan)
    assert all("immutable_manifest" not in item for item in result.receipt.expected_read_plan)


def test_rejected_warm_cache_falls_back_once_without_exploratory_reads(tmp_path: Path) -> None:
    cache = _cache(tmp_path)
    _run(cache=cache)
    for path in (tmp_path / "warm").glob("*.json"):
        path.write_text("not-json", encoding="utf-8")
    result = _run(cache=cache)

    assert result.receipt.status == "READY_WITH_WARNINGS"
    assert result.receipt.execution_path == "warm_fallback_to_cold"
    assert result.receipt.external_read_count == 6
    assert result.receipt.read_budget is not None
    assert result.receipt.read_budget.cache_reads == 1
    assert result.receipt.read_budget.cache_rejections == 1
    assert result.receipt.retry_count == 0


_ALLOWED = {
    InitializationState.NOT_STARTED: {InitializationState.READING_AUTHORITY},
    InitializationState.READING_AUTHORITY: {
        InitializationState.READING_RELEASE_INDEX,
        InitializationState.INITIALIZATION_BLOCKED,
    },
    InitializationState.READING_RELEASE_INDEX: {
        InitializationState.READING_IMMUTABLE_MANIFEST,
        InitializationState.INITIALIZATION_BLOCKED,
    },
    InitializationState.READING_IMMUTABLE_MANIFEST: {
        InitializationState.READING_SYSTEM_STATE,
        InitializationState.INITIALIZATION_BLOCKED,
    },
    InitializationState.READING_SYSTEM_STATE: {
        InitializationState.READING_INTEGRATION_INVENTORY,
        InitializationState.INITIALIZATION_BLOCKED,
    },
    InitializationState.READING_INTEGRATION_INVENTORY: {
        InitializationState.CHECKING_CONNECTOR_LIVENESS,
        InitializationState.INITIALIZATION_BLOCKED,
    },
    InitializationState.CHECKING_CONNECTOR_LIVENESS: {
        InitializationState.READY,
        InitializationState.READY_WITH_WARNINGS,
        InitializationState.INITIALIZATION_BLOCKED,
    },
    InitializationState.READY: set(),
    InitializationState.READY_WITH_WARNINGS: set(),
    InitializationState.INITIALIZATION_BLOCKED: set(),
}


@pytest.mark.parametrize(
    ("source", "target"),
    [
        (source, target)
        for source in InitializationState
        for target in InitializationState
        if target not in _ALLOWED[source]
    ],
)
def test_every_invalid_state_transition_fails_closed(
    source: InitializationState,
    target: InitializationState,
) -> None:
    operation = InitializationOperation(operation_id="invalid-transition")
    operation.state = source

    with pytest.raises(InitializationTransitionError):
        operation.transition(target)

    if source in {
        InitializationState.READY,
        InitializationState.READY_WITH_WARNINGS,
        InitializationState.INITIALIZATION_BLOCKED,
    }:
        assert operation.state is source
    else:
        assert operation.state is InitializationState.INITIALIZATION_BLOCKED


def test_one_transient_retry_is_bounded_to_same_exact_target() -> None:
    authority = _compiled_reader(transient_failures=1)
    result = _run(authority=authority)

    assert result.receipt.status == "READY"
    assert result.receipt.retry_count == 1
    assert result.receipt.external_read_count == 7
    assert authority.reads[:2] == [
        ("governance/AUTHORITY.json", "HEAD"),
        ("governance/AUTHORITY.json", "HEAD"),
    ]
    assert result.receipt.read_budget is not None
    assert result.receipt.read_budget.budget_passed is True


def test_integrity_contradiction_is_not_retried() -> None:
    authority = _compiled_reader()
    authority.values[("governance/RELEASE_INDEX.md", "HEAD")] = "tampered"
    result = _run(authority=authority)

    assert result.receipt.status == "INITIALIZATION_BLOCKED"
    assert result.receipt.retry_count == 0
    assert result.receipt.external_read_count == 2
    assert "digest" in (result.receipt.blocked_condition or "")


@pytest.mark.parametrize(
    "terminal",
    [
        InitializationState.READY,
        InitializationState.READY_WITH_WARNINGS,
        InitializationState.INITIALIZATION_BLOCKED,
    ],
)
def test_terminal_lock_rejects_after_every_terminal_state(terminal: InitializationState) -> None:
    operation = InitializationOperation(operation_id=f"terminal-{terminal.value}")
    operation.state = terminal
    invoked = False

    def provider() -> str:
        nonlocal invoked
        invoked = True
        return "unexpected"

    with pytest.raises(InitializationAlreadyTerminal) as captured:
        operation.execute_external(
            capability=InitializationCapability.GITHUB_AUTHORITY_READ,
            target="github:governance/AUTHORITY.json@HEAD",
            provider=provider,
            initiator="response_generation",
        )

    assert invoked is False
    assert captured.value.provider_invoked is False
    assert captured.value.terminal_status == terminal.value
    assert operation.post_terminal_executed_calls == 0


_DENIED_CAPABILITIES = (
    InitializationCapability.GENERIC_REPOSITORY_SEARCH,
    InitializationCapability.ARBITRARY_GITHUB_FILE_READ,
    InitializationCapability.PLUGIN_SKILL_DISCOVERY,
    InitializationCapability.GOOGLE_DRIVE_READ,
    InitializationCapability.NOTION_WORKSPACE_SEARCH,
    InitializationCapability.TODOIST_WRITE,
    InitializationCapability.EMAIL,
    InitializationCapability.MESSAGING,
    InitializationCapability.CALENDAR,
    InitializationCapability.SCHEDULING,
    InitializationCapability.CREDENTIAL_CHANGE,
    InitializationCapability.DELETION,
    InitializationCapability.SCHEMA_CHANGE,
    InitializationCapability.PUBLICATION,
    InitializationCapability.AUTHORITY_CHANGE,
    InitializationCapability.WEB_SEARCH,
    InitializationCapability.INTENT_MEMORY,
    InitializationCapability.INTENT_USER_CONTROL,
    InitializationCapability.PROFILE_LOAD,
    InitializationCapability.COMMUNICATION_POLICY,
    InitializationCapability.PLAYBOOK,
    InitializationCapability.DIAGNOSTICS_EXTERNAL,
    InitializationCapability.TELEMETRY_EXTERNAL,
)


@pytest.mark.parametrize("capability", _DENIED_CAPABILITIES)
def test_operation_allowlist_denies_unapproved_capabilities_before_provider(
    capability: InitializationCapability,
) -> None:
    operation = InitializationOperation(operation_id=f"deny-{capability.value}")
    operation.transition(InitializationState.READING_AUTHORITY)
    invoked = False

    def provider() -> str:
        nonlocal invoked
        invoked = True
        return "unexpected"

    with pytest.raises(InitializationCallRejected):
        operation.execute_external(
            capability=capability,
            target="unapproved:target",
            provider=provider,
            initiator="natural_language_override",
        )

    assert invoked is False
    assert operation.state is InitializationState.INITIALIZATION_BLOCKED
    assert operation.rejected_calls()[-1].provider_invoked is False



def test_resolved_target_cannot_be_rebound() -> None:
    operation = InitializationOperation(operation_id="target-rebind")
    operation.transition(InitializationState.READING_AUTHORITY)
    first = InitializationTargetBindings(
        release_index="github:governance/RELEASE_INDEX.md@HEAD",
        immutable_manifest="github:release/RELEASE_MANIFEST_V761.md@" + "a" * 40,
        system_state="notion:https://app.notion.com/p/system-state",
        integration_inventory="notion:<inventory-from-manifest>",
    )
    operation.bind_targets(first)

    with pytest.raises(InitializationTransitionError, match="already bound"):
        operation.bind_targets(
            InitializationTargetBindings(
                release_index="github:governance/OTHER_INDEX.md@HEAD",
                immutable_manifest=first.immutable_manifest,
                system_state=first.system_state,
                integration_inventory=first.integration_inventory,
            )
        )

    assert operation.state is InitializationState.INITIALIZATION_BLOCKED
    assert operation.trace()[-1].provider_invoked is False

def test_unauthorized_exact_target_is_rejected_before_provider() -> None:
    operation = InitializationOperation(operation_id="wrong-target")
    operation.transition(InitializationState.READING_AUTHORITY)
    invoked = False

    def provider() -> str:
        nonlocal invoked
        invoked = True
        return "unexpected"

    with pytest.raises(InitializationCallRejected, match="target is not authorized"):
        operation.execute_external(
            capability=InitializationCapability.GITHUB_AUTHORITY_READ,
            target="github:README.md@HEAD",
            provider=provider,
        )

    assert invoked is False
    assert operation.state is InitializationState.INITIALIZATION_BLOCKED


def test_second_inventory_and_todoist_reads_are_rejected_post_terminal() -> None:
    operation = InitializationOperation(operation_id="no-second-reads")
    result = _run(operation=operation)
    assert result.receipt.status == "READY"

    for capability, target in (
        (
            InitializationCapability.NOTION_INTEGRATION_INVENTORY_READ,
            "notion:collection://inventory-source",
        ),
        (InitializationCapability.TODOIST_LIVENESS_READ, "todoist:connector-liveness"),
    ):
        invoked = False

        def provider() -> str:
            nonlocal invoked
            invoked = True
            return "unexpected"

        with pytest.raises(InitializationAlreadyTerminal):
            operation.execute_external(
                capability=capability,
                target=target,
                provider=provider,
                initiator="diagnostics",
            )
        assert invoked is False


def test_quick_ready_does_not_escalate_to_full_validation(monkeypatch: pytest.MonkeyPatch) -> None:
    import atlas_ros.kernel.bootstrap as bootstrap

    def forbidden(*_: object, **__: object) -> object:
        raise AssertionError("Full Validation must be a separate operation")

    monkeypatch.setattr(bootstrap, "initialize_full", forbidden)
    result = _run()
    assert result.receipt.status == "READY"


def test_malformed_authority_blocks_after_one_external_read() -> None:
    authority = _compiled_reader()
    authority.values[("governance/AUTHORITY.json", "HEAD")] = "not-json"
    result = _run(authority=authority)

    assert result.receipt.status == "INITIALIZATION_BLOCKED"
    assert result.receipt.external_read_count == 1
    assert result.receipt.retry_count == 0


def test_manifest_mismatch_blocks_without_later_provider_calls() -> None:
    authority = _compiled_reader()
    authority.values[("release/RELEASE_MANIFEST_V761.md", "a" * 40)] = "tampered"
    dynamic = FakeDynamicReader()
    liveness = FakeLivenessReader()
    result = _run(authority=authority, dynamic=dynamic, liveness=liveness)

    assert result.receipt.status == "INITIALIZATION_BLOCKED"
    assert result.receipt.external_read_count == 3
    assert dynamic.calls == []
    assert liveness.calls == 0


def test_missing_inventory_binding_blocks_before_notion_reads() -> None:
    authority = _compiled_reader()
    manifest_key = ("release/RELEASE_MANIFEST_V761.md", "a" * 40)
    manifest = "# Atlas ROS v7.6.1\n"
    raw = json.loads(authority.values[("governance/AUTHORITY.json", "HEAD")])
    raw["active_release"]["manifest_sha256"] = sha256_digest(manifest)
    raw.pop("integrity")
    from atlas_ros.kernel.authority import canonical_authority_payload

    if raw.get("historical_rollbacks") == []:
        raw.pop("historical_rollbacks")
    raw["integrity"] = {
        "algorithm": "sha256",
        "content_sha256": sha256_digest(canonical_authority_payload(raw)),
    }
    authority.values[("governance/AUTHORITY.json", "HEAD")] = json.dumps(raw)
    authority.values[manifest_key] = manifest
    dynamic = FakeDynamicReader()
    result = _run(authority=authority, dynamic=dynamic)

    assert result.receipt.status == "INITIALIZATION_BLOCKED"
    assert "Integration Inventory reference" in (result.receipt.blocked_condition or "")
    assert dynamic.calls == []


def test_system_state_disagreement_stops_before_inventory() -> None:
    dynamic = FakeDynamicReader()
    dynamic.system_state = dynamic.system_state.model_copy(update={"active_version": "7.6.0"})
    result = _run(dynamic=dynamic)

    assert result.receipt.status == "INITIALIZATION_BLOCKED"
    assert [name for name, _ in dynamic.calls] == ["system_state"]


def test_inventory_schema_or_read_error_stops_before_todoist() -> None:
    class InvalidInventoryReader(FakeDynamicReader):
        def read_integration_inventory(self, reference: str) -> IntegrationInventorySnapshot:
            self.calls.append(("inventory", reference))
            raise ValueError("inventory schema error")

    dynamic = InvalidInventoryReader()
    liveness = FakeLivenessReader()
    result = _run(dynamic=dynamic, liveness=liveness)

    assert result.receipt.status == "INITIALIZATION_BLOCKED"
    assert "inventory schema error" in (result.receipt.blocked_condition or "")
    assert liveness.calls == 0
    assert result.receipt.retry_count == 0


def test_todoist_liveness_failure_is_terminal_and_not_retried() -> None:
    result = _run(liveness=FakeLivenessReader(live=False))

    assert result.receipt.status == "INITIALIZATION_BLOCKED"
    assert "Todoist" in (result.receipt.blocked_condition or "")
    assert result.receipt.retry_count == 0
    assert result.receipt.terminal_lock_activated is True
    assert result.receipt.post_terminal_executed_calls == 0


def test_quick_initialization_import_graph_excludes_adaptive_predecessor_surfaces() -> None:
    source = Path("src/atlas_ros/kernel/bootstrap.py").read_text()
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
        elif isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)

    prohibited_fragments = (
        "intent_memory",
        "profile_bundle_v761",
        "user_communication_policy_v761",
        "user_communication_playbooks_v761",
        "plugins",
    )
    assert not {
        module
        for module in imported
        if any(fragment in module for fragment in prohibited_fragments)
    }
