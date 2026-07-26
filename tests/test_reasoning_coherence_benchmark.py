import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
evaluate = importlib.import_module("scripts.evaluate_reasoning_coherence").evaluate


def test_reasoning_coherence_benchmark() -> None:
    report = evaluate(Path("benchmarks/reasoning-coherence-v1.json"))
    assert report["eligible"]
    assert report["passed"] == report["cases"]
    assert report["cloudvision_invariant"]
    assert report["provider_writes"] == 0
