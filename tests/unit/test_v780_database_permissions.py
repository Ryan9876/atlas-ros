from __future__ import annotations

import os
import stat
from pathlib import Path

import pytest

from atlas_ros.runtime.database import RuntimeDatabase

pytestmark = pytest.mark.skipif(os.name != "posix", reason="POSIX mode-bit test")


def mode(path: Path) -> int:
    return stat.S_IMODE(path.stat().st_mode)


def test_runtime_database_permissions_and_missing_sidecars(tmp_path: Path) -> None:
    path = tmp_path / "runtime" / "atlas.sqlite3"
    database = RuntimeDatabase(path)

    database._secure_database_files()
    database.initialize()

    assert mode(path.parent) == 0o700
    assert mode(path) == 0o600


def test_wal_and_shm_permissions_are_restored_after_recreation(tmp_path: Path) -> None:
    path = tmp_path / "runtime" / "atlas.sqlite3"
    database = RuntimeDatabase(path)
    database.initialize()

    with database.connect() as connection:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("CREATE TABLE IF NOT EXISTS permission_probe (value TEXT)")
        connection.execute("INSERT INTO permission_probe VALUES ('probe')")
        wal = Path(f"{path}-wal")
        shm = Path(f"{path}-shm")
        assert wal.exists()
        assert shm.exists()
        wal.chmod(0o666)
        shm.chmod(0o666)
        database._secure_database_files()
        assert mode(wal) == 0o600
        assert mode(shm) == 0o600

    path.chmod(0o666)
    database._secure_database_files()
    assert mode(path) == 0o600
