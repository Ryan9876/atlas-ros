import json
from pathlib import Path

from atlas_ros.intelligence.calibration import load_calibration_cases


def test_ryan_evaluation_set_v1_has_promotion_scale_and_domain_coverage():
    path=Path("benchmarks/ryan-intelligence-evaluation-set-v1.json")
    raw=json.loads(path.read_text())
    assert len(raw) >= 50
    assert len({item["id"] for item in raw}) == len(raw)
    assert len({item["domain"] for item in raw}) == 8
    assert all(item["authority_refs"] for item in raw)
    assert all(item["prohibited_outcomes"] for item in raw)
    cases=load_calibration_cases(path)
    assert len(cases)==len(raw)
