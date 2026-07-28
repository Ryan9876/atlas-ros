"""Version-neutral deterministic release compiler.

The compiler transforms one declarative release specification into candidate
artifacts. It never publishes, activates authority, or performs provider writes.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import yaml

from atlas_ros.contracts.digests import sha256_digest
from atlas_ros.contracts.release import (
    CompiledReleaseArtifact,
    ReleaseCompilationReceipt,
    ReleaseSpecification,
)

COMPILER_VERSION = "1.1.0"


class ReleaseCompilationError(ValueError):
    """Raised when a release specification cannot compile safely."""


@dataclass(frozen=True, slots=True)
class CompiledRelease:
    specification: ReleaseSpecification
    files: Mapping[str, str]
    receipt: ReleaseCompilationReceipt

    def write(self, root: Path) -> tuple[Path, ...]:
        """Write the deterministic candidate bundle beneath one output root."""
        root = root.resolve()
        written: list[Path] = []
        for relative, content in sorted(self.files.items()):
            path = (root / relative).resolve()
            if root != path and root not in path.parents:
                raise ReleaseCompilationError(f"compiler output escapes root: {relative}")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            written.append(path)
        return tuple(written)


def load_release_specification(
    path: Path,
    *,
    source_commit: str | None = None,
) -> ReleaseSpecification:
    """Load and validate one YAML or JSON release specification."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as error:
        raise ReleaseCompilationError(f"cannot read release specification: {path}") from error
    try:
        loaded = yaml.safe_load(text)
    except yaml.YAMLError as error:
        raise ReleaseCompilationError("release specification is not valid YAML") from error
    if not isinstance(loaded, Mapping):
        raise ReleaseCompilationError("release specification must be a mapping")
    values = cast(dict[str, Any], dict(loaded))
    values.pop("contract_id", None)
    values.pop("schema_version", None)
    values.pop("specification_digest", None)
    identity = values.get("identity")
    if not isinstance(identity, Mapping):
        raise ReleaseCompilationError("release specification identity must be a mapping")
    identity_values = dict(identity)
    declared_commit = identity_values.get("source_commit")
    if source_commit is not None:
        if re.fullmatch(r"[0-9a-f]{40}", source_commit) is None:
            raise ReleaseCompilationError("source commit override must be an exact commit SHA")
        if declared_commit not in {"__SOURCE_COMMIT__", source_commit}:
            raise ReleaseCompilationError(
                "source commit override disagrees with the release specification"
            )
        identity_values["source_commit"] = source_commit
    elif declared_commit == "__SOURCE_COMMIT__":
        raise ReleaseCompilationError(
            "release specification source identity is unbound; provide an exact source commit"
        )
    values["identity"] = identity_values
    try:
        return ReleaseSpecification.create(**values)
    except ValueError as error:
        raise ReleaseCompilationError(str(error)) from error


def compile_release(
    specification: ReleaseSpecification,
    *,
    compiled_at: datetime | None = None,
) -> CompiledRelease:
    """Compile all candidate artifacts from one immutable specification."""
    if not specification.candidate_only:
        raise ReleaseCompilationError("compiler accepts candidate-only specifications")
    _validate_semantic_scope(specification)
    version = specification.identity.version
    slug = _version_slug(version)
    transaction_prefix = sha256_digest(
        {
            "specification_digest": specification.specification_digest,
            "source_commit": specification.identity.source_commit,
        }
    )[:20]

    files: dict[str, str] = {}
    files[f"release/RELEASE_MANIFEST_{slug}.md"] = _render_manifest(specification)
    files["current/RELEASE_MANIFEST.md"] = _render_current_manifest(specification)
    files[f"release/RELEASE_SCOPE_{slug}.md"] = _render_scope(specification)
    files[f"release/RELEASE_NOTES_{slug}.md"] = _render_notes(specification)
    files["governance/AUTHORITY_CANDIDATE.json"] = _json(
        _authority_candidate(specification, transaction_prefix)
    )
    files["governance/RELEASE_INDEX_CANDIDATE.md"] = _render_release_index(
        specification
    )
    files["plans/VALIDATION_PLAN.json"] = _json(
        {
            "schema_version": "1.0",
            "release_version": version,
            "profile": list(specification.validation_profile),
            "provider_writes": 0,
            "production_authorized": False,
        }
    )
    files["plans/PUBLICATION_PLAN.json"] = _json(
        {
            "schema_version": "1.0",
            "transaction_id": f"release-publication-{transaction_prefix}",
            "release_version": version,
            "policy": list(specification.publication_policy),
            "requires_separate_exact_authorization": True,
            "enabled": False,
        }
    )
    files["plans/AUTHORITY_ACTIVATION_PLAN.json"] = _json(
        {
            "schema_version": "1.0",
            "transaction_id": f"authority-activation-{transaction_prefix}",
            "release_version": version,
            "policy": list(specification.authority_activation_policy),
            "requires_independent_publication_readback": True,
            "enabled": False,
        }
    )
    files["plans/RESTORATION_PLAN.json"] = _json(
        {
            "schema_version": "1.0",
            "candidate": specification.identity.model_dump(mode="json"),
            "immediate_rollback": specification.immediate_rollback.model_dump(mode="json"),
            "historical_rollbacks": [
                item.model_dump(mode="json")
                for item in specification.historical_rollbacks
            ],
            "requirements": list(specification.restoration_requirements),
        }
    )
    files["plans/ROLLBACK_EVIDENCE_REQUIREMENTS.json"] = _json(
        {
            "schema_version": "1.0",
            "release_version": version,
            "rollback_release": specification.immediate_rollback.model_dump(mode="json"),
            "required_evidence": [
                "immutable source identity",
                "published checksums",
                "clean installation",
                "runtime identity",
                "restoration readback",
                "authority rollback transaction rehearsal",
            ],
        }
    )
    files["evidence/SOURCE_MANIFEST.json"] = _json(
        {
            "schema_version": "1.0",
            "package_name": specification.package_name,
            "release_version": version,
            "source_commit": specification.identity.source_commit,
            "specification_digest": specification.specification_digest,
        }
    )
    files["evidence/SBOM_REFERENCES.json"] = _json(
        {
            "schema_version": "1.0",
            "release_version": version,
            "required_formats": ["CycloneDX 1.5"],
            "artifact_requirements": list(specification.artifact_requirements),
        }
    )
    files["evidence/TRANSACTION_IDENTITIES.json"] = _json(
        {
            "schema_version": "1.0",
            "validation": f"release-validation-{transaction_prefix}",
            "publication": f"release-publication-{transaction_prefix}",
            "authority_activation": f"authority-activation-{transaction_prefix}",
            "restoration": f"release-restoration-{transaction_prefix}",
        }
    )
    files["evidence/RELEASE_RECEIPT_TEMPLATE.json"] = _json(
        {
            "schema_version": "1.0",
            "release_version": version,
            "source_commit": specification.identity.source_commit,
            "candidate_validated": False,
            "published": False,
            "authority_activated": False,
            "provider_writes": 0,
            "production_authorized": False,
        }
    )

    artifacts = tuple(
        CompiledReleaseArtifact(
            path=path,
            content_sha256=sha256_digest(content),
            media_type=_media_type(path),
        )
        for path, content in sorted(files.items())
    )
    receipt = ReleaseCompilationReceipt(
        package_name=specification.package_name,
        release_version=version,
        source_commit=specification.identity.source_commit,
        specification_digest=specification.specification_digest,
        compiler_version=COMPILER_VERSION,
        artifacts=artifacts,
        output_digest=sha256_digest(
            [artifact.model_dump(mode="json") for artifact in artifacts]
        ),
        compiled_at=compiled_at or datetime(1970, 1, 1, tzinfo=UTC),
    )
    files["evidence/RELEASE_COMPILATION_RECEIPT.json"] = _json(
        receipt.model_dump(mode="json")
    )
    files["CHECKSUMS.sha256"] = "".join(
        f"{sha256_digest(content)}  {path}\n"
        for path, content in sorted(files.items())
        if path != "CHECKSUMS.sha256"
    )
    return CompiledRelease(specification=specification, files=files, receipt=receipt)


def _validate_semantic_scope(specification: ReleaseSpecification) -> None:
    candidate_major = int(specification.identity.version.split(".", 1)[0])
    rollback_major = int(specification.immediate_rollback.version.split(".", 1)[0])
    if candidate_major < rollback_major:
        raise ReleaseCompilationError("candidate major version cannot precede rollback major")
    if specification.identity.source_commit == specification.immediate_rollback.source_commit:
        raise ReleaseCompilationError("candidate and rollback source commits must differ")
    mandatory = {
        "build-once artifacts",
        "independent post-publication readback",
        "rollback restoration",
    }
    missing = mandatory - set(specification.promotion_prerequisites)
    if missing:
        raise ReleaseCompilationError(
            "release specification is missing promotion prerequisites: "
            + ", ".join(sorted(missing))
        )


def _version_slug(version: str) -> str:
    if re.fullmatch(r"\d+\.\d+\.\d+", version) is None:
        raise ReleaseCompilationError("release version must be semantic")
    return "V" + version.replace(".", "")


def _render_manifest(spec: ReleaseSpecification) -> str:
    version = spec.identity.version
    return (
        f"# Atlas ROS v{version} Immutable Release Manifest Candidate\n\n"
        "Status: Candidate only. This document does not activate production authority.\n\n"
        f"- Package: `{spec.package_name}`\n"
        f"- Package version: `{version}`\n"
        f"- Authority model version: `{spec.authority_model_version}`\n"
        f"- Exact source commit: `{spec.identity.source_commit}`\n"
        f"- Candidate tag: `{spec.identity.tag}`\n"
        f"- Immediate rollback: `{spec.immediate_rollback.version}` at "
        f"`{spec.immediate_rollback.source_commit}`\n"
        f"- Integration Inventory authority: {spec.integration_inventory_url}\n"
        + (
            f"- Integration Inventory data source: "
            f"{spec.integration_inventory_data_source}\n"
            if spec.integration_inventory_data_source is not None
            else ""
        )
        + "\n"
        "## Required integrations\n\n"
        + "\n".join(f"- {item}" for item in spec.required_integrations)
        + "\n\n## Optional integrations\n\n"
        + "\n".join(f"- {item}" for item in spec.optional_integrations)
        + "\n\n## Scope\n\n"
        + "\n".join(f"- {item}" for item in spec.release_scope)
        + "\n\n## Reserved actions\n\n"
        "Production promotion, authority activation, Drive deletion, credential revocation, "
        "historical deletion, immutable-release mutation, permission expansion, and unattended "
        "consequential execution remain disabled pending separate exact authorization.\n"
    )


def _render_current_manifest(spec: ReleaseSpecification) -> str:
    return (
        f"# Atlas ROS v{spec.identity.version} Current-Manifest Projection Candidate\n\n"
        "Generated projection only. The live `release/RELEASE_MANIFEST.md` remains unchanged "
        "until an independently verified authority-activation transaction is authorized.\n\n"
        f"Candidate source: `{spec.identity.source_commit}`\n"
    )


def _render_scope(spec: ReleaseSpecification) -> str:
    return (
        f"# Atlas ROS v{spec.identity.version} Release Scope Candidate\n\n"
        "Status: Development candidate; not production authority.\n\n"
        + "\n".join(f"- {item}" for item in spec.release_scope)
        + "\n"
    )


def _render_notes(spec: ReleaseSpecification) -> str:
    return (
        f"# Atlas ROS v{spec.identity.version} Release Notes Scaffold\n\n"
        "## Candidate summary\n\n"
        "Generated from the declarative release specification. Final notes must bind exact "
        "validation, artifact, restoration, and publication evidence.\n\n"
        "## Compatibility\n\n"
        + "\n".join(f"- {item}" for item in spec.compatibility_rules)
        + "\n"
    )


def _authority_candidate(
    spec: ReleaseSpecification,
    transaction_prefix: str,
) -> dict[str, object]:
    return {
        "schema_version": "1.0",
        "status": "Candidate",
        "repository": "Ryan9876/atlas-ros",
        "authority_model_version": spec.authority_model_version,
        "candidate_release": spec.identity.model_dump(mode="json"),
        "immediate_rollback": spec.immediate_rollback.model_dump(mode="json"),
        "historical_rollbacks": [
            item.model_dump(mode="json") for item in spec.historical_rollbacks
        ],
        "required_integrations": list(spec.required_integrations),
        "optional_integrations": list(spec.optional_integrations),
        "notion_system_state_url": spec.notion_system_state_url,
        "integration_inventory_url": spec.integration_inventory_url,
        "integration_inventory_data_source": (
            spec.integration_inventory_data_source
        ),
        "activation_transaction_id": f"authority-activation-{transaction_prefix}",
        "production_authorized": False,
        "authority_activated": False,
    }


def _render_release_index(spec: ReleaseSpecification) -> str:
    return (
        "# Atlas ROS Release Index Candidate\n\n"
        "Generated from a candidate release specification; not current authority.\n\n"
        f"- Candidate version: {spec.identity.version}\n"
        f"- Candidate commit: {spec.identity.source_commit}\n"
        f"- Immediate rollback: {spec.immediate_rollback.version}\n"
        "- Production status: not authorized\n"
    )


def _json(value: object) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def _media_type(path: str) -> str:
    if path.endswith(".json"):
        return "application/json"
    if path.endswith(".md"):
        return "text/markdown"
    return "text/plain"
