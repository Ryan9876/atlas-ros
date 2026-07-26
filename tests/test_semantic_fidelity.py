import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
evaluate = importlib.import_module("scripts.evaluate_semantic_fidelity").evaluate


def test_semantic_fidelity_gold_and_invariance() -> None:
    report = evaluate(Path("benchmarks/semantic-fidelity-v1.json"))
    assert report["eligible"]
    assert report["passed"] == report["cases"]
    assert report["metamorphic_invariance"] == {"cloudvision-invariance": True}
    assert report["live_provider_writes"] == 0
