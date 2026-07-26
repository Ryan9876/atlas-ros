from __future__ import annotations

from collections.abc import Callable
from typing import Any, Literal
from uuid import UUID

from atlas_ros.contracts import (
    KnowledgePackage,
    KnowledgePackageV2,
    ManagementActionV1,
    ManagementPackage,
    ManagementPackageV2,
    ManagementPackageV3,
    ManagementSection,
    ReasoningPackage,
    ReasoningPackageV2,
    ReasoningPackageV3,
    ReasoningPackageV4,
    SemanticRole,
    ValidationResult,
    deterministic_digest,
)
from atlas_ros.models import PlanningModelRegistry

EventSink = Callable[[str, dict[str, str]], None]


class ManagementStructureEngine:
    """Builds provider-independent management artifacts from governed packages."""

    def __init__(
        self,
        registry: PlanningModelRegistry,
        event_sink: EventSink | None = None,
    ) -> None:
        self._registry = registry
        self._event_sink = event_sink

    def structure(
        self,
        reasoning: ReasoningPackage | ReasoningPackageV2,
        knowledge: KnowledgePackage,
        model_id: str,
        *,
        owner: str | None = None,
        workstream: str | None = None,
    ) -> ManagementPackage:
        """Preserve deterministic v1 template behavior."""
        if reasoning.correlation_id != knowledge.correlation_id:
            raise ValueError("reasoning and knowledge correlation ids must match")
        model = self._registry.get(model_id)
        values = {"classification": reasoning.classification, **knowledge.facts}
        try:
            responsibility = model.responsibility_template.format_map(values)
            outcome = model.outcome_template.format_map(values)
        except KeyError as exc:
            raise ValueError(f"missing planning-model value: {exc.args[0]}") from exc
        return ManagementPackage(
            correlation_id=reasoning.correlation_id,
            source_component="engines.management_structure",
            responsibility=responsibility,
            desired_outcome=outcome,
            owner=model.default_owner if owner is None else owner,
            workstream=model.default_workstream if workstream is None else workstream,
            decision_points=list(knowledge.unresolved_questions),
        )

    def structure_v2(
        self,
        reasoning: ReasoningPackageV3,
        knowledge: KnowledgePackageV2,
        *,
        owner: str | None = None,
        workstream: str | None = None,
    ) -> ManagementPackageV2:
        self._validate_correlations(reasoning.correlation_id, knowledge)
        if not knowledge.verify_digest():
            raise ValueError("Knowledge Package V2 digest verification failed")
        model = self._registry.get(
            knowledge.selected_planning_model_id,
            knowledge.selected_planning_model_version,
        )
        if knowledge.contract_version not in model.supported_knowledge_package_versions:
            raise ValueError("planning model does not support this Knowledge Package version")
        sections: list[ManagementSection] = []
        unresolved: list[str] = list(knowledge.unresolved_questions)
        validations: list[ValidationResult] = []
        section_provenance: dict[str, tuple[str, ...]] = {}
        completeness: dict[str, str] = {}

        for definition in model.sections:
            source_keys = definition.contribution_keys or (f"section:{definition.section_id}",)
            content = {
                key: knowledge.composed_facts[key]
                for key in source_keys
                if key in knowledge.composed_facts
            }
            section_unresolved: list[str] = []
            for dependency in definition.dependencies:
                if completeness.get(dependency) != "complete":
                    section_unresolved.append(f"section_dependency:{dependency}")
            if definition.required and not content:
                section_unresolved.append(f"missing_section_content:{definition.section_id}")
            state: Literal["complete", "incomplete", "decision_required"] = "complete"
            if section_unresolved:
                state = "decision_required" if definition.required else "incomplete"
                unresolved.extend(section_unresolved)
            provenance = tuple(
                dict.fromkeys(
                    source
                    for key in source_keys
                    for source in knowledge.value_provenance.get(key, ())
                )
            )
            section_provenance[definition.section_id] = provenance
            completeness[definition.section_id] = state
            sections.append(
                ManagementSection(
                    section_id=definition.section_id,
                    title=definition.title,
                    content=content,
                    provenance=provenance,
                    completeness=state,
                    unresolved_items=tuple(section_unresolved),
                )
            )
            validations.append(
                ValidationResult(
                    rule=f"required section {definition.section_id}",
                    passed=state == "complete" or not definition.required,
                    detail=", ".join(section_unresolved),
                )
            )

        accountable_owner = (model.default_owner if owner is None else owner) or str(
            reasoning.known_inputs.get("owner", "")
        )
        if not accountable_owner and "accountable_owner_required" in model.validation_rules:
            unresolved.append("missing_accountable_owner")
            validations.append(
                ValidationResult(
                    rule="accountable_owner_required",
                    passed=False,
                    detail="No accountable owner was supplied.",
                )
            )
        lifecycle = "structurally_complete"
        if unresolved:
            lifecycle = "decision_required"
        elif any(section.completeness != "complete" for section in sections):
            lifecycle = "incomplete"
        desired_outcome = str(
            reasoning.known_inputs.get("desired_outcome", reasoning.normalized_intent)
        )
        responsibility = str(
            reasoning.known_inputs.get("responsibility", reasoning.normalized_intent)
        )
        package_arguments: dict[str, Any] = {
            "correlation_id": reasoning.correlation_id,
            "artifact_id": f"{model.artifact_type}:{reasoning.correlation_id}:{model.version}",
            "artifact_type": model.artifact_type,
            "planning_model_id": model.model_id,
            "planning_model_version": model.version,
            "source_reasoning_reference": f"reasoning-package/v3/{reasoning.correlation_id}",
            "source_knowledge_reference": f"knowledge-package/v2/{knowledge.package_digest}",
            "responsibility": responsibility,
            "desired_outcome": desired_outcome,
            "owner": accountable_owner,
            "workstream": model.default_workstream if workstream is None else workstream,
            "sections": tuple(sections),
            "section_provenance": section_provenance,
            "section_completeness": completeness,
            "assumptions": knowledge.assumptions,
            "unresolved_items": tuple(dict.fromkeys(unresolved)),
            "decision_points": tuple(dict.fromkeys(unresolved)),
            "governance_requirements": tuple(
                dict.fromkeys((*model.governance_rules, *knowledge.governance_overlays))
            ),
            "required_approvals": model.required_approvals,
            "escalation_requirements": model.escalation_requirements,
            "completion_evidence_requirements": tuple(
                dict.fromkeys((*model.completion_evidence, *knowledge.evidence_overlays))
            ),
            "validation_results": tuple(validations),
            "lifecycle_status": lifecycle,
            "planning_registry_digest": self._registry.digest(),
            "module_registry_digest": knowledge.module_registry_digest,
            "configuration_digest": knowledge.configuration_digest,
        }
        unsigned = ManagementPackageV2(package_digest="0" * 64, **package_arguments)
        package = ManagementPackageV2(
            **package_arguments,
            package_digest=deterministic_digest(unsigned.digest_payload()),
        )
        if self._event_sink:
            self._event_sink(
                "management_package_constructed",
                {
                    "correlation_id": str(reasoning.correlation_id),
                    "model_id": model.model_id,
                    "model_version": model.version,
                    "status": lifecycle,
                    "registry_digest": self._registry.digest(),
                    "package_digest": package.package_digest,
                },
            )
        return package

    def structure_v3(
        self,
        reasoning: ReasoningPackageV4,
        knowledge: KnowledgePackageV2,
        *,
        owner: str | None = None,
        workstream: str | None = None,
    ) -> ManagementPackageV3:
        """Construct a semantic management package without control-plane leakage."""
        self._validate_correlations(reasoning.correlation_id, knowledge)
        if not knowledge.verify_digest():
            raise ValueError("Knowledge Package V2 digest verification failed")
        model = self._registry.get(
            knowledge.selected_planning_model_id,
            knowledge.selected_planning_model_version,
        )
        if reasoning.contract_version not in model.supported_reasoning_package_versions:
            raise ValueError("planning model does not support Reasoning Package V4")
        if 3 not in model.supported_management_package_versions:
            raise ValueError("planning model does not support Management Package V3")

        accountable_owner = (owner if owner is not None else model.default_owner) or str(
            reasoning.known_inputs.get("owner", "Ryan")
        )
        primary_done_when = str(
            knowledge.composed_facts.get(
                "primary_done_when",
                "The primary business outcome is complete and verified.",
            )
        )
        primary_reference = f"intent-partition/{reasoning.intent_partition_digest}/primary"

        def actions_from(
            key: str,
            role: SemanticRole,
            horizon: str,
            source_role: str,
            *,
            ready: bool,
        ) -> list[ManagementActionV1]:
            raw_items = knowledge.composed_facts.get(key, ())
            if not isinstance(raw_items, list | tuple):
                return []
            result: list[ManagementActionV1] = []
            for index, raw in enumerate(raw_items, 1):
                if not isinstance(raw, dict):
                    continue
                title = str(raw.get("title", "")).strip()
                if not title:
                    continue
                action_id = (
                    f"{reasoning.selected_planning_model_id}:{source_role}:{index}:"
                    f"{deterministic_digest(title)[:16]}"
                )
                result.append(
                    ManagementActionV1(
                        action_id=action_id,
                        title=title,
                        objective=str(raw.get("objective", title)).strip(),
                        done_when=str(
                            raw.get("done_when", f"{title} is complete and verified.")
                        ).strip(),
                        owner=(
                            accountable_owner
                            if role is SemanticRole.CURRENT_BUSINESS_ACTION
                            else ""
                        ),
                        semantic_role=role,
                        horizon=horizon,  # type: ignore[arg-type]
                        source_instruction_role=source_role,
                        semantic_provenance=(
                            primary_reference,
                            f"knowledge/{key}/{index}",
                        ),
                        execution_ready=ready,
                        trigger=str(raw.get("trigger", "")).strip(),
                    )
                )
            return result

        current = actions_from(
            "current_actions",
            SemanticRole.CURRENT_BUSINESS_ACTION,
            "current",
            "current_business_action",
            ready=True,
        )
        known_titles = {item.title.casefold() for item in current}
        for index, title in enumerate(reasoning.current_business_actions, len(current) + 1):
            cleaned = title.strip().rstrip(".")
            if not cleaned or cleaned.casefold() in known_titles:
                continue
            current.append(
                ManagementActionV1(
                    action_id=f"explicit-current:{index}:{deterministic_digest(cleaned)[:16]}",
                    title=cleaned,
                    objective=cleaned,
                    done_when=f"{cleaned} is complete and verified.",
                    owner=accountable_owner,
                    semantic_role=SemanticRole.CURRENT_BUSINESS_ACTION,
                    horizon="current",
                    source_instruction_role="current_business_action",
                    semantic_provenance=(primary_reference, "reasoning/current_business_actions"),
                    execution_ready=True,
                )
            )
            known_titles.add(cleaned.casefold())

        delegated = actions_from(
            "delegated_actions",
            SemanticRole.DELEGATED_ACTION,
            "next",
            "delegated_action",
            ready=False,
        )
        conditional = actions_from(
            "conditional_actions",
            SemanticRole.CONDITIONAL_ACTION,
            "conditional",
            "conditional_action",
            ready=False,
        )
        conditional.extend(
            actions_from(
                "future_actions",
                SemanticRole.CONDITIONAL_ACTION,
                "future",
                "conditional_action",
                ready=False,
            )
        )
        unresolved = tuple(
            dict.fromkeys(
                (*reasoning.intent_partition_ambiguities, *knowledge.unresolved_questions)
            )
        )
        lifecycle = (
            "decision_required"
            if reasoning.requires_human_decision or unresolved
            else "structurally_complete"
        )
        semantic_provenance = {
            "primary_outcome": (primary_reference,),
            "evaluation_context": tuple(
                f"intent-partition/{reasoning.intent_partition_digest}/evaluation/{index}"
                for index, _ in enumerate(reasoning.evaluation_context, 1)
            ),
            "audit_requirements": tuple(
                f"intent-partition/{reasoning.intent_partition_digest}/audit/{index}"
                for index, _ in enumerate(reasoning.audit_requirements, 1)
            ),
            "execution_constraints": tuple(
                f"intent-partition/{reasoning.intent_partition_digest}/constraint/{index}"
                for index, _ in enumerate(reasoning.execution_constraints, 1)
            ),
        }
        arguments: dict[str, Any] = {
            "correlation_id": reasoning.correlation_id,
            "artifact_id": f"{model.artifact_type}:{reasoning.correlation_id}:{model.version}",
            "artifact_type": model.artifact_type,
            "planning_model_id": model.model_id,
            "planning_model_version": model.version,
            "source_reasoning_reference": f"reasoning-package/v4/{reasoning.correlation_id}",
            "source_knowledge_reference": f"knowledge-package/v2/{knowledge.package_digest}",
            "responsibility": reasoning.responsibility_domain,
            "primary_outcome": reasoning.primary_business_outcome,
            "primary_outcome_done_when": primary_done_when,
            "owner": accountable_owner,
            "workstream": model.default_workstream if workstream is None else workstream,
            "execution_candidates": tuple(current),
            "delegated_outcomes": tuple(delegated),
            "conditional_outcomes": tuple(conditional),
            "evaluation_context": reasoning.evaluation_context,
            "audit_requirements": reasoning.audit_requirements,
            "execution_constraints": reasoning.execution_constraints,
            "reference_context": reasoning.reference_context,
            "semantic_provenance": semantic_provenance,
            "assumptions": knowledge.assumptions,
            "unresolved_items": unresolved,
            "lifecycle_status": lifecycle,
            "planning_registry_digest": self._registry.digest(),
            "module_registry_digest": knowledge.module_registry_digest,
            "configuration_digest": knowledge.configuration_digest,
            "intent_partition_digest": reasoning.intent_partition_digest,
        }
        unsigned = ManagementPackageV3(package_digest="0" * 64, **arguments)
        package = ManagementPackageV3(
            **arguments,
            package_digest=deterministic_digest(unsigned.digest_payload()),
        )
        if self._event_sink:
            self._event_sink(
                "semantic_management_package_constructed",
                {
                    "correlation_id": str(reasoning.correlation_id),
                    "model_id": model.model_id,
                    "status": lifecycle,
                    "package_digest": package.package_digest,
                },
            )
        return package

    @staticmethod
    def _validate_correlations(
        correlation_id: UUID,
        knowledge: KnowledgePackageV2,
    ) -> None:
        if correlation_id != knowledge.correlation_id:
            raise ValueError("reasoning and knowledge correlation ids must match")
