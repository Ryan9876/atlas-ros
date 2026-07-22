import importlib.util
import json
from pathlib import Path

import pytest

from atlas_ros.intelligence.calibration import load_calibration_cases


def _load_promotion_module():
    script = Path("scripts/prepare_v500_promotion.py")
    spec = importlib.util.spec_from_file_location("prepare_v500_promotion", script)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_ryan_evaluation_set_v1_has_promotion_scale_and_domain_coverage():
    path = Path("benchmarks/ryan-intelligence-evaluation-set-v1.json")
    raw = json.loads(path.read_text())
    assert len(raw) >= 50
    assert len({item["id"] for item in raw}) == len(raw)
    assert len({item["domain"] for item in raw}) == 8
    assert all(item["authority_refs"] for item in raw)
    assert all(item["prohibited_outcomes"] for item in raw)
    cases = load_calibration_cases(path)
    assert len(cases) == len(raw)


def test_solo_maintainer_review_evidence_is_accepted(tmp_path: Path):
    module = _load_promotion_module()
    review_path = tmp_path / "review.json"
    reviewed_head_sha = "9f77e83889052876d1d299629e7ee7f3cbfafe6a"
    review_path.write_text(
        json.dumps(
            {
                "path": "solo_maintainer",
                "reviewer": "Ryan9876",
                "status": "approved",
                "evidence_reference": "GitHub PR #5 comment 5048550568",
                "reviewed_head_sha": reviewed_head_sha,
                "checklist_evidence": ["scope reviewed", "CI passed"],
            }
        ),
        encoding="utf-8",
    )

    review = module.load_governed_review(review_path)

    assert review is not None
    assert review["path"] == "solo_maintainer"
    assert review["status"] == "approved"


def test_solo_maintainer_review_requires_checklist(tmp_path: Path):
    module = _load_promotion_module()
    review_path = tmp_path / "review.json"
    reviewed_head_sha = "9f77e83889052876d1d299629e7ee7f3cbfafe6a"
    review_path.write_text(
        json.dumps(
            {
                "path": "solo_maintainer",
                "reviewer": "Ryan9876",
                "status": "approved",
                "evidence_reference": "GitHub PR #5 comment 5048550568",
                "reviewed_head_sha": reviewed_head_sha,
                "checklist_evidence": [],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="requires checklist evidence"):
        module.load_governed_review(review_path)


def test_promotion_script_uses_governed_review_terminology():
    source = Path("scripts/prepare_v500_promotion.py").read_text(encoding="utf-8")

    assert "candidate_ready_for_governed_review" in source
    assert "candidate_ready_for_independent_review" not in source
    assert "independent reviewer approval" not in source
