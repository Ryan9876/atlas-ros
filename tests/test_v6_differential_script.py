import json
from pathlib import Path
from typing import Any

from scripts import evaluate_v6_differential


def test_main_writes_to_requested_output(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    report = {
        "baseline": "Atlas ROS v5.6.0",
        "candidate": "Atlas ROS v6.0.0rc1",
        "compared_fields": 1,
        "unexplained_differences": {},
        "unexplained_drift_count": 0,
        "objective_preserved": True,
        "hierarchy_and_task_count_preserved": True,
        "section_routing_preserved": True,
        "command_parsing_preserved": True,
        "live_provider_writes": 0,
        "eligible": True,
    }
    monkeypatch.setattr(evaluate_v6_differential, "evaluate", lambda _: report)
    output = tmp_path / "nested" / "differential.json"

    evaluate_v6_differential.main(
        [
            "--rollback-source",
            str(tmp_path / "rollback"),
            "--output",
            str(output),
        ]
    )

    assert json.loads(output.read_text(encoding="utf-8")) == report
