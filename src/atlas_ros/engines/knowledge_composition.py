from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping
from typing import Any

from atlas_ros.contracts import (
    KnowledgePackage,
    KnowledgePackageV2,
    ReasoningPackage,
    ReasoningPackageV2,
    ReasoningPackageV3,
    deterministic_digest,
)
from atlas_ros.models import (
    KnowledgeDependencyResolver,
    KnowledgeModuleRegistry,
    PlanningModelRegistry,
)

EventSink = Callable[[str, dict[str, str]], None]


class KnowledgeCompositionEngine:
    """Composes governed knowledge without constructing artifacts or execution objects."""

    def __init__(
        self,
        registry: KnowledgeModuleRegistry,
        planning_registry: PlanningModelRegistry | None = None,
        event_sink: EventSink | None = None,
    ) -> None:
        self._registry = registry
        self._planning_registry = planning_registry
        self._event_sink = event_sink

    def compose(
        self,
        reasoning: ReasoningPackage | ReasoningPackageV2,
        module_ids: tuple[str, ...],
        context: dict[str, Any] | None = None,
    ) -> KnowledgePackage:
        """Preserve the v1 compatibility path used by existing consumers."""
        supplied = context or {}
        facts: dict[str, Any] = {}
        unresolved: list[str] = []
        for module_id in module_ids:
            module = self._registry.get(module_id)
            facts.update(module.facts)
            for key in module.required_context:
                if key in supplied:
                    facts[key] = supplied[key]
                elif key not in unresolved:
                    unresolved.append(key)
        return KnowledgePackage(
            correlation_id=reasoning.correlation_id,
            source_component="engines.knowledge_composition",
            module_ids=list(module_ids),
            facts=facts,
            unresolved_questions=unresolved,
        )

    def compose_v2(
        self,
        reasoning: ReasoningPackageV3,
        *,
        context: dict[str, Any] | None = None,
        include_optional: tuple[str, ...] = (),
    ) -> KnowledgePackageV2:
        if self._planning_registry is None:
            raise ValueError("Planning Model registry is required for V2 composition")
        model = self._planning_registry.resolve(
            reasoning.selected_planning_model_id,
            reasoning.selected_planning_model_version_constraint,
            active_only=True,
        )
        if reasoning.contract_version not in model.supported_reasoning_package_versions:
            raise ValueError(
                f"planning model {model.model_id}@{model.version} does not support "
                f"Reasoning Package V{reasoning.contract_version}"
            )
        resolution = KnowledgeDependencyResolver(self._registry).resolve(
            model,
            include_optional=include_optional,
        )
        supplied = {**reasoning.known_inputs, **(context or {})}
        facts: dict[str, Any] = {}
        provenance: dict[str, tuple[str, ...]] = {}
        providers: dict[str, tuple[int, str]] = {}
        governance: list[str] = []
        evidence: list[str] = []
        resolutions: list[str] = []
        module_by_id = {
            module.module_id: module
            for module in (*resolution.required_modules, *resolution.optional_modules)
        }
        for module_id in resolution.composition_order:
            module = module_by_id[module_id]
            material = _plain(module.facts)
            for section_id, contribution in module.section_contributions.items():
                material[f"section:{section_id}"] = _plain(contribution)
            for key, value in material.items():
                existing = providers.get(key)
                if existing is not None:
                    if module.precedence == existing[0]:
                        raise ValueError(f"ambiguous precedence for composed value: {key}")
                    if module.precedence < existing[0]:
                        continue
                    if module.merge_policy == "reject":
                        raise ValueError(f"module merge policy rejects overwrite: {key}")
                    resolutions.append(
                        f"{key}:{existing[1]}->{module.module_id}:{module.merge_policy}"
                    )
                    if module.merge_policy == "append":
                        prior = facts[key]
                        value = [*(prior if isinstance(prior, list) else [prior]), value]
                    elif module.merge_policy == "merge":
                        prior_mapping = facts[key]
                        if not isinstance(prior_mapping, dict) or not isinstance(value, dict):
                            raise ValueError(f"merge policy requires mappings: {key}")
                        value = {**prior_mapping, **value}
                facts[key] = value
                providers[key] = (module.precedence, module.module_id)
                provenance[key] = (*provenance.get(key, ()), f"{module.module_id}@{module.version}")
            governance.extend(module.governance_overlays)
            evidence.extend(module.evidence_overlays)

        missing = tuple(key for key in resolution.required_context if key not in supplied)
        for key, value in supplied.items():
            facts.setdefault(key, value)
            provenance.setdefault(key, ("reasoning_context",))
        configuration_digest = hashlib.sha256(
            json.dumps(
                {
                    "model": f"{model.model_id}@{model.version}",
                    "planning_registry": self._planning_registry.digest(),
                    "module_registry": self._registry.digest(),
                },
                sort_keys=True,
                separators=(",", ":"),
            ).encode()
        ).hexdigest()
        arguments: dict[str, Any] = {
            "correlation_id": reasoning.correlation_id,
            "source_reasoning_reference": (f"reasoning-package/v3/{reasoning.correlation_id}"),
            "selected_planning_model_id": model.model_id,
            "selected_planning_model_version": model.version,
            "required_modules": tuple(
                f"{module.module_id}@{module.version}" for module in resolution.required_modules
            ),
            "optional_modules": tuple(
                f"{module.module_id}@{module.version}" for module in resolution.optional_modules
            ),
            "module_versions": {
                module.module_id: module.version
                for module in (*resolution.required_modules, *resolution.optional_modules)
            },
            "dependency_graph": resolution.dependency_graph,
            "composition_order": resolution.composition_order,
            "context_bindings": supplied,
            "composed_facts": facts,
            "value_provenance": provenance,
            "governance_overlays": tuple(sorted(set(governance))),
            "evidence_overlays": tuple(sorted(set(evidence))),
            "conflict_resolutions": tuple(resolutions),
            "missing_context_requirements": missing,
            "assumptions": reasoning.planning_assumptions,
            "warnings": resolution.warnings,
            "unresolved_questions": tuple(
                dict.fromkeys((*reasoning.unresolved_planning_questions, *missing))
            ),
            "resolution_trace": resolution.trace,
            "planning_registry_digest": self._planning_registry.digest(),
            "module_registry_digest": self._registry.digest(),
            "configuration_digest": configuration_digest,
            "resolution_digest": resolution.digest,
        }
        unsigned = KnowledgePackageV2(package_digest="0" * 64, **arguments)
        package = KnowledgePackageV2(
            **arguments,
            package_digest=deterministic_digest(unsigned.digest_payload()),
        )
        self._emit(
            "knowledge_package_composed",
            reasoning,
            model.model_id,
            model.version,
            package.package_digest,
            "decision_required" if package.unresolved_questions else "complete",
        )
        return package

    def _emit(
        self,
        event: str,
        reasoning: ReasoningPackageV3,
        model_id: str,
        model_version: str,
        package_digest: str,
        status: str,
    ) -> None:
        if self._event_sink:
            self._event_sink(
                event,
                {
                    "correlation_id": str(reasoning.correlation_id),
                    "model_id": model_id,
                    "model_version": model_version,
                    "package_digest": package_digest,
                    "status": status,
                    "registry_digest": self._registry.digest(),
                },
            )


def _plain(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_plain(item) for item in value]
    return value
