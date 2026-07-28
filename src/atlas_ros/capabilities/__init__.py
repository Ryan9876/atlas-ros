"""Canonical v7 capability catalog and immutable registry surface."""

from atlas_ros.capabilities.compiler import (
    CapabilityCompilationError,
    compile_capability_registry,
)
from atlas_ros.capabilities.registry import CapabilityDescriptor, CapabilityRegistry

__all__ = [
    "CapabilityCompilationError",
    "CapabilityDescriptor",
    "CapabilityRegistry",
    "compile_capability_registry",
]
