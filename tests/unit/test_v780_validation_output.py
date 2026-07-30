from __future__ import annotations

import subprocess

import pytest

from atlas_ros.devtools_cli.validation import validate


def completed(returncode: int, *, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(("check",), returncode, stdout=stdout, stderr=stderr)


@pytest.mark.parametrize(
    ("stdout", "stderr"),
    [
        ("stdout failure\n", ""),
        ("", "stderr failure\n"),
        ("stdout failure\n", "stderr failure\n"),
    ],
)
def test_failed_validation_replays_streams_separately(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    stdout: str,
    stderr: str,
) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: completed(1, stdout=stdout, stderr=stderr),
    )

    receipt = validate("edit", execute=True)
    captured = capsys.readouterr()

    assert captured.out == stdout
    assert "validation failed: ruff check ." in captured.err
    assert captured.err.endswith(stderr) if stderr else True
    assert receipt.checks_failed == ("ruff check .",)
    assert receipt.checks_passed == ()


def test_successful_validation_remains_quiet(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: completed(0, stdout="captured success\n", stderr="warning\n"),
    )

    receipt = validate("edit", execute=True)
    captured = capsys.readouterr()

    assert captured.out == ""
    assert captured.err == ""
    assert receipt.checks_failed == ()
    assert receipt.checks_passed == ("ruff check .", "pytest -q tests/unit")
