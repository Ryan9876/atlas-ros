from __future__ import annotations

import pytest

from atlas_ros.adapters.errors import AdapterConfigurationError
from atlas_ros.adapters.keychain import MacOSKeychain


def test_reads_named_secret_without_persisting_it() -> None:
    commands: list[list[str]] = []

    def runner(command: list[str]) -> str:
        commands.append(command)
        return "secret-value\n"

    assert MacOSKeychain("ryan", runner).read("atlas-ros-notion-token") == "secret-value"
    assert commands == [
        ["security", "find-generic-password", "-a", "ryan", "-s", "atlas-ros-notion-token", "-w"]
    ]


def test_rejects_empty_secret() -> None:
    with pytest.raises(AdapterConfigurationError):
        MacOSKeychain("ryan", lambda _: "").read("atlas-ros-todoist-token")
