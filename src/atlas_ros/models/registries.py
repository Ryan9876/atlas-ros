from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping


@dataclass(frozen=True)
class KnowledgeModule:
    module_id: str
    facts: Mapping[str, Any] = field(default_factory=dict)
    required_context: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.module_id.strip():
            raise ValueError("knowledge module id is required")
        object.__setattr__(self, "facts", MappingProxyType(dict(self.facts)))


@dataclass(frozen=True)
class PlanningModel:
    model_id: str
    responsibility_template: str
    outcome_template: str
    default_owner: str = ""
    default_workstream: str = ""

    def __post_init__(self) -> None:
        if not self.model_id.strip():
            raise ValueError("planning model id is required")
        if not self.responsibility_template.strip() or not self.outcome_template.strip():
            raise ValueError("planning model templates are required")


class KnowledgeModuleRegistry:
    def __init__(self, modules: tuple[KnowledgeModule, ...] = ()) -> None:
        self._modules: dict[str, KnowledgeModule] = {}
        for module in modules:
            self.register(module)

    def register(self, module: KnowledgeModule) -> None:
        if module.module_id in self._modules:
            raise ValueError(f"duplicate knowledge module: {module.module_id}")
        self._modules[module.module_id] = module

    def get(self, module_id: str) -> KnowledgeModule:
        try:
            return self._modules[module_id]
        except KeyError as exc:
            raise KeyError(f"unknown knowledge module: {module_id}") from exc


class PlanningModelRegistry:
    def __init__(self, models: tuple[PlanningModel, ...] = ()) -> None:
        self._models: dict[str, PlanningModel] = {}
        for model in models:
            self.register(model)

    def register(self, model: PlanningModel) -> None:
        if model.model_id in self._models:
            raise ValueError(f"duplicate planning model: {model.model_id}")
        self._models[model.model_id] = model

    def get(self, model_id: str) -> PlanningModel:
        try:
            return self._models[model_id]
        except KeyError as exc:
            raise KeyError(f"unknown planning model: {model_id}") from exc
