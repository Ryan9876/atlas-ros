"""Profile-bundle compiler and privacy checks for Atlas ROS v7.6.1."""
from __future__ import annotations

import json
import re
from pathlib import Path

from atlas_ros.user_communication_contracts_v761 import UserCommunicationProfileBundleV1

_FORBIDDEN_CONTENT = (
    re.compile(r"-----BEGIN [A-Z ]+PRIVATE KEY-----"),
    re.compile(r"\b(?:api[_-]?key|access[_-]?token|bearer)\b", re.IGNORECASE),
    re.compile(r"\b(?:diagnosis|clinical disorder|protected characteristic)\b", re.IGNORECASE),
)


def load_profile_bundle(path: Path) -> UserCommunicationProfileBundleV1:
    return UserCommunicationProfileBundleV1.model_validate_json(path.read_text())


def validate_profile_minimization(
    bundle: UserCommunicationProfileBundleV1,
) -> tuple[str, ...]:
    errors: list[str] = []
    payload = json.dumps(bundle.model_dump(mode="json"), sort_keys=True)
    if any(pattern.search(payload) for pattern in _FORBIDDEN_CONTENT):
        errors.append("profile contains prohibited sensitive or secret-like content")
    if bundle.contains_raw_assessment_content:
        errors.append("profile contains raw assessment content")
    if bundle.execution_authorization_effect or bundle.provider_permission_effect:
        errors.append("profile cannot create execution or provider authority")
    if bundle.provider_write_count or bundle.todoist_write_count:
        errors.append("profile bundle must be provider-write free")
    for source in bundle.source_evidence:
        if source.raw_content_retained:
            errors.append(f"{source.source_id}: raw source content is retained")
        if source.embedded_instructions_authorized:
            errors.append(f"{source.source_id}: embedded instructions are authorized")
    return tuple(sorted(errors))


def write_minimized_bundle(
    *,
    source: Path,
    output: Path,
) -> tuple[UserCommunicationProfileBundleV1, str]:
    bundle = load_profile_bundle(source)
    errors = validate_profile_minimization(bundle)
    if errors:
        raise ValueError("; ".join(errors))
    output.parent.mkdir(parents=True, exist_ok=True)
    rendered = json.dumps(bundle.model_dump(mode="json"), indent=2, sort_keys=True) + "\n"
    output.write_text(rendered)
    return bundle, bundle.deterministic_digest


def load_profile_or_none(path: Path) -> UserCommunicationProfileBundleV1 | None:
    """Fail closed to the v7.6.0 baseline for missing, invalid, or corrupted bundles."""
    try:
        bundle = load_profile_bundle(path)
    except (OSError, ValueError):
        return None
    if validate_profile_minimization(bundle):
        return None
    return bundle
