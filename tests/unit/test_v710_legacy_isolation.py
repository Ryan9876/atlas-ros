from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from scripts.validate_legacy_isolation import validate


def test_repository_compatibility_paths_are_isolated() -> None:
    assert validate(
        Path("src/atlas_ros"),
        Path("governance/compatibility-paths.yaml"),
    ) == []


def test_unknown_canonical_command_never_loads_legacy_cli() -> None:
    program = """
import sys
from atlas_ros.entry_points.main import main
try:
    main(['legacy-command'])
except SystemExit:
    pass
assert 'atlas_ros.cli' not in sys.modules
assert 'atlas_ros.entry_points._legacy' not in sys.modules
"""
    result = subprocess.run(
        [sys.executable, "-c", program],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
