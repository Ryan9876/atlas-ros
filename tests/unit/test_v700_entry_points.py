from __future__ import annotations

import json
import subprocess
import sys

import pytest

from atlas_ros.entry_points.main import RuntimeCommandError, initialize, main, status, verify


def test_status_is_lightweight_and_reports_no_writes(capsys: pytest.CaptureFixture[str]) -> None:
    status(json_output=True)
    payload = json.loads(capsys.readouterr().out)

    assert payload["version"] == "7.6.1"
    assert payload["active_production_version"] == "7.6.0"
    assert payload["production_authority_changed"] is False
    assert payload["provider_writes"] is False


def test_initialize_fails_closed_without_authority_readers(
    capsys: pytest.CaptureFixture[str],
) -> None:
    initialize(json_output=True)
    payload = json.loads(capsys.readouterr().out)

    assert payload["status"] == "initialization_blocked"
    assert payload["writes"] is False
    assert payload["required"] == [
        "GitHub authority reader",
        "Notion System State reader",
        "Notion Integration Inventory reader",
        "Todoist liveness reader",
    ]


def test_runtime_verify_checks_only_installed_identity(
    capsys: pytest.CaptureFixture[str],
) -> None:
    verify(json_output=True)
    payload = json.loads(capsys.readouterr().out)

    assert payload == {
        "active_production_version": "7.6.0",
        "scope": "installed_candidate_runtime_identity",
        "valid": True,
        "version": "7.6.1",
        "writes": False,
    }


def test_execute_is_fail_closed_without_authorized_adapter() -> None:
    with pytest.raises(RuntimeCommandError, match="immutable authorized plan"):
        main(["execute"])


def test_status_import_does_not_load_provider_intelligence_or_release_modules() -> None:
    program = """
import sys
from atlas_ros.entry_points.main import status
status(json_output=True)
for prefix in ('atlas_ros.adapters', 'atlas_ros.intelligence', 'atlas_ros.release'):
    assert not any(name == prefix or name.startswith(prefix + '.') for name in sys.modules), prefix
"""
    result = subprocess.run(
        [sys.executable, "-c", program],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
