from __future__ import annotations

from scripts.compare_v700_performance import _benchmark_passed


def test_canonical_boolean_benchmark_report_passes() -> None:
    assert _benchmark_passed(
        {
            "passed": True,
            "zero_provider_writes": True,
        }
    )


def test_legacy_string_benchmark_report_passes() -> None:
    assert _benchmark_passed(
        {
            "status": "passed",
            "provider_writes": 0,
        }
    )


def test_benchmark_report_rejects_failed_or_write_capable_results() -> None:
    assert not _benchmark_passed(
        {
            "passed": False,
            "zero_provider_writes": True,
        }
    )
    assert not _benchmark_passed(
        {
            "passed": True,
            "zero_provider_writes": False,
        }
    )
