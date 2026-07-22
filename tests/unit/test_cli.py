from __future__ import annotations

import sys
from pathlib import Path

import pytest

from atlas_ros import cli


def run_cli(monkeypatch: pytest.MonkeyPatch, *arguments: str) -> None:
    monkeypatch.setattr(sys, "argv", ["atlas", *arguments])
    cli.main()


def test_status_and_initialize(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    run_cli(monkeypatch, "status")
    assert "production-capable" in capsys.readouterr().out
    run_cli(monkeypatch, "initialize", "--json")
    assert '"writes": false' in capsys.readouterr().out


def test_capture_and_decompose(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    monkeypatch.setenv("ATLAS_RUNTIME_DIR", str(tmp_path))
    run_cli(monkeypatch, "capture", "harmless acceptance fixture", "--source", "test")
    assert "capture_id" in capsys.readouterr().out
    run_cli(
        monkeypatch,
        "decompose",
        "a1",
        "Investigate",
        "--owner",
        "Ryan",
        "--definition-of-done",
        "Evidence recorded",
        "--execution-ready",
        "--delegated-work",
    )
    assert '"status":"ready"' in capsys.readouterr().out


def test_release_cli_round_trip(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    (tmp_path / "artifact.txt").write_text("fixture", encoding="utf-8")
    checksum_file = tmp_path / "checksums.sha256"
    run_cli(monkeypatch, "release", "inventory", "--root", str(tmp_path))
    assert "artifact.txt" in capsys.readouterr().out
    run_cli(
        monkeypatch,
        "release",
        "checksums",
        "--root",
        str(tmp_path),
        "--checksum-file",
        str(checksum_file),
    )
    assert checksum_file.exists()
    capsys.readouterr()
    run_cli(
        monkeypatch,
        "release",
        "verify",
        "--root",
        str(tmp_path),
        "--checksum-file",
        str(checksum_file),
    )
    assert '"valid":true' in capsys.readouterr().out


def test_todoist_apply_stays_denied() -> None:
    with pytest.raises(PermissionError, match="not exposed"):
        cli.todoist_apply()


def test_todoist_reconcile_dry_run_and_apply(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    class Adapter:
        @classmethod
        def from_environment(cls):
            return cls()

        @classmethod
        def from_keychain(cls, _account: str):
            return cls()

    class Mutation:
        mutation_type = type("T", (), {"value": "action_update"})()
        notion_page_id = "page"
        todoist_task_id = "task"
        summary = "sync"
        properties = {"Status": "Completed"}

    class Plan:
        generated_at = __import__("datetime").datetime.now(__import__("datetime").UTC)
        mutations = (Mutation(),)
        ignored = ()
        conflicts = ()

    class Result:
        planned = 1
        applied = 1
        conflicts = 0
        ignored = 0
        verified = 1

        @property
        def __dict__(self):
            return {
                "planned": self.planned,
                "applied": self.applied,
                "conflicts": self.conflicts,
                "ignored": self.ignored,
                "verified": self.verified,
            }

    class Service:
        def __init__(self, *_args, **_kwargs):
            pass

        def plan(self, **_kwargs):
            return Plan()

        def apply(self, _plan, confirmed: bool = False):
            assert confirmed
            return Result()

    monkeypatch.setattr(cli, "LiveNotionAdapter", Adapter)
    monkeypatch.setattr(cli, "LiveTodoistAdapter", Adapter)
    monkeypatch.setattr(cli, "TodoistReconciliationService", Service)
    monkeypatch.setenv("ATLAS_ACTION_DATA_SOURCE_ID", "actions")
    monkeypatch.setenv("ATLAS_RUNTIME_DIR", str(tmp_path))
    cli.todoist_reconcile(apply=False, full=True, task_id="", keychain=False)
    assert '"mode": "dry-run"' in capsys.readouterr().out
    cli.todoist_reconcile(apply=True, full=False, task_id="task", keychain=True)
    assert '"applied": 1' in capsys.readouterr().out


def test_todoist_reconcile_requires_action_source(monkeypatch: pytest.MonkeyPatch) -> None:
    class Adapter:
        @classmethod
        def from_environment(cls):
            return cls()

    monkeypatch.setattr(cli, "LiveNotionAdapter", Adapter)
    monkeypatch.setattr(cli, "LiveTodoistAdapter", Adapter)
    monkeypatch.delenv("ATLAS_ACTION_DATA_SOURCE_ID", raising=False)
    with pytest.raises(ValueError, match="ATLAS_ACTION_DATA_SOURCE_ID"):
        cli.todoist_reconcile(apply=False, full=False, task_id="", keychain=False)
