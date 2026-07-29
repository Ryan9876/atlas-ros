"""Canonical local/CI validation planning and receipts."""

from __future__ import annotations

import json
import subprocess
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from atlas_ros.devtools_cli.impact import assess_changes

TIERS: dict[str, tuple[tuple[str, ...], ...]] = {
    "edit": (
        ("ruff", "check", "."),
        ("pytest", "-q", "tests/unit"),
    ),
    "feature": (
        ("ruff", "check", "."),
        ("mypy", "src"),
        ("pytest", "-q"),
    ),
    "branch": (
        ("ruff", "check", "."),
        ("mypy", "src"),
        ("python", "scripts/validate_architecture.py"),
        ("pytest",),
    ),
    "candidate": (
        ("ruff", "check", "."),
        ("mypy", "src"),
        ("python", "scripts/validate_architecture.py"),
        ("pytest",),
        ("python", "-m", "build"),
    ),
}


@dataclass(frozen=True)
class ValidationReceipt:
    schema_version: str
    tier: str
    mode: str
    checks_selected: tuple[str, ...]
    checks_passed: tuple[str, ...]
    checks_failed: tuple[str, ...]
    broadened: tuple[str, ...]
    cache_used: bool
    duration_seconds: float
    push_appropriate: bool
    candidate_freeze_permitted: bool
    provider_writes: int = 0


def validate(
    tier: str,
    *,
    execute: bool,
    changed_paths: tuple[str, ...] = (),
) -> ValidationReceipt:
    if tier not in TIERS:
        raise ValueError(f"unsupported validation tier: {tier}")
    impact = assess_changes(changed_paths)
    commands = TIERS[tier]
    passed: list[str] = []
    failed: list[str] = []
    started = time.monotonic()
    for command in commands:
        label = " ".join(command)
        if not execute:
            continue
        result = subprocess.run(command, check=False, text=True, capture_output=True)
        (passed if result.returncode == 0 else failed).append(label)
        if result.returncode != 0:
            break
    duration = time.monotonic() - started
    complete = execute and not failed and len(passed) == len(commands)
    return ValidationReceipt(
        schema_version="development-validation-receipt-v1",
        tier=tier,
        mode="execute" if execute else "plan",
        checks_selected=tuple(" ".join(command) for command in commands),
        checks_passed=tuple(passed),
        checks_failed=tuple(failed),
        broadened=impact.broadened_validation,
        cache_used=False,
        duration_seconds=round(duration, 3),
        push_appropriate=complete and tier in {"feature", "branch", "candidate"},
        candidate_freeze_permitted=complete and tier == "candidate",
    )


def write_receipt(receipt: ValidationReceipt, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(receipt), indent=2, sort_keys=True) + "\n")
