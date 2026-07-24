from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from .registries import (
    KnowledgeModule,
    KnowledgeModuleRegistry,
    ModuleDependency,
    PlanningModel,
)


class DependencyResolutionError(ValueError):
    pass


@dataclass(frozen=True)
class ResolutionResult:
    required_modules: tuple[KnowledgeModule, ...]
    optional_modules: tuple[KnowledgeModule, ...]
    dependency_graph: tuple[tuple[str, tuple[str, ...]], ...]
    composition_order: tuple[str, ...]
    warnings: tuple[str, ...]
    trace: tuple[str, ...]
    required_context: tuple[str, ...]
    digest: str


class KnowledgeDependencyResolver:
    def __init__(self, registry: KnowledgeModuleRegistry) -> None:
        self._registry = registry

    def resolve(
        self,
        model: PlanningModel,
        *,
        include_optional: tuple[str, ...] = (),
    ) -> ResolutionResult:
        selected: dict[str, KnowledgeModule] = {}
        required_ids: set[str] = set()
        optional_ids: set[str] = set()
        graph: dict[str, set[str]] = {}
        trace: list[str] = []
        warnings: list[str] = []
        visiting: list[str] = []

        def visit(dependency: ModuleDependency, required: bool) -> None:
            identity = dependency.module_id
            if identity in visiting:
                cycle = " -> ".join((*visiting, identity))
                raise DependencyResolutionError(f"dependency cycle: {cycle}")
            try:
                module = self._registry.resolve(identity, dependency.version_constraint)
            except KeyError as exc:
                if required:
                    raise DependencyResolutionError(str(exc)) from exc
                warnings.append(f"optional_dependency_omitted:{identity}")
                return
            existing = selected.get(identity)
            if existing and existing.version != module.version:
                raise DependencyResolutionError(
                    f"incompatible constraints for {identity}: "
                    f"{existing.version} and {dependency.version_constraint}"
                )
            if existing:
                if required:
                    required_ids.add(identity)
                    optional_ids.discard(identity)
                return
            visiting.append(identity)
            selected[identity] = module
            graph.setdefault(identity, set())
            if required:
                required_ids.add(identity)
            else:
                optional_ids.add(identity)
            trace.append(f"resolved:{identity}@{module.version}")
            if module.lifecycle_status == "deprecated":
                replacement = (
                    f":replacement={module.replacement_module}"
                    if module.replacement_module
                    else ""
                )
                warnings.append(f"deprecated_module:{identity}@{module.version}{replacement}")
            for child in sorted(
                module.required_dependencies,
                key=lambda item: (item.module_id, item.version_constraint),
            ):
                graph[identity].add(child.module_id)
                visit(child, True)
            for child in sorted(
                module.optional_dependencies,
                key=lambda item: (item.module_id, item.version_constraint),
            ):
                if child.module_id in include_optional:
                    graph[identity].add(child.module_id)
                    visit(child, False)
            visiting.pop()

        for dependency in sorted(
            model.required_modules,
            key=lambda item: (item.module_id, item.version_constraint),
        ):
            visit(dependency, True)
        for dependency in sorted(
            model.optional_modules,
            key=lambda item: (item.module_id, item.version_constraint),
        ):
            if dependency.module_id in include_optional:
                visit(dependency, False)
            elif model.allow_degraded_composition:
                warnings.append(f"optional_dependency_omitted:{dependency.module_id}")

        for module_id, module in selected.items():
            for conflict in module.declared_conflicts:
                if conflict in selected:
                    raise DependencyResolutionError(
                        f"declared module conflict: {module_id} conflicts with {conflict}"
                    )

        providers: dict[str, list[KnowledgeModule]] = {}
        for module in selected.values():
            keys = module.provided_knowledge_keys or tuple(module.facts)
            for key in keys:
                providers.setdefault(key, []).append(module)
        for key, modules in providers.items():
            if len(modules) < 2:
                continue
            priorities = [module.precedence for module in modules]
            if len(set(priorities)) != len(priorities):
                names = ", ".join(sorted(module.module_id for module in modules))
                raise DependencyResolutionError(f"ambiguous providers for {key}: {names}")

        ordered: list[str] = []
        temporary: set[str] = set()
        permanent: set[str] = set()

        def topo(module_id: str) -> None:
            if module_id in permanent:
                return
            if module_id in temporary:
                raise DependencyResolutionError(f"dependency cycle: {module_id}")
            temporary.add(module_id)
            for child in sorted(graph.get(module_id, ())):
                topo(child)
            temporary.remove(module_id)
            permanent.add(module_id)
            ordered.append(module_id)

        for module_id in sorted(selected):
            topo(module_id)
        graph_tuple = tuple(
            (module_id, tuple(sorted(dependencies)))
            for module_id, dependencies in sorted(graph.items())
        )
        context = tuple(
            sorted({key for module in selected.values() for key in module.required_context})
        )
        payload = {
            "model": f"{model.model_id}@{model.version}",
            "modules": [(item, selected[item].version) for item in ordered],
            "graph": graph_tuple,
            "warnings": sorted(warnings),
            "context": context,
        }
        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        return ResolutionResult(
            required_modules=tuple(selected[item] for item in ordered if item in required_ids),
            optional_modules=tuple(selected[item] for item in ordered if item in optional_ids),
            dependency_graph=graph_tuple,
            composition_order=tuple(ordered),
            warnings=tuple(sorted(warnings)),
            trace=tuple(trace),
            required_context=context,
            digest=digest,
        )
