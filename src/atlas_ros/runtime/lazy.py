"""Verified lazy import primitives for the Atlas command surface."""

from __future__ import annotations

import importlib
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

CommandHandler = Callable[[Sequence[str]], None]


class LazyCommandError(ValueError):
    """Raised when a lazy command cannot be resolved safely."""


@dataclass(frozen=True, slots=True)
class LazyCommandTarget:
    """One command-to-callable binding resolved only after command selection."""

    module: str
    attribute: str
    capability_group: str

    def resolve(self) -> CommandHandler:
        module = importlib.import_module(self.module)
        value = getattr(module, self.attribute, None)
        if not callable(value):
            raise LazyCommandError(
                f"lazy command target is not callable: {self.module}:{self.attribute}"
            )
        return value


@dataclass(frozen=True, slots=True)
class StartupProfile:
    """Observed import footprint for one command dispatch."""

    command: str
    modules_before: int
    modules_after: int
    imported_modules: tuple[str, ...]

    @property
    def imported_count(self) -> int:
        return len(self.imported_modules)


class LazyCommandRegistry:
    """Immutable command registry with explicit eager and lazy bindings."""

    def __init__(
        self,
        *,
        eager: Mapping[str, CommandHandler] | None = None,
        lazy: Mapping[str, LazyCommandTarget] | None = None,
    ) -> None:
        eager_values = dict(eager or {})
        lazy_values = dict(lazy or {})
        overlap = set(eager_values) & set(lazy_values)
        if overlap:
            raise LazyCommandError(
                "commands cannot be both eager and lazy: " + ", ".join(sorted(overlap))
            )
        if any(not name or name.strip() != name for name in (*eager_values, *lazy_values)):
            raise LazyCommandError("command names must be non-empty canonical strings")
        self._eager = MappingProxyType(eager_values)
        self._lazy = MappingProxyType(lazy_values)

    @property
    def commands(self) -> tuple[str, ...]:
        return tuple(sorted((*self._eager, *self._lazy)))

    def resolve(self, command: str) -> CommandHandler:
        eager = self._eager.get(command)
        if eager is not None:
            return eager
        target = self._lazy.get(command)
        if target is None:
            raise LazyCommandError(f"unknown command: {command}")
        return target.resolve()

    def dispatch(self, command: str, arguments: Sequence[str]) -> None:
        self.resolve(command)(arguments)


def profile_dispatch(
    registry: LazyCommandRegistry,
    command: str,
    arguments: Sequence[str] = (),
    *,
    namespace_prefix: str = "atlas_ros",
) -> StartupProfile:
    """Run one command and report only newly imported Atlas modules."""
    before = set(sys.modules)
    registry.dispatch(command, arguments)
    after = set(sys.modules)
    imported = tuple(
        sorted(
            name
            for name in after - before
            if name == namespace_prefix or name.startswith(namespace_prefix + ".")
        )
    )
    return StartupProfile(
        command=command,
        modules_before=len(before),
        modules_after=len(after),
        imported_modules=imported,
    )


def call_without_arguments(handler: Callable[..., Any]) -> CommandHandler:
    """Adapt a no-argument callable to the command registry contract."""

    def wrapped(arguments: Sequence[str]) -> None:
        if arguments:
            raise LazyCommandError("command does not accept positional arguments")
        handler()

    return wrapped
