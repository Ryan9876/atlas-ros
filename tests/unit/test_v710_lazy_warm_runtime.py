from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from atlas_ros.runtime.lazy import LazyCommandRegistry, LazyCommandTarget, profile_dispatch
from atlas_ros.runtime.warm import WarmRuntimeCache, WarmRuntimeConfig, WarmRuntimeError


def test_lazy_target_imports_only_after_command_resolution(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    package = tmp_path / "lazy_fixture"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "command.py").write_text(
        "def run(arguments):\n    assert list(arguments) == ['ok']\n",
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    registry = LazyCommandRegistry(
        lazy={
            "fixture": LazyCommandTarget(
                module="lazy_fixture.command",
                attribute="run",
                capability_group="test",
            )
        }
    )

    assert "lazy_fixture.command" not in sys.modules
    profile = profile_dispatch(registry, "fixture", ("ok",), namespace_prefix="lazy_fixture")
    assert profile.imported_modules == ("lazy_fixture", "lazy_fixture.command")


def test_status_command_does_not_load_provider_release_or_migration_modules() -> None:
    program = """
import json
import sys
from atlas_ros.entry_points.main import main
main(['status', '--json'])
payload = json.loads(sys.stdout.getvalue()) if False else None
for prefix in (
    'atlas_ros.adapters',
    'atlas_ros.contracts.migrations',
    'atlas_ros.intelligence',
    'atlas_ros.release',
    'tools.release',
):
    assert not any(name == prefix or name.startswith(prefix + '.') for name in sys.modules), prefix
"""
    result = subprocess.run(
        [sys.executable, "-c", program],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["version"] == "7.8.0"
    assert payload["production_authority_loaded"] is False
    assert payload["production_authority_state"] == "not_loaded"
    assert "active_production_version" not in payload


def config(tmp_path: Path, token: str = "fixture-token") -> WarmRuntimeConfig:
    return WarmRuntimeConfig(
        root=tmp_path / "warm",
        auth_token_sha256=hashlib.sha256(token.encode()).hexdigest(),
        ttl_seconds=60,
        max_entries=2,
    )


def test_warm_runtime_is_authenticated_non_authoritative_and_fresh(tmp_path: Path) -> None:
    cache = WarmRuntimeCache(config(tmp_path))
    payload = {"capabilities": ["capture", "planning"]}
    snapshot = cache.put(
        key="capabilities",
        kind="capability_metadata",
        payload=payload,
        source_digest="a" * 64,
        auth_token="fixture-token",
        verified_at_epoch=100.0,
    )

    loaded = cache.get(
        key="capabilities",
        auth_token="fixture-token",
        expected_source_digest="a" * 64,
        now_epoch=120.0,
    )
    assert loaded.payload == payload
    assert loaded.payload_digest == snapshot.payload_digest

    with pytest.raises(WarmRuntimeError, match="authentication"):
        cache.get(key="capabilities", auth_token="incorrect-token", expected_source_digest="a" * 64, now_epoch=120.0)
    with pytest.raises(WarmRuntimeError, match="expired"):
        cache.get(key="capabilities", auth_token="fixture-token", expected_source_digest="a" * 64, now_epoch=200.0)
    with pytest.raises(WarmRuntimeError, match="stale"):
        cache.get(key="capabilities", auth_token="fixture-token", expected_source_digest="b" * 64, now_epoch=120.0)
    assert cache.clear(auth_token="fixture-token") == 1
