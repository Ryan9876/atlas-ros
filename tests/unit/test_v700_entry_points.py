from __future__ import annotations

import json
import subprocess
import sys

import pytest

from atlas_ros.entry_points.main import RuntimeCommandError, initialize, main, status, verify


def test_status_is_lightweight_and_reports_no_writes(capsys: pytest.CaptureFixture[str]) -> None:
    status(json_output=True)
    payload = json.loads(capsys.readouterr().out)

    assert payload == {
        "authority_model_version": "7.0",
        "production_authority_loaded": False,
        "production_authority_state": "not_loaded",
        "provider_writes": 0,
        "runtime_identity": "installed_package",
        "status": "installed_runtime_available",
        "version": "8.3.0",
    }
    assert "active_production_version" not in payload


def test_initialize_fails_closed_without_authority_readers(
    capsys: pytest.CaptureFixture[str],
) -> None:
    initialize(json_output=True)
    payload = json.loads(capsys.readouterr().out)

    assert payload["status"] == "initialization_blocked"
    assert payload["production_authority_loaded"] is False
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
        "production_authority_loaded": False,
        "scope": "installed_runtime_identity",
        "valid": True,
        "version": "8.3.0",
        "writes": False,
    }


@pytest.mark.parametrize("flag", ["--help", "-h"])
def test_root_help_exits_successfully(
    flag: str,
    capsys: pytest.CaptureFixture[str],
) -> None:
    main([flag])
    output = capsys.readouterr().out
    assert "usage: atlas" in output
    assert "status" in output


def test_no_arguments_prints_help_and_preserves_exit_behavior(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as error:
        main([])
    assert error.value.code == 2
    assert "usage: atlas" in capsys.readouterr().out


def test_unknown_command_remains_error(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as error:
        main(["unknown"])
    assert error.value.code == 2
    assert "unknown command" in capsys.readouterr().err


def test_execute_is_fail_closed_without_authorized_adapter() -> None:
    with pytest.raises(RuntimeCommandError, match="immutable authorized plan"):
        main(["execute"])


def test_status_import_does_not_load_provider_intelligence_or_release_modules() -> None:
    program = """
import sys
from atlas_ros.entry_points.main import main
main(['status', '--json'])
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
