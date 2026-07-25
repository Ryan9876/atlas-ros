from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERN = re.compile(r"\bW(?:0[1-4]|03A)\b|atlas_ros\.(?:workflows|legacy)")
EXCLUDED = {
    "PKG-INFO",
    "scripts/inventory_w_references.py",
    "release/W_NUMBER_RETIREMENT_INVENTORY.json",
}


def disposition(path: str) -> str:
    if path.startswith(
        (
            "docs/migration/",
            "scripts/evaluate_v6_differential.py",
            "tests/test_phase7_semantic_cutover.py",
        )
    ):
        return "retain_archival_or_migration"
    if path.startswith(
        (
            "candidate-evidence/",
            "docs/adr/",
            "docs/release/",
            "release/atlas-ros-",
            "release/RELEASE_",
            "release/FULL_",
            "release/V5",
            "release/INSTALL_ON_MAC.md",
            "scripts/build_v5",
            "tools/assemble_v410_restoration.py",
            "CHANGELOG.md",
            "docs/roadmap/PHASE_1_CLASSIFICATION_INTELLIGENCE_EXECUTION_PLAN.md",
        )
    ):
        return "retain_historical_evidence"
    if path.startswith("tests/"):
        return "replace_or_retirement_test"
    return "remove_or_replace"


def main() -> None:
    references: list[dict[str, object]] = []
    for path in sorted(ROOT.rglob("*")):
        relative = path.relative_to(ROOT).as_posix()
        if (
            not path.is_file()
            or relative in EXCLUDED
            or any(part.startswith(".") for part in path.relative_to(ROOT).parts)
            or any(
                part in {"dist", "build", "__pycache__", "extracted", "clean-wheel"}
                for part in path.parts
            )
        ):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        matches = sorted(set(PATTERN.findall(text)))
        if matches:
            references.append(
                {
                    "path": relative,
                    "disposition": disposition(relative),
                    "match_count": len(list(PATTERN.finditer(text))),
                }
            )
    runtime_modules = sorted(
        path.relative_to(ROOT).as_posix()
        for path in (ROOT / "src" / "atlas_ros").rglob("w*.py")
    )
    blocking = [
        item
        for item in references
        if item["disposition"] == "remove_or_replace"
        and not str(item["path"]).startswith("src/atlas_ros/validation/")
    ]
    payload: dict[str, object] = {
        "schema_version": 1,
        "candidate": "6.0.0rc1",
        "runtime_w_modules": runtime_modules,
        "runtime_w_module_count": len(runtime_modules),
        "blocking_references": blocking,
        "blocking_reference_count": len(blocking),
        "references": references,
    }
    digest_payload = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    payload["inventory_sha256"] = hashlib.sha256(digest_payload).hexdigest()
    output = ROOT / "release" / "W_NUMBER_RETIREMENT_INVENTORY.json"
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if runtime_modules or blocking:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
