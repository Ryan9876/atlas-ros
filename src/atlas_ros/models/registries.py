from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field, fields, is_dataclass
from types import MappingProxyType
from typing import Any, TypeVar

SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")


@dataclass(frozen=True, order=True)
class SemanticVersion:
    major: int
    minor: int
    patch: int

    @classmethod
    def parse(cls, value: str) -> SemanticVersion:
        match = SEMVER.fullmatch(value)
        if not match:
            raise ValueError(f"invalid semantic version: {value}")
        return cls(*(int(part) for part in match.groups()))

    def __str__(self) -> str:
        return f"{self.major}.{self.minor}.{self.patch}"


def version_satisfies(version: str, constraint: str = "*") -> bool:
    candidate = SemanticVersion.parse(version)
    normalized = constraint.strip()
    if normalized in {"", "*"}:
        return True
    if normalized.startswith("^"):
        floor = SemanticVersion.parse(normalized[1:])
        ceiling = SemanticVersion(floor.major + 1, 0, 0)
        return floor <= candidate < ceiling
    if normalized.startswith("~"):
        floor = SemanticVersion.parse(normalized[1:])
        ceiling = SemanticVersion(floor.major, floor.minor + 1, 0)
        return floor <= candidate < ceiling
    for specifier in (part.strip() for part in normalized.split(",")):
        operator = next(
            (item for item in ("==", ">=", "<=", ">", "<") if specifier.startswith(item)),
            "==",
        )
        target = SemanticVersion.parse(specifier.removeprefix(operator))
        if operator == "==" and candidate != target:
            return False
        if operator == ">=" and candidate < target:
            return False
        if operator == "<=" and candidate > target:
            return False
        if operator == ">" and candidate <= target:
            return False
        if operator == "<" and candidate >= target:
            return False
    return True


def _freeze_mapping(value: Mapping[str, Any]) -> Mapping[str, Any]:
    frozen: dict[str, Any] = {}
    for key, item in value.items():
        if isinstance(item, Mapping):
            frozen[str(key)] = _freeze_mapping(item)
        elif isinstance(item, list | tuple):
            frozen[str(key)] = tuple(item)
        else:
            frozen[str(key)] = item
    return MappingProxyType(frozen)


@dataclass(frozen=True)
class ModuleDependency:
    module_id: str
    version_constraint: str = "*"

    def __post_init__(self) -> None:
        if not self.module_id.strip():
            raise ValueError("dependency module id is required")


@dataclass(frozen=True)
class SectionDefinition:
    section_id: str
    title: str
    required: bool = True
    dependencies: tuple[str, ...] = ()
    contribution_keys: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.section_id.strip() or not self.title.strip():
            raise ValueError("section id and title are required")


@dataclass(frozen=True)
class KnowledgeModule:
    module_id: str
    facts: Mapping[str, Any] = field(default_factory=dict)
    required_context: tuple[str, ...] = ()
    version: str = "1.0.0"
    category: str = "planning"
    lifecycle_status: str = "active"
    purpose: str = ""
    provided_knowledge_keys: tuple[str, ...] = ()
    optional_context: tuple[str, ...] = ()
    required_dependencies: tuple[ModuleDependency, ...] = ()
    optional_dependencies: tuple[ModuleDependency, ...] = ()
    declared_conflicts: tuple[str, ...] = ()
    precedence: int = 0
    merge_policy: str = "reject"
    governance_overlays: tuple[str, ...] = ()
    evidence_overlays: tuple[str, ...] = ()
    section_contributions: Mapping[str, Any] = field(default_factory=dict)
    validation_rules: tuple[str, ...] = ()
    supported_knowledge_package_versions: tuple[int, ...] = (2,)
    deprecated_reason: str = ""
    replacement_module: str = ""

    def __post_init__(self) -> None:
        if not self.module_id.strip():
            raise ValueError("knowledge module id is required")
        SemanticVersion.parse(self.version)
        if self.lifecycle_status not in {"active", "deprecated", "retired"}:
            raise ValueError(f"invalid module lifecycle status: {self.lifecycle_status}")
        if self.merge_policy not in {"reject", "replace", "append", "merge"}:
            raise ValueError(f"invalid module merge policy: {self.merge_policy}")
        object.__setattr__(self, "facts", _freeze_mapping(self.facts))
        object.__setattr__(
            self,
            "section_contributions",
            _freeze_mapping(self.section_contributions),
        )


@dataclass(frozen=True)
class PlanningModel:
    model_id: str
    responsibility_template: str = ""
    outcome_template: str = ""
    default_owner: str = ""
    default_workstream: str = ""
    version: str = "1.0.0"
    lifecycle_status: str = "active"
    purpose: str = ""
    supported_management_patterns: tuple[str, ...] = ()
    artifact_type: str = "management_artifact"
    sections: tuple[SectionDefinition, ...] = ()
    planning_rules: tuple[str, ...] = ()
    governance_rules: tuple[str, ...] = ()
    required_approvals: tuple[str, ...] = ()
    escalation_requirements: tuple[str, ...] = ()
    completion_evidence: tuple[str, ...] = ()
    required_modules: tuple[ModuleDependency, ...] = ()
    optional_modules: tuple[ModuleDependency, ...] = ()
    allow_degraded_composition: bool = False
    supported_reasoning_package_versions: tuple[int, ...] = (3,)
    supported_knowledge_package_versions: tuple[int, ...] = (2,)
    supported_management_package_versions: tuple[int, ...] = (2,)
    validation_rules: tuple[str, ...] = ()
    deprecated_reason: str = ""
    replacement_model: str = ""

    def __post_init__(self) -> None:
        if not self.model_id.strip():
            raise ValueError("planning model id is required")
        SemanticVersion.parse(self.version)
        if self.lifecycle_status not in {"active", "deprecated", "retired"}:
            raise ValueError(f"invalid model lifecycle status: {self.lifecycle_status}")
        if not self.sections and (
            not self.responsibility_template.strip() or not self.outcome_template.strip()
        ):
            raise ValueError("planning model templates or sections are required")
        section_ids = [section.section_id for section in self.sections]
        if len(section_ids) != len(set(section_ids)):
            raise ValueError("planning model section ids must be unique")


T = TypeVar("T", KnowledgeModule, PlanningModel)


class _VersionedRegistry[T: (KnowledgeModule, PlanningModel)]:
    kind = "registry item"

    def __init__(self, items: Iterable[T] = ()) -> None:
        self._items: dict[tuple[str, str], T] = {}
        for item in items:
            self.register(item)

    def _item_id(self, item: T) -> str:
        raise NotImplementedError

    def _identity(self, item: T) -> tuple[str, str]:
        return self._item_id(item), item.version

    def register(self, item: T) -> None:
        identity = self._identity(item)
        if identity in self._items:
            raise ValueError(f"duplicate {self.kind}: {identity[0]}@{identity[1]}")
        self._items[identity] = item

    def resolve(self, item_id: str, constraint: str = "*", *, active_only: bool = False) -> T:
        known_id = any(registered_id == item_id for registered_id, _ in self._items)
        candidates = [
            item
            for (registered_id, _), item in self._items.items()
            if registered_id == item_id
            and version_satisfies(item.version, constraint)
            and (not active_only or item.lifecycle_status == "active")
            and item.lifecycle_status != "retired"
        ]
        if not candidates:
            if not known_id:
                raise KeyError(f"unknown {self.kind}: {item_id}")
            raise KeyError(f"unsupported {self.kind} version: {item_id}@{constraint}")
        return max(candidates, key=lambda item: SemanticVersion.parse(item.version))

    def get(self, item_id: str, version: str | None = None) -> T:
        return self.resolve(item_id, version or "*")

    def list(self) -> tuple[T, ...]:
        return tuple(
            item
            for _, item in sorted(
                self._items.items(),
                key=lambda pair: (pair[0][0], SemanticVersion.parse(pair[0][1])),
            )
        )

    def manifest(self) -> tuple[dict[str, Any], ...]:
        return tuple(_serializable(item) for item in self.list())

    def digest(self) -> str:
        encoded = json.dumps(self.manifest(), sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode()).hexdigest()


def _serializable(item: KnowledgeModule | PlanningModel) -> dict[str, Any]:
    value = _to_plain(item)
    if not isinstance(value, dict):
        raise TypeError("registry item must serialize to a mapping")
    return value


def _to_plain(value: Any) -> Any:
    if is_dataclass(value):
        return {item.name: _to_plain(getattr(value, item.name)) for item in fields(value)}
    if isinstance(value, Mapping):
        return {str(key): _to_plain(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_to_plain(item) for item in value]
    return value


class KnowledgeModuleRegistry(_VersionedRegistry[KnowledgeModule]):
    kind = "knowledge module"

    def __init__(self, modules: tuple[KnowledgeModule, ...] = ()) -> None:
        super().__init__(modules)

    def _item_id(self, item: KnowledgeModule) -> str:
        return item.module_id


class PlanningModelRegistry(_VersionedRegistry[PlanningModel]):
    kind = "planning model"

    def __init__(self, models: tuple[PlanningModel, ...] = ()) -> None:
        super().__init__(models)

    def _item_id(self, item: PlanningModel) -> str:
        return item.model_id
