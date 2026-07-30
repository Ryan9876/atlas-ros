"""Deterministic pre-provider circuit breaker for Quick Initialization."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from enum import Enum
from typing import Literal, TypeVar
from uuid import uuid4

from atlas_ros.contracts.authority import (
    InitializationReadBudget,
    InitializationRejectedCall,
    InitializationTraceEntry,
)

_T = TypeVar("_T")


class InitializationState(str, Enum):
    """Typed lifecycle states for one Quick Initialization operation."""

    NOT_STARTED = "NOT_STARTED"
    READING_AUTHORITY = "READING_AUTHORITY"
    READING_RELEASE_INDEX = "READING_RELEASE_INDEX"
    READING_IMMUTABLE_MANIFEST = "READING_IMMUTABLE_MANIFEST"
    READING_SYSTEM_STATE = "READING_SYSTEM_STATE"
    READING_INTEGRATION_INVENTORY = "READING_INTEGRATION_INVENTORY"
    CHECKING_CONNECTOR_LIVENESS = "CHECKING_CONNECTOR_LIVENESS"
    READY = "READY"
    READY_WITH_WARNINGS = "READY_WITH_WARNINGS"
    INITIALIZATION_BLOCKED = "INITIALIZATION_BLOCKED"


class InitializationCapability(str, Enum):
    """Initialization-scoped capabilities evaluated before provider execution."""

    GITHUB_AUTHORITY_READ = "github.authority.read"
    GITHUB_RELEASE_INDEX_READ = "github.release_index.read"
    GITHUB_IMMUTABLE_MANIFEST_READ = "github.immutable_manifest.read"
    NOTION_SYSTEM_STATE_READ = "notion.system_state.read"
    NOTION_INTEGRATION_INVENTORY_READ = "notion.integration_inventory.read"
    TODOIST_LIVENESS_READ = "todoist.connector_liveness.read"

    GENERIC_REPOSITORY_SEARCH = "github.repository.search"
    ARBITRARY_GITHUB_FILE_READ = "github.file.read.arbitrary"
    PLUGIN_SKILL_DISCOVERY = "plugin.skill.discovery"
    GOOGLE_DRIVE_READ = "google_drive.read"
    NOTION_WORKSPACE_SEARCH = "notion.workspace.search"
    TODOIST_WRITE = "todoist.write"
    EMAIL = "email"
    MESSAGING = "messaging"
    CALENDAR = "calendar"
    SCHEDULING = "scheduling"
    CREDENTIAL_CHANGE = "credential.change"
    DELETION = "deletion"
    SCHEMA_CHANGE = "schema.change"
    PUBLICATION = "publication"
    AUTHORITY_CHANGE = "authority.change"
    WEB_SEARCH = "web.search"
    INTENT_MEMORY = "intent_memory"
    INTENT_USER_CONTROL = "intent_user_control"
    PROFILE_LOAD = "profile.load"
    COMMUNICATION_POLICY = "communication_policy.compile"
    PLAYBOOK = "situational_playbook.select"
    DIAGNOSTICS_EXTERNAL = "diagnostics.external"
    TELEMETRY_EXTERNAL = "telemetry.external"


_TERMINAL_STATES = frozenset(
    {
        InitializationState.READY,
        InitializationState.READY_WITH_WARNINGS,
        InitializationState.INITIALIZATION_BLOCKED,
    }
)

_EXPECTED_CAPABILITY_BY_STATE: Mapping[InitializationState, InitializationCapability] = {
    InitializationState.READING_AUTHORITY: InitializationCapability.GITHUB_AUTHORITY_READ,
    InitializationState.READING_RELEASE_INDEX: (
        InitializationCapability.GITHUB_RELEASE_INDEX_READ
    ),
    InitializationState.READING_IMMUTABLE_MANIFEST: (
        InitializationCapability.GITHUB_IMMUTABLE_MANIFEST_READ
    ),
    InitializationState.READING_SYSTEM_STATE: InitializationCapability.NOTION_SYSTEM_STATE_READ,
    InitializationState.READING_INTEGRATION_INVENTORY: (
        InitializationCapability.NOTION_INTEGRATION_INVENTORY_READ
    ),
    InitializationState.CHECKING_CONNECTOR_LIVENESS: (
        InitializationCapability.TODOIST_LIVENESS_READ
    ),
}

_ALLOWED_TRANSITIONS: Mapping[InitializationState, frozenset[InitializationState]] = {
    InitializationState.NOT_STARTED: frozenset({InitializationState.READING_AUTHORITY}),
    InitializationState.READING_AUTHORITY: frozenset(
        {
            InitializationState.READING_RELEASE_INDEX,
            InitializationState.INITIALIZATION_BLOCKED,
        }
    ),
    InitializationState.READING_RELEASE_INDEX: frozenset(
        {
            InitializationState.READING_IMMUTABLE_MANIFEST,
            InitializationState.INITIALIZATION_BLOCKED,
        }
    ),
    InitializationState.READING_IMMUTABLE_MANIFEST: frozenset(
        {
            InitializationState.READING_SYSTEM_STATE,
            InitializationState.INITIALIZATION_BLOCKED,
        }
    ),
    InitializationState.READING_SYSTEM_STATE: frozenset(
        {
            InitializationState.READING_INTEGRATION_INVENTORY,
            InitializationState.INITIALIZATION_BLOCKED,
        }
    ),
    InitializationState.READING_INTEGRATION_INVENTORY: frozenset(
        {
            InitializationState.CHECKING_CONNECTOR_LIVENESS,
            InitializationState.INITIALIZATION_BLOCKED,
        }
    ),
    InitializationState.CHECKING_CONNECTOR_LIVENESS: frozenset(_TERMINAL_STATES),
    InitializationState.READY: frozenset(),
    InitializationState.READY_WITH_WARNINGS: frozenset(),
    InitializationState.INITIALIZATION_BLOCKED: frozenset(),
}

_ORDERED_CAPABILITIES = (
    InitializationCapability.GITHUB_AUTHORITY_READ,
    InitializationCapability.GITHUB_RELEASE_INDEX_READ,
    InitializationCapability.GITHUB_IMMUTABLE_MANIFEST_READ,
    InitializationCapability.NOTION_SYSTEM_STATE_READ,
    InitializationCapability.NOTION_INTEGRATION_INVENTORY_READ,
    InitializationCapability.TODOIST_LIVENESS_READ,
)

_CONNECTOR_BY_CAPABILITY: Mapping[InitializationCapability, str] = {
    InitializationCapability.GITHUB_AUTHORITY_READ: "GitHub",
    InitializationCapability.GITHUB_RELEASE_INDEX_READ: "GitHub",
    InitializationCapability.GITHUB_IMMUTABLE_MANIFEST_READ: "GitHub",
    InitializationCapability.NOTION_SYSTEM_STATE_READ: "Notion",
    InitializationCapability.NOTION_INTEGRATION_INVENTORY_READ: "Notion",
    InitializationCapability.TODOIST_LIVENESS_READ: "Todoist",
}


class InitializationTransitionError(RuntimeError):
    """Raised when orchestration attempts an invalid state transition."""


class InitializationCallRejected(PermissionError):
    """Raised when the operation-scoped capability allowlist denies a call."""


class InitializationAlreadyTerminal(InitializationCallRejected):
    """Typed proof that a post-terminal provider call was rejected pre-provider."""

    def __init__(
        self,
        *,
        terminal_status: str,
        operation_id: str,
        attempted_capability: str,
        target: str,
        rejection_reason: str,
        sequence: int,
    ) -> None:
        self.terminal_status = terminal_status
        self.operation_id = operation_id
        self.attempted_capability = attempted_capability
        self.target = target
        self.rejection_reason = rejection_reason
        self.sequence = sequence
        self.provider_invoked = False
        super().__init__(
            f"{rejection_reason}: operation={operation_id} status={terminal_status} "
            f"capability={attempted_capability} target={target} sequence={sequence}; "
            "provider_invoked=false"
        )


class TransientInitializationReadError(ConnectionError):
    """Signals a provider read failure eligible for the one bounded retry."""


@dataclass(frozen=True)
class InitializationTargetBindings:
    """Exact targets resolved from the live authority chain."""

    release_index: str
    immutable_manifest: str
    system_state: str
    integration_inventory: str


@dataclass
class InitializationOperation:
    """Mutable operation context enforcing sequence, capability, budget, and lock."""

    operation_id: str = field(default_factory=lambda: uuid4().hex)
    retry_budget: int = 1
    clean_cold_read_budget: Literal[6] = 6
    state: InitializationState = InitializationState.NOT_STARTED
    _sequence: int = 0
    _trace: list[InitializationTraceEntry] = field(default_factory=list)
    _rejected: list[InitializationRejectedCall] = field(default_factory=list)
    _completed_capabilities: set[InitializationCapability] = field(default_factory=set)
    _targets: dict[InitializationCapability, str] = field(
        default_factory=lambda: {
            InitializationCapability.GITHUB_AUTHORITY_READ: (
                "github:governance/AUTHORITY.json@HEAD"
            ),
            InitializationCapability.GITHUB_RELEASE_INDEX_READ: (
                "github:<release-index-from-authority>@HEAD"
            ),
            InitializationCapability.GITHUB_IMMUTABLE_MANIFEST_READ: (
                "github:<manifest-from-authority>@<immutable-commit>"
            ),
            InitializationCapability.NOTION_SYSTEM_STATE_READ: (
                "notion:<system-state-from-authority>"
            ),
            InitializationCapability.NOTION_INTEGRATION_INVENTORY_READ: (
                "notion:<inventory-from-manifest>"
            ),
            InitializationCapability.TODOIST_LIVENESS_READ: (
                "todoist:connector-liveness"
            ),
        }
    )
    attempted_external_reads: int = 0
    completed_external_reads: int = 0
    failed_external_reads: int = 0
    retries: int = 0
    cache_reads: int = 0
    cache_rejections: int = 0
    post_terminal_attempts: int = 0
    post_terminal_executed_calls: int = 0
    _reads_by_connector: dict[str, int] = field(default_factory=dict)
    _reads_by_target: dict[str, int] = field(default_factory=dict)

    @property
    def terminal(self) -> bool:
        return self.state in _TERMINAL_STATES

    @property
    def terminal_status(self) -> str | None:
        return self.state.value if self.terminal else None

    def bind_targets(self, bindings: InitializationTargetBindings) -> None:
        """Bind exact targets once authority and manifest references are known."""
        if self.terminal:
            raise InitializationTransitionError("cannot bind targets after terminal state")
        resolved = {
            InitializationCapability.GITHUB_RELEASE_INDEX_READ: bindings.release_index,
            InitializationCapability.GITHUB_IMMUTABLE_MANIFEST_READ: (
                bindings.immutable_manifest
            ),
            InitializationCapability.NOTION_SYSTEM_STATE_READ: bindings.system_state,
            InitializationCapability.NOTION_INTEGRATION_INVENTORY_READ: (
                bindings.integration_inventory
            ),
        }
        for capability, target in resolved.items():
            current = self._targets[capability]
            if "<" not in current and current != target:
                self._append_trace(
                    capability="target.binding",
                    target=f"{current}->{target}",
                    outcome="rejected",
                    attempt=0,
                    initiator="orchestration",
                    provider_invoked=False,
                    detail=f"attempted to rebind {capability.value}",
                )
                self.block()
                raise InitializationTransitionError(
                    f"initialization target is already bound: {capability.value}"
                )
            self._targets[capability] = target

    def transition(self, new_state: InitializationState) -> None:
        """Advance through the explicit state machine or fail closed."""
        if self.terminal:
            raise InitializationTransitionError(
                f"terminal state is irreversible: {self.state.value} -> {new_state.value}"
            )
        if new_state not in _ALLOWED_TRANSITIONS[self.state]:
            previous = self.state
            self._append_trace(
                capability="state.transition",
                target=f"{previous.value}->{new_state.value}",
                outcome="rejected",
                attempt=0,
                initiator="orchestration",
                provider_invoked=False,
                detail="invalid initialization state transition",
            )
            self.state = InitializationState.INITIALIZATION_BLOCKED
            raise InitializationTransitionError(
                f"invalid initialization transition: {previous.value} -> {new_state.value}"
            )
        self.state = new_state

    def terminalize(self, status: InitializationState) -> None:
        """Activate the irreversible terminal execution lock."""
        if status not in _TERMINAL_STATES:
            raise InitializationTransitionError(f"not a terminal state: {status.value}")
        self.transition(status)

    def block(self) -> None:
        """Fail the operation closed from any non-terminal active state."""
        if self.terminal:
            return
        if self.state is InitializationState.NOT_STARTED:
            self.transition(InitializationState.READING_AUTHORITY)
        self.transition(InitializationState.INITIALIZATION_BLOCKED)

    def record_cache(
        self,
        *,
        outcome: Literal["hit", "rejected"],
        detail: str = "",
    ) -> None:
        """Record authenticated local-cache activity without spending provider budget."""
        self.cache_reads += 1
        if outcome == "rejected":
            self.cache_rejections += 1
        self._append_trace(
            capability="warm_cache",
            target="local:authenticated-immutable-authority-cache",
            outcome=outcome,
            attempt=1,
            initiator="orchestration",
            provider_invoked=False,
            detail=detail,
        )

    def record_internal_validation(self, *, capability: str, detail: str) -> None:
        """Record deterministic local validation without an external call."""
        self._append_trace(
            capability=capability,
            target="local:validated-cached-authority",
            outcome="internal",
            attempt=0,
            initiator="orchestration",
            provider_invoked=False,
            detail=detail,
        )

    def execute_external(
        self,
        *,
        capability: InitializationCapability,
        target: str,
        provider: Callable[[], _T],
        initiator: str = "orchestration",
    ) -> _T:
        """Authorize and execute one exact provider read, with at most one retry."""
        self._authorize(capability=capability, target=target, initiator=initiator)
        max_attempts = 2 if self.retry_budget > 0 else 1
        for attempt in range(1, max_attempts + 1):
            self._enforce_budget(capability=capability, target=target, initiator=initiator)
            self.attempted_external_reads += 1
            connector = _CONNECTOR_BY_CAPABILITY[capability]
            self._reads_by_connector[connector] = self._reads_by_connector.get(connector, 0) + 1
            self._reads_by_target[target] = self._reads_by_target.get(target, 0) + 1
            try:
                result = provider()
            except Exception as error:
                self.failed_external_reads += 1
                self._append_trace(
                    capability=capability.value,
                    target=target,
                    outcome="failed",
                    attempt=attempt,
                    initiator=initiator,
                    provider_invoked=True,
                    detail=str(error),
                )
                if attempt == 1 and self._retry_allowed(error):
                    self.retries += 1
                    continue
                raise
            self.completed_external_reads += 1
            self._completed_capabilities.add(capability)
            self._append_trace(
                capability=capability.value,
                target=target,
                outcome="completed",
                attempt=attempt,
                initiator=initiator,
                provider_invoked=True,
            )
            return result
        raise AssertionError("unreachable initialization provider loop")

    def deny_external(
        self,
        *,
        capability: InitializationCapability,
        target: str,
        initiator: str,
    ) -> None:
        """Exercise the same pre-provider boundary for an explicitly denied call."""
        self._authorize(capability=capability, target=target, initiator=initiator)
        raise AssertionError("denied capability unexpectedly passed authorization")

    def expected_read_plan(
        self,
        *,
        include_immutable_external_reads: bool = True,
    ) -> tuple[str, ...]:
        capabilities = (
            _ORDERED_CAPABILITIES
            if include_immutable_external_reads
            else (
                InitializationCapability.GITHUB_AUTHORITY_READ,
                InitializationCapability.NOTION_SYSTEM_STATE_READ,
                InitializationCapability.NOTION_INTEGRATION_INVENTORY_READ,
                InitializationCapability.TODOIST_LIVENESS_READ,
            )
        )
        return tuple(
            f"{index + 1}:{capability.value}:{self._targets[capability]}"
            for index, capability in enumerate(capabilities)
        )

    def trace(self) -> tuple[InitializationTraceEntry, ...]:
        return tuple(self._trace)

    def rejected_calls(self) -> tuple[InitializationRejectedCall, ...]:
        return tuple(self._rejected)

    def read_budget(self, *, expected_external_reads: int = 6) -> InitializationReadBudget:
        allowed = self.clean_cold_read_budget + self.retries
        return InitializationReadBudget(
            expected_external_reads=expected_external_reads,
            maximum_clean_cold_reads=self.clean_cold_read_budget,
            attempted_external_reads=self.attempted_external_reads,
            completed_external_reads=self.completed_external_reads,
            failed_external_reads=self.failed_external_reads,
            retry_count=self.retries,
            cache_reads=self.cache_reads,
            cache_rejections=self.cache_rejections,
            rejected_calls=len(self._rejected),
            reads_by_connector=dict(sorted(self._reads_by_connector.items())),
            reads_by_target=dict(sorted(self._reads_by_target.items())),
            budget_passed=(
                self.attempted_external_reads <= allowed
                and self.post_terminal_executed_calls == 0
            ),
        )

    def _authorize(
        self,
        *,
        capability: InitializationCapability,
        target: str,
        initiator: str,
    ) -> None:
        if self.terminal:
            self.post_terminal_attempts += 1
            sequence = self._reject(
                capability=capability,
                target=target,
                reason="initialization operation is already terminal",
                initiator=initiator,
            )
            raise InitializationAlreadyTerminal(
                terminal_status=self.state.value,
                operation_id=self.operation_id,
                attempted_capability=capability.value,
                target=target,
                rejection_reason="initialization operation is already terminal",
                sequence=sequence,
            )
        expected = _EXPECTED_CAPABILITY_BY_STATE.get(self.state)
        if capability is not expected:
            reason = (
                f"capability is not allowed in state {self.state.value}; "
                f"expected {expected.value if expected else 'no provider capability'}"
            )
            self._reject(
                capability=capability,
                target=target,
                reason=reason,
                initiator=initiator,
            )
            self.block()
            raise InitializationCallRejected(reason)
        expected_target = self._targets[capability]
        if target != expected_target:
            reason = f"target is not authorized: expected {expected_target}, received {target}"
            self._reject(
                capability=capability,
                target=target,
                reason=reason,
                initiator=initiator,
            )
            self.block()
            raise InitializationCallRejected(reason)
        if capability in self._completed_capabilities:
            reason = f"approved initialization read already completed: {capability.value}"
            self._reject(
                capability=capability,
                target=target,
                reason=reason,
                initiator=initiator,
            )
            self.block()
            raise InitializationCallRejected(reason)

    def _enforce_budget(
        self,
        *,
        capability: InitializationCapability,
        target: str,
        initiator: str,
    ) -> None:
        maximum = self.clean_cold_read_budget + self.retry_budget
        if self.attempted_external_reads < maximum:
            return
        reason = f"initialization external-read budget exhausted: maximum={maximum}"
        self._reject(
            capability=capability,
            target=target,
            reason=reason,
            initiator=initiator,
        )
        self.block()
        raise InitializationCallRejected(reason)

    def _retry_allowed(self, error: Exception) -> bool:
        if self.retries >= self.retry_budget or self.terminal:
            return False
        return isinstance(
            error,
            (TransientInitializationReadError, TimeoutError, ConnectionError),
        ) and not isinstance(error, PermissionError)

    def _reject(
        self,
        *,
        capability: InitializationCapability,
        target: str,
        reason: str,
        initiator: str,
    ) -> int:
        self._sequence += 1
        sequence = self._sequence
        rejected = InitializationRejectedCall(
            sequence=sequence,
            state=self.state.value,
            capability=capability.value,
            target=target,
            rejection_reason=reason,
            initiator=initiator,
            provider_invoked=False,
        )
        self._rejected.append(rejected)
        self._trace.append(
            InitializationTraceEntry(
                sequence=sequence,
                state=self.state.value,
                capability=capability.value,
                target=target,
                outcome="rejected",
                attempt=0,
                initiator=initiator,
                provider_invoked=False,
                detail=reason,
            )
        )
        return sequence

    def _append_trace(
        self,
        *,
        capability: str,
        target: str,
        outcome: Literal["completed", "failed", "rejected", "hit", "internal"],
        attempt: int,
        initiator: str,
        provider_invoked: bool,
        detail: str = "",
    ) -> None:
        self._sequence += 1
        self._trace.append(
            InitializationTraceEntry(
                sequence=self._sequence,
                state=self.state.value,
                capability=capability,
                target=target,
                outcome=outcome,
                attempt=attempt,
                initiator=initiator,
                provider_invoked=provider_invoked,
                detail=detail,
            )
        )
