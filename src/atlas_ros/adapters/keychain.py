from __future__ import annotations

import subprocess
from collections.abc import Callable

from atlas_ros.adapters.errors import AdapterConfigurationError

CommandRunner = Callable[[list[str]], str]


def _run_security(command: list[str]) -> str:
    result = subprocess.run(command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise AdapterConfigurationError("keychain", "read", "credential was not available")
    return result.stdout.strip()


class MacOSKeychain:
    """Reads a narrowly scoped Atlas secret without logging or persisting it."""

    def __init__(self, account: str, runner: CommandRunner = _run_security) -> None:
        self.account = account
        self.runner = runner

    def read(self, service: str) -> str:
        secret = self.runner(
            ["security", "find-generic-password", "-a", self.account, "-s", service, "-w"]
        ).strip()
        if not secret:
            raise AdapterConfigurationError("keychain", "read", "credential was empty")
        return secret
