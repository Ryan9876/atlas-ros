from __future__ import annotations

import json
from importlib.resources import files
from typing import Any, cast

from atlas_ros.contracts.domain_v62 import (
    DomainKnowledgeContextV62,
    DomainKnowledgePackV62,
    DomainKnowledgeSelectionV62,
)
from atlas_ros.contracts.models import deterministic_digest
from atlas_ros.contracts.v62 import CanonicalIntent, EvidenceReference, MemoryApprovalState


class DomainKnowledgeRegistryV62:
    """Replaceable, versioned domain packs with no provider or execution authority."""

    def __init__(self, packs: tuple[DomainKnowledgePackV62, ...] | None = None) -> None:
        self._packs = packs or self._load_default()
        if not self._packs:
            raise ValueError("domain knowledge registry cannot be empty")

    def select(self, canonical: CanonicalIntent) -> DomainKnowledgeContextV62:
        pack = next(
            (item for item in self._packs if item.domain == canonical.domain),
            next(item for item in self._packs if item.domain == "general"),
        )
        exact = pack.domain == canonical.domain
        confidence = 0.98 if exact and canonical.domain != "general" else 0.78
        missing = ()
        technical_intents = {
            "controlled-technology-pilot",
            "automation-proof-of-concept",
            "infrastructure-modernization",
            "migration",
            "decommission",
        }
        if canonical.domain == "general" and canonical.intent_type in technical_intents:
            confidence = 0.65
            missing = ("authoritative technical domain or platform",)
        evidence = (
            EvidenceReference(
                source="domain_packs_v1",
                detail=f"Selected {pack.pack_id}@{pack.version} for {canonical.domain}.",
            ),
        )
        selection_values: dict[str, Any] = {
            "contract_version": 1,
            "requested_domain": canonical.domain,
            "selected_pack_id": pack.pack_id,
            "selected_pack_version": pack.version,
            "confidence": confidence,
            "sufficient": confidence >= 0.75 and not missing,
            "missing_requirements": missing,
            "evidence": [item.model_dump(mode="json") for item in evidence],
        }
        selection = DomainKnowledgeSelectionV62(
            requested_domain=canonical.domain,
            selected_pack_id=pack.pack_id,
            selected_pack_version=pack.version,
            confidence=confidence,
            sufficient=confidence >= 0.75 and not missing,
            missing_requirements=missing,
            evidence=evidence,
            selection_digest=deterministic_digest(selection_values),
        )
        facts = {
            f"fact_{index}": fact for index, fact in enumerate(pack.planning_facts, start=1)
        }
        context_values: dict[str, Any] = {
            "selection": selection.model_dump(mode="json"),
            "facts": facts,
            "terminology": pack.terminology,
        }
        return DomainKnowledgeContextV62(
            selection=selection,
            facts=facts,
            terminology=pack.terminology,
            context_digest=deterministic_digest(context_values),
        )

    @staticmethod
    def _load_default() -> tuple[DomainKnowledgePackV62, ...]:
        resource = files("atlas_ros.data").joinpath("domain_packs_v1.json")
        raw = cast(dict[str, Any], json.loads(resource.read_text(encoding="utf-8")))
        records = cast(list[dict[str, Any]], raw["packs"])
        result: list[DomainKnowledgePackV62] = []
        for record in records:
            provenance = (
                EvidenceReference(
                    source="domain_packs_v1",
                    detail="Governed provider-free domain-pack registry.",
                ),
            )
            values: dict[str, Any] = {
                "contract_version": 1,
                "pack_id": str(record["pack_id"]),
                "version": str(record["version"]),
                "domain": str(record["domain"]),
                "description": str(record["description"]),
                "terminology": tuple(cast(list[str], record["terminology"])),
                "planning_facts": tuple(cast(list[str], record["planning_facts"])),
                "provider_free": True,
                "execution_authority": False,
                "approval_state": MemoryApprovalState.APPROVED.value,
                "provenance": [item.model_dump(mode="json") for item in provenance],
            }
            result.append(
                DomainKnowledgePackV62(
                    pack_id=str(record["pack_id"]),
                    version=str(record["version"]),
                    domain=str(record["domain"]),
                    description=str(record["description"]),
                    terminology=tuple(cast(list[str], record["terminology"])),
                    planning_facts=tuple(cast(list[str], record["planning_facts"])),
                    provenance=provenance,
                    pack_digest=deterministic_digest(values),
                )
            )
        return tuple(result)
