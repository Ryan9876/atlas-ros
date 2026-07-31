from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml


def sha256(path: str) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def test_exact_v810_publication_controls_are_bound_and_no_rebuild() -> None:
    manifest = Path("release/RELEASE_MANIFEST_V810.md").read_text()
    authorization = Path("release/V810_EXACT_PACKAGE_AUTHORIZATION.md").read_text()
    trigger = json.loads(Path("release/V810_PUBLICATION_TRIGGER.json").read_text())
    publisher = Path(".github/workflows/v810-authorized-publication-controller.yml").read_text()
    readback = Path(".github/workflows/v810-independent-publication-readback.yml").read_text()

    assert sha256("release/RELEASE_MANIFEST_V810.md") == "bd1cd4ad0ad64c3a77a562e55ca334abcfedb0382a640e4c961bbd85372cff43"
    assert sha256("release/V810_EXACT_PACKAGE_AUTHORIZATION.md") == "830cc61af8b81097253a07dc4402875fd56f06e2fdc137cee00603e65d675455"
    assert trigger["package_source_commit"] == "8843a97e58efe46e632335df95487855b7971a75"
    assert trigger["candidate_artifact_id"] == 8779256493
    assert trigger["candidate_artifact_sha256"] == "dc2f5d93f1d3aafe34d680f6c797fd190d0b2570e9e854cc2917057d0591a22a"
    assert trigger["implementation_merge"] == "32db7aaf307299a98b360bb25271589b0487fe90"
    assert trigger["prepublication_active_version"] == "8.0.0"
    assert trigger["prepublication_rollback_version"] == "7.8.0"
    assert trigger["release_manifest_sha256"] == "bd1cd4ad0ad64c3a77a562e55ca334abcfedb0382a640e4c961bbd85372cff43"
    assert trigger["authorization_sha256"] == "830cc61af8b81097253a07dc4402875fd56f06e2fdc137cee00603e65d675455"
    assert trigger["decision_id"] == "V4D-62"
    assert trigger["review_id"] == "V4V-115"
    assert "No production Notion schema migration is required" in manifest
    assert "AUTHORIZED BY RYAN" in authorization
    assert "python -m build" not in publisher
    assert "pip wheel" not in publisher
    assert "gh release create" in publisher
    assert "release:" in readback
    assert "authority_activated': False" in readback

    yaml.safe_load(publisher)
    yaml.safe_load(readback)
