from __future__ import annotations

import hashlib
from importlib.resources import files
from pathlib import Path
from typing import Any

import yaml

from .registries import (
    KnowledgeModule,
    KnowledgeModuleRegistry,
    ModuleDependency,
    PlanningModel,
    PlanningModelRegistry,
    SectionDefinition,
)


def _read_packaged(relative: str) -> dict[str, Any]:
    raw = files("atlas_ros.data").joinpath(relative).read_text(encoding="utf-8")
    payload = yaml.safe_load(raw)
    if not isinstance(payload, dict):
        raise ValueError(f"configuration {relative} must contain a mapping")
    return payload


def _dependency(payload: dict[str, Any]) -> ModuleDependency:
    return ModuleDependency(
        module_id=str(payload["module_id"]),
        version_constraint=str(payload.get("version_constraint", "*")),
    )


def load_planning_model(payload: dict[str, Any]) -> PlanningModel:
    return PlanningModel(
        model_id=str(payload["model_id"]),
        version=str(payload["version"]),
        lifecycle_status=str(payload.get("lifecycle_status", "active")),
        purpose=str(payload.get("purpose", "")),
        supported_management_patterns=tuple(payload.get("supported_management_patterns", ())),
        artifact_type=str(payload.get("artifact_type", "management_artifact")),
        default_owner=str(payload.get("default_owner", "")),
        default_workstream=str(payload.get("default_workstream", "")),
        sections=tuple(
            SectionDefinition(
                section_id=str(item["section_id"]),
                title=str(item["title"]),
                required=bool(item.get("required", True)),
                dependencies=tuple(item.get("dependencies", ())),
                contribution_keys=tuple(item.get("contribution_keys", ())),
            )
            for item in payload.get("sections", ())
        ),
        planning_rules=tuple(payload.get("planning_rules", ())),
        governance_rules=tuple(payload.get("governance_rules", ())),
        required_approvals=tuple(payload.get("required_approvals", ())),
        escalation_requirements=tuple(payload.get("escalation_requirements", ())),
        completion_evidence=tuple(payload.get("completion_evidence", ())),
        required_modules=tuple(_dependency(item) for item in payload.get("required_modules", ())),
        optional_modules=tuple(_dependency(item) for item in payload.get("optional_modules", ())),
        allow_degraded_composition=bool(payload.get("allow_degraded_composition", False)),
        supported_reasoning_package_versions=tuple(
            payload.get("supported_reasoning_package_versions", (3,))
        ),
        supported_knowledge_package_versions=tuple(
            payload.get("supported_knowledge_package_versions", (2,))
        ),
        supported_management_package_versions=tuple(
            payload.get("supported_management_package_versions", (2,))
        ),
        validation_rules=tuple(payload.get("validation_rules", ())),
        deprecated_reason=str(payload.get("deprecated_reason", "")),
        replacement_model=str(payload.get("replacement_model", "")),
    )


def load_knowledge_module(payload: dict[str, Any]) -> KnowledgeModule:
    return KnowledgeModule(
        module_id=str(payload["module_id"]),
        version=str(payload["version"]),
        category=str(payload.get("category", "planning")),
        lifecycle_status=str(payload.get("lifecycle_status", "active")),
        purpose=str(payload.get("purpose", "")),
        facts=payload.get("facts", {}),
        provided_knowledge_keys=tuple(payload.get("provided_knowledge_keys", ())),
        required_context=tuple(payload.get("required_context", ())),
        optional_context=tuple(payload.get("optional_context", ())),
        required_dependencies=tuple(
            _dependency(item) for item in payload.get("required_dependencies", ())
        ),
        optional_dependencies=tuple(
            _dependency(item) for item in payload.get("optional_dependencies", ())
        ),
        declared_conflicts=tuple(payload.get("declared_conflicts", ())),
        precedence=int(payload.get("precedence", 0)),
        merge_policy=str(payload.get("merge_policy", "reject")),
        governance_overlays=tuple(payload.get("governance_overlays", ())),
        evidence_overlays=tuple(payload.get("evidence_overlays", ())),
        section_contributions=payload.get("section_contributions", {}),
        validation_rules=tuple(payload.get("validation_rules", ())),
        supported_knowledge_package_versions=tuple(
            payload.get("supported_knowledge_package_versions", (2,))
        ),
        deprecated_reason=str(payload.get("deprecated_reason", "")),
        replacement_module=str(payload.get("replacement_module", "")),
    )


def load_default_registries() -> tuple[PlanningModelRegistry, KnowledgeModuleRegistry]:
    data_root = files("atlas_ros.data")
    models = tuple(
        load_planning_model(yaml.safe_load(path.read_text(encoding="utf-8")))
        for path in sorted(
            data_root.joinpath("planning-models").iterdir(), key=lambda item: item.name
        )
        if path.name.endswith(".yaml")
    )
    module_items: list[KnowledgeModule] = []
    for path in sorted(
        data_root.joinpath("knowledge-modules").iterdir(), key=lambda item: item.name
    ):
        if not path.name.endswith(".yaml"):
            continue
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"configuration {path.name} must contain a mapping")
        module_items.extend(load_knowledge_module(item) for item in payload["modules"])
    return PlanningModelRegistry(models), KnowledgeModuleRegistry(tuple(module_items))


def configuration_digest(root: Path) -> str:
    paths = sorted(
        (
            *root.joinpath("planning-models").glob("*.yaml"),
            *root.joinpath("knowledge-modules").glob("*.yaml"),
        )
    )
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def assert_source_package_equivalence(source: Path, packaged: Path) -> None:
    if configuration_digest(source) != configuration_digest(packaged):
        raise ValueError("source and packaged registry configurations differ")
