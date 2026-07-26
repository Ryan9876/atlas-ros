from pathlib import Path

from scripts.evaluate_semantic_fidelity import evaluate


def test_semantic_fidelity_gold_and_invariance() -> None:
    report = evaluate(Path("benchmarks/semantic-fidelity-v1.json"))
    assert report["eligible"]
    assert report["passed"] == report["cases"]
    assert report["metamorphic_invariance"] == {"cloudvision-invariance": True}
    assert report["live_provider_writes"] == 0
