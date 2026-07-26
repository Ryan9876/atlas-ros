from __future__ import annotations

import re

from atlas_ros.contracts.v62 import CanonicalIntent, stable_fingerprint

from .archetypes_v62 import CanonicalIntentEngineV62 as _BaseCanonicalIntentEngineV62


_CLOUDVISION_OUTCOME = "Launch the Arista CloudVision code-upgrade automation pilot"


class CanonicalIntentEngineV62(_BaseCanonicalIntentEngineV62):
    """Expanded canonicalizer for equivalent CloudVision pilot phrasings."""

    def canonicalize(self, raw_input: str) -> CanonicalIntent:
        normalized = re.sub(
            r"\s+",
            " ",
            raw_input.casefold().replace("cvp", "cloudvision"),
        ).strip(" .")
        cloudvision_upgrade = (
            ("cloudvision" in normalized or "cloud vision" in normalized)
            and ("upgrade" in normalized or "upgrades" in normalized or "ugrade" in normalized)
        )
        if not cloudvision_upgrade:
            return super().canonicalize(raw_input)
        qualifiers = self._material_qualifiers(normalized)
        fingerprint = stable_fingerprint(
            {
                "canonical_text": _CLOUDVISION_OUTCOME,
                "intent_type": "controlled-technology-pilot",
                "domain": "network_automation",
                "material_qualifiers": qualifiers,
            }
        )
        return CanonicalIntent(
            raw_input=raw_input,
            canonical_text=_CLOUDVISION_OUTCOME,
            intent_type="controlled-technology-pilot",
            domain="network_automation",
            normalization_steps=(
                "trimmed_whitespace",
                "normalized_case",
                "normalized_aliases",
                "mapped_cloudvision_pilot_contract",
            ),
            material_qualifiers=qualifiers,
            semantic_fingerprint=fingerprint,
        )
