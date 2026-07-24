from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from atlas_ros.intelligence.records import CanonicalRecordType, parse_record


def load_record(path: Path) -> CanonicalRecordType:
    payload: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("canonical record file must contain a JSON object")
    return parse_record(payload)


def write_record(path: Path, record: CanonicalRecordType) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(record.model_dump_json(indent=2) + "\n", encoding="utf-8")
