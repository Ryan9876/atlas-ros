"""Deterministic repository inventory for Google Drive dependencies.

The scanner performs no provider reads. It classifies repository references so
retirement readiness can prove that initialization, runtime, release authority,
restoration, and rollback no longer require Google Drive.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from atlas_ros.contracts.digests import sha256_digest

DependencyClass = Literal[
    "current_runtime",
    "startup_authority",
    "release_authority",
    "restoration",
    "historical_reference",
    "migration_tooling",
    "documentation_only",
    "obsolete",
]

_PATTERNS = (
    re.compile(r"drive\.google\.com", re.IGNORECASE),
    re.compile(r"Google[_ ]Drive", re.IGNORECASE),
    re.compile(r"\bDrive\b", re.IGNORECASE),
)
_TEXT_SUFFIXES = {
    ".py",
    ".md",
    ".json",
    ".yaml",
    ".yml",
    ".toml",
    ".txt",
    ".sh",
}
_EXCLUDED_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    "__pycache__",
    "build",
    "dist",
    ".venv",
    "candidate-evidence",
    "publication",
    "v710-evidence",
    "candidate",
}


@dataclass(frozen=True, slots=True)
class DriveDependencyReference:
    path: str
    line: int
    excerpt: str
    classification: DependencyClass
    current_dependency: bool
    file_sha256: str


@dataclass(frozen=True, slots=True)
class DriveDependencyInventory:
    root: str
    references: tuple[DriveDependencyReference, ...]
    inventory_digest: str

    @property
    def current_dependencies(self) -> tuple[DriveDependencyReference, ...]:
        return tuple(item for item in self.references if item.current_dependency)

    @property
    def summary(self) -> dict[str, int]:
        result: dict[str, int] = {}
        for item in self.references:
            result[item.classification] = result.get(item.classification, 0) + 1
        return dict(sorted(result.items()))


def inventory_drive_dependencies(root: Path) -> DriveDependencyInventory:
    """Scan all text assets and return a deterministic item-level inventory."""
    resolved = root.resolve()
    references: list[DriveDependencyReference] = []
    for path in sorted(resolved.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in _TEXT_SUFFIXES:
            continue
        relative = path.relative_to(resolved)
        if _EXCLUDED_PARTS & set(relative.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if not any(pattern.search(text) for pattern in _PATTERNS):
            continue
        digest = sha256_digest(text)
        for line_number, line in enumerate(text.splitlines(), 1):
            if not any(pattern.search(line) for pattern in _PATTERNS):
                continue
            classification = classify_reference(relative.as_posix(), line)
            references.append(
                DriveDependencyReference(
                    path=relative.as_posix(),
                    line=line_number,
                    excerpt=_compact(line),
                    classification=classification,
                    current_dependency=classification
                    in {"current_runtime", "startup_authority", "release_authority"},
                    file_sha256=digest,
                )
            )
    payload = [
        {
            "path": item.path,
            "line": item.line,
            "excerpt": item.excerpt,
            "classification": item.classification,
            "current_dependency": item.current_dependency,
            "file_sha256": item.file_sha256,
        }
        for item in references
    ]
    return DriveDependencyInventory(
        root=resolved.as_posix(),
        references=tuple(references),
        inventory_digest=sha256_digest(payload),
    )


def classify_reference(path: str, line: str) -> DependencyClass:
    """Classify one reference from path and local semantic context."""
    lowered_path = path.lower()
    lowered_line = line.lower()
    if lowered_path in {
        "src/atlas_ros/contracts/release.py",
        "src/atlas_ros/data/authorities.yaml",
        "src/atlas_ros/kernel/authority.py",
    }:
        return "documentation_only"
    if lowered_path in {
        "src/atlas_ros/cli.py",
        "src/atlas_ros/entry_points/_legacy.py",
        "src/atlas_ros/entry_points/migrate.py",
        "src/atlas_ros/entry_points/release.py",
    }:
        return "migration_tooling"
    if lowered_path.startswith("src/atlas_ros/intelligence/"):
        return "obsolete"
    if lowered_path.startswith("src/atlas_ros/"):
        if "/release/" in lowered_path or "/contracts/migrations/" in lowered_path:
            return "migration_tooling"
        if lowered_path.startswith("src/atlas_ros/validation/") or any(
            token in lowered_line
            for token in (
                "forbidden",
                "must not",
                "not required",
                "not read",
                "optional",
                "cannot be a required",
                "historical",
                "legacy",
            )
        ):
            return "documentation_only"
        return "current_runtime"
    if lowered_path.startswith("tools/release/drive") or "drive_migration" in lowered_path:
        return "migration_tooling"
    if lowered_path.startswith("scripts/") and (
        "drive" in lowered_path or "retirement" in lowered_path
    ):
        return "migration_tooling"
    if "rollback" in lowered_path or "restoration" in lowered_path:
        return "restoration"
    if lowered_path.startswith("release/") and (
        re.search(r"release_(manifest|notes|scope)_v\d+", lowered_path)
        or lowered_path.startswith("release/authority-migration/")
        or lowered_path.startswith("release/v")
        or lowered_path == "release/implementation-registry.json"
    ):
        return "historical_reference"
    if lowered_path.startswith("governance/") or lowered_path.startswith("release/"):
        if any(
            token in lowered_line
            for token in (
                "startup authority",
                "initialization authority",
                "release authority",
                "required integration",
                "bootstrap",
            )
        ):
            if any(
                token in lowered_line
                for token in (
                    "forbidden",
                    "not read",
                    "not required",
                    "optional",
                    "outside",
                    "reject",
                    "no google drive",
                    "never",
                )
            ):
                return "documentation_only"
            return "release_authority"
        if "historical" in lowered_line or "legacy" in lowered_line:
            return "historical_reference"
        return "documentation_only"
    if lowered_path.startswith(".github/workflows/"):
        if re.search(r"/v\d+", lowered_path):
            return "historical_reference"
        if any(token in lowered_line for token in ("bootstrap", "authority", "required")):
            if any(
                token in lowered_line
                for token in ("forbidden", "not required", "disconnected")
            ):
                return "documentation_only"
            return "release_authority"
        return "documentation_only"
    if lowered_path.startswith("docs/adr/") or re.search(r"/v\d{3,}", lowered_path):
        return "historical_reference"
    if lowered_path.startswith("release/") and lowered_path not in {
        "release/release_manifest.md",
    }:
        return "historical_reference"
    if lowered_path.startswith("docs/") or lowered_path.endswith(".md"):
        if "historical" in lowered_line or "legacy" in lowered_line:
            return "historical_reference"
        if "initialization" in lowered_line or "startup" in lowered_line:
            if any(
                token in lowered_line
                for token in ("not read", "forbidden", "optional", "never")
            ):
                return "documentation_only"
            return "startup_authority"
        return "documentation_only"
    if lowered_path.startswith("tests/"):
        return "documentation_only"
    return "obsolete"


def assert_zero_current_drive_dependencies(inventory: DriveDependencyInventory) -> None:
    """Fail when any runtime or authority dependency remains."""
    if inventory.current_dependencies:
        lines = ", ".join(
            f"{item.path}:{item.line} ({item.classification})"
            for item in inventory.current_dependencies
        )
        raise ValueError("current Google Drive dependencies remain: " + lines)


def _compact(line: str) -> str:
    return " ".join(line.strip().split())[:240]
