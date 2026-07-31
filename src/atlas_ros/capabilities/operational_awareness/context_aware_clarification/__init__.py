"""Governed package identity for context-aware clarification."""

from ..clarification_analyzer import ContextAwareClarificationAnalyzer
from ..clarification_compatibility import ClarificationCompatibilityAdapter

CAPABILITY_ID = "atlas.context-aware-clarification"

__all__ = [
    "CAPABILITY_ID",
    "ClarificationCompatibilityAdapter",
    "ContextAwareClarificationAnalyzer",
]
