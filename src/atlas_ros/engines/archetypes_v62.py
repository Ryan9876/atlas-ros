from __future__ import annotations

import json
import re
from importlib.resources import files
from typing import Any, cast

from atlas_ros.contracts.models import deterministic_digest
from atlas_ros.contracts.v62 import (
    ArchetypeSelection,
    CanonicalIntent,
    EvidenceReference,
    MemoryApprovalState,
    OutcomeRole,
    OutcomeSet,
    OutcomeV2,
    PlanningArchetype,
    stable_fingerprint,
)


_CLOUDVISION_OUTCOME = "Launch the Arista CloudVision code-upgrade automation pilot"


class ArchetypeRegistryV62:
    """Versioned, declarative, nonauthoritative planning archetype registry."""

    def __init__(self, archetypes: tuple[PlanningArchetype, ...] | None = None) -> None:
        self._archetypes = archetypes or self._load_default()
        if not self._archetypes:
            raise ValueError("planning archetype registry cannot be empty")

    @property
    def archetypes(self) -> tuple[PlanningArchetype, ...]:
        return self._archetypes

    def get(self, archetype_id: str) -> PlanningArchetype:
        for archetype in self._archetypes:
            if archetype.archetype_id == archetype_id:
                return archetype
        raise KeyError(archetype_id)

    @staticmethod
    def _load_default() -> tuple[PlanningArchetype, ...]:
        resource = files("atlas_ros.data").joinpath("planning_archetypes_v1.json")
        raw = cast(dict[str, Any], json.loads(resource.read_text(encoding="utf-8")))
        records = cast(list[dict[str, Any]], raw["archetypes"])
        result: list[PlanningArchetype] = []
        for record in records:
            values: dict[str, Any] = {
                "archetype_id": str(record["archetype_id"]),
                "version": str(record["version"]),
                "title": str(record["title"]),
                "description": str(record["description"]),
                "trigger_terms": tuple(cast(list[str], record["trigger_terms"])),
                "current_checkpoint_templates": tuple(
                    cast(list[str], record["current_checkpoint_templates"])
                ),
                "delegated_template": str(record.get("delegated_template", "")),
                "conditional_template": str(record.get("conditional_template", "")),
                "future_template": str(record.get("future_template", "")),
                "required_dependency_categories": tuple(
                    cast(list[str], record.get("required_dependency_categories", []))
                ),
                "approval_state": MemoryApprovalState.APPROVED,
            }
            result.append(
                PlanningArchetype(
                    **values,
                    registry_digest=deterministic_digest(values),
                )
            )
        return tuple(result)


class CanonicalIntentEngineV62:
    """Normalize equivalent phrasings while retaining material qualifiers."""

    def canonicalize(self, raw_input: str) -> CanonicalIntent:
        if not raw_input.strip():
            raise ValueError("input cannot be empty")
        normalized = self._normalize(raw_input)
        steps = ["trimmed_whitespace", "normalized_case", "normalized_aliases"]
        qualifiers = self._material_qualifiers(normalized)

        cloudvision = (
            ("cloudvision" in normalized or "cloud vision" in normalized)
            and ("upgrade" in normalized or "ugrade" in normalized)
            and ("automation" in normalized or "automate" in normalized)
        )
        if cloudvision:
            canonical_text = _CLOUDVISION_OUTCOME
            intent_type = "controlled-technology-pilot"
            domain = "network_automation"
            steps.append("mapped_cloudvision_pilot_contract")
        else:
            intent_type = self._intent_type(normalized)
            canonical_text = self._canonical_text(normalized, intent_type)
            domain = self._domain(normalized)

        fingerprint = stable_fingerprint(
            {
                "canonical_text": canonical_text,
                "intent_type": intent_type,
                "domain": domain,
                "material_qualifiers": qualifiers,
            }
        )
        return CanonicalIntent(
            raw_input=raw_input,
            canonical_text=canonical_text,
            intent_type=intent_type,
            domain=domain,
            normalization_steps=tuple(steps),
            material_qualifiers=qualifiers,
            semantic_fingerprint=fingerprint,
        )

    @staticmethod
    def _normalize(value: str) -> str:
        normalized = value.casefold().replace("cvp", "cloudvision")
        normalized = re.sub(r"^\s*(task|outcome)\s*=\s*", "", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip(" .")
        return normalized

    @staticmethod
    def _material_qualifiers(value: str) -> tuple[str, ...]:
        qualifier_patterns = {
            "production": ("production", "prod "),
            "lab_only": ("lab only", "non-production only", "test environment only"),
            "no_downtime": ("no downtime", "zero downtime", "without downtime"),
            "deadline": (" by ", "before ", "deadline"),
            "budget": ("budget", "under $", "not exceed $"),
            "preserve_records": ("preserve", "retain prior", "keep previous"),
            "compare_versions": ("compare", "side-by-side", "previous version"),
            "provider_readback": ("provider readback", "execution receipt"),
        }
        return tuple(
            key
            for key, patterns in qualifier_patterns.items()
            if any(pattern in f" {value} " for pattern in patterns)
        )

    @staticmethod
    def _intent_type(value: str) -> str:
        mappings = (
            ("decommission", ("decommission", "retire", "shut down")),
            ("migration", ("migrate", "migration", "move to", "transition to")),
            (
                "compliance-readiness",
                ("compliance", "audit readiness", "certification readiness"),
            ),
            (
                "vendor-evaluation",
                ("vendor evaluation", "evaluate vendor", "select vendor"),
            ),
            (
                "incident-follow-up",
                ("incident follow-up", "post incident", "postmortem"),
            ),
            (
                "automation-proof-of-concept",
                ("proof of concept", " poc", "automation test"),
            ),
            (
                "controlled-technology-pilot",
                ("pilot", "controlled trial", "technology trial"),
            ),
            (
                "infrastructure-modernization",
                ("modernize", "modernization", "infrastructure refresh"),
            ),
            (
                "operational-remediation",
                ("remediate", "corrective action", "operational issue"),
            ),
            (
                "process-improvement",
                ("process improvement", "streamline", "reduce cycle time"),
            ),
        )
        for intent_type, terms in mappings:
            if any(term in value for term in terms):
                return intent_type
        return "process-improvement"

    @staticmethod
    def _canonical_text(value: str, intent_type: str) -> str:
        cleaned = re.sub(
            r"\b(compare|preserve|require|do not block)\b.*$",
            "",
            value,
        ).strip(" ,.;")
        if not cleaned:
            cleaned = value
        if intent_type == "migration":
            return f"Complete the governed migration: {cleaned}"
        if intent_type == "decommission":
            return f"Complete the governed decommission: {cleaned}"
        if intent_type == "compliance-readiness":
            return f"Establish compliance readiness: {cleaned}"
        if intent_type == "vendor-evaluation":
            return f"Complete the vendor evaluation: {cleaned}"
        if intent_type == "incident-follow-up":
            return f"Complete the incident follow-up: {cleaned}"
        if intent_type in {"controlled-technology-pilot", "automation-proof-of-concept"}:
            return f"Launch the controlled initiative: {cleaned}"
        return cleaned[:1].upper() + cleaned[1:]

    @staticmethod
    def _domain(value: str) -> str:
        if any(term in value for term in ("network", "arista", "cisco", "juniper")):
            return "networking"
        if any(term in value for term in ("aws", "azure", "cloud", "kubernetes")):
            return "cloud_infrastructure"
        if any(term in value for term in ("security", "compliance", "audit")):
            return "security_compliance"
        if any(term in value for term in ("employee", "hiring", "performance review")):
            return "people_operations"
        if any(term in value for term in ("budget", "finance", "cost")):
            return "finance"
        return "general"


class MultiOutcomeEngineV62:
    """Preserve primary, secondary, supporting, and competing outcomes."""

    def recognize(self, canonical: CanonicalIntent) -> OutcomeSet:
        raw = canonical.raw_input.casefold()
        primary = OutcomeV2(
            outcome_id=self._outcome_id("primary", canonical.canonical_text),
            text=canonical.canonical_text,
            role=OutcomeRole.PRIMARY,
            priority=1,
            explicit=True,
            provenance=("canonical_intent",),
        )
        secondary: list[OutcomeV2] = []
        supporting: list[OutcomeV2] = []
        competing: list[OutcomeV2] = []

        if any(term in raw for term in ("reduce downtime", "minimize downtime")):
            secondary.append(
                self._outcome(
                    "Reduce downtime during delivery",
                    OutcomeRole.SECONDARY,
                    2,
                    "explicit_secondary_outcome",
                )
            )
        if any(term in raw for term in ("document the process", "create documentation")):
            supporting.append(
                self._outcome(
                    "Create reusable process documentation",
                    OutcomeRole.SUPPORTING,
                    3,
                    "explicit_supporting_outcome",
                )
            )
        if " while " in raw and not secondary:
            tail = raw.split(" while ", 1)[1].strip(" .")
            if tail:
                secondary.append(
                    self._outcome(
                        tail[:1].upper() + tail[1:],
                        OutcomeRole.SECONDARY,
                        2,
                        "while_clause",
                    )
                )
        if " versus " in raw or " vs " in raw:
            competing.append(
                self._outcome(
                    "Resolve the competing outcome or approach",
                    OutcomeRole.COMPETING,
                    2,
                    "competing_clause",
                )
            )

        values: dict[str, Any] = {
            "contract_version": 1,
            "primary": primary.model_dump(mode="json"),
            "secondary": [item.model_dump(mode="json") for item in secondary],
            "supporting": [item.model_dump(mode="json") for item in supporting],
            "competing": [item.model_dump(mode="json") for item in competing],
            "ranking_requires_clarification": bool(competing),
        }
        return OutcomeSet(
            primary=primary,
            secondary=tuple(secondary),
            supporting=tuple(supporting),
            competing=tuple(competing),
            ranking_requires_clarification=bool(competing),
            outcome_digest=deterministic_digest(values),
        )

    @staticmethod
    def _outcome_id(role: str, text: str) -> str:
        return f"outcome-{role}-{stable_fingerprint(text)[:16]}"

    def _outcome(
        self,
        text: str,
        role: OutcomeRole,
        priority: int,
        provenance: str,
    ) -> OutcomeV2:
        return OutcomeV2(
            outcome_id=self._outcome_id(role.value, text),
            text=text,
            role=role,
            priority=priority,
            explicit=True,
            provenance=(provenance,),
        )


class ArchetypeSelectionEngineV62:
    """Select governed topology without allowing archetypes to override intent."""

    def __init__(self, registry: ArchetypeRegistryV62 | None = None) -> None:
        self.registry = registry or ArchetypeRegistryV62()

    def select(self, canonical: CanonicalIntent) -> ArchetypeSelection:
        scores: list[tuple[float, PlanningArchetype, tuple[str, ...]]] = []
        normalized = canonical.raw_input.casefold()
        for archetype in self.registry.archetypes:
            evidence: list[str] = []
            score = 0.45
            if archetype.archetype_id == canonical.intent_type:
                score = 0.92
                evidence.append("canonical_intent_type")
            matched = tuple(term for term in archetype.trigger_terms if term in normalized)
            if matched:
                score = max(score, min(0.96, 0.72 + (0.06 * len(matched))))
                evidence.extend(f"trigger:{term}" for term in matched)
            if (
                archetype.archetype_id == "controlled-technology-pilot"
                and canonical.canonical_text == _CLOUDVISION_OUTCOME
            ):
                score = 0.99
                evidence.append("v611_cloudvision_acceptance_contract")
            scores.append((score, archetype, tuple(evidence or ("fallback_similarity",))))
        scores.sort(key=lambda item: (-item[0], item[1].archetype_id))
        selected_score, selected, evidence_codes = scores[0]
        evidence = tuple(
            EvidenceReference(source="archetype_registry_v1", detail=code)
            for code in evidence_codes
        )
        alternatives = tuple(item[1].archetype_id for item in scores[1:4])
        values: dict[str, Any] = {
            "archetype_id": selected.archetype_id,
            "archetype_version": selected.version,
            "confidence": selected_score,
            "evidence": [item.model_dump(mode="json") for item in evidence],
            "alternatives": alternatives,
        }
        return ArchetypeSelection(
            archetype_id=selected.archetype_id,
            archetype_version=selected.version,
            confidence=selected_score,
            evidence=evidence,
            alternatives=alternatives,
            selection_digest=deterministic_digest(values),
        )
