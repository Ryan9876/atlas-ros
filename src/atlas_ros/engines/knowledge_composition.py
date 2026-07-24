from __future__ import annotations

from typing import Any

from atlas_ros.contracts import KnowledgePackage, ReasoningPackage
from atlas_ros.models import KnowledgeModuleRegistry


class KnowledgeCompositionEngine:
    """Composes governed knowledge without creating execution artifacts."""

    def __init__(self, registry: KnowledgeModuleRegistry) -> None:
        self._registry = registry

    def compose(
        self,
        reasoning: ReasoningPackage,
        module_ids: tuple[str, ...],
        context: dict[str, Any] | None = None,
    ) -> KnowledgePackage:
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
