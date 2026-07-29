"""Disabled-by-default compiler for Atlas ROS v7.6.1 communication adaptation."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from atlas_ros.user_communication_contracts_v761 import (
    AdaptationMode,
    CommunicationContext,
    CommunicationPreferenceV1,
    CompiledCommunicationPolicyV1,
    ContradictionState,
    PreferenceConfirmationState,
    SensitivityLevel,
    UserCommunicationProfileBundleV1,
    UserOverrideState,
)

_BASE_DIRECTIVES = (
    "Lead with the conclusion, recommendation, or current state.",
    "Separate verified facts, assumptions, interpretations, risks, and actions.",
    "Explain reasoning for material recommendations.",
    "Present meaningful tradeoffs and recommend a preferred option when supported.",
    "Challenge assumptions respectfully and state uncertainty directly.",
    "Identify diminishing returns when more analysis is unlikely to change the outcome.",
    "Provide a concrete next decision or action when one exists.",
)

_BASE_AVOIDED = (
    "empty reassurance",
    "excessive praise",
    "vague motivation",
    "unsupported certainty",
    "unrelated sensitive profile disclosure",
)


@dataclass(frozen=True)
class UserCommunicationFeaturePolicyV761:
    mode: AdaptationMode = AdaptationMode.DISABLED
    selected_profile_version: str | None = None
    disabled_contexts: frozenset[CommunicationContext] = frozenset()
    disabled_preference_ids: frozenset[str] = frozenset()

    @property
    def inspection_enabled(self) -> bool:
        return self.mode in (AdaptationMode.INSPECTION, AdaptationMode.ADAPTATION)

    @property
    def adaptation_enabled(self) -> bool:
        return self.mode is AdaptationMode.ADAPTATION

    def compile(
        self,
        *,
        context: CommunicationContext,
        now: str,
        request_user_id: str,
        request_workspace_id: str,
        profile: UserCommunicationProfileBundleV1 | None = None,
        current_instruction_directives: tuple[str, ...] = (),
        live_authority_override: bool = False,
        consequential: bool = False,
    ) -> CompiledCommunicationPolicyV1:
        _parse_timestamp(now)
        directives = list(_BASE_DIRECTIVES)
        avoided = list(_BASE_AVOIDED)
        applied: list[str] = []
        excluded: list[str] = []
        profile_version: str | None = None
        profile_digest: str | None = None
        current_override = bool(current_instruction_directives)
        profile_valid = profile is not None and self._profile_eligible(
            profile,
            now=now,
            request_user_id=request_user_id,
            request_workspace_id=request_workspace_id,
        )
        adaptation_allowed = (
            self.adaptation_enabled
            and profile_valid
            and profile is not None
            and profile.global_enabled
            and context not in self.disabled_contexts
            and not current_override
            and not live_authority_override
        )
        if profile is not None:
            profile_version = profile.profile_version
            profile_digest = profile.deterministic_digest
            for preference in profile.preferences:
                if self._preference_eligible(
                    preference,
                    context=context,
                    now=now,
                    consequential=consequential,
                ) and adaptation_allowed:
                    directives.extend(preference.preferred_behaviors)
                    avoided.extend(preference.avoided_behaviors)
                    applied.append(preference.preference_id)
                else:
                    excluded.append(preference.preference_id)
        if current_override:
            directives.extend(current_instruction_directives)
        compiled_directives = _bounded_unique(directives, 16)
        compiled_avoided = _bounded_unique(avoided, 12)
        return CompiledCommunicationPolicyV1(
            context=context,
            profile_version=profile_version,
            profile_digest=profile_digest,
            adaptation_mode=self.mode,
            adaptation_applied=bool(applied),
            current_instruction_override=current_override,
            live_authority_override=live_authority_override,
            directives=compiled_directives,
            avoided_patterns=compiled_avoided,
            applied_preference_ids=tuple(sorted(applied)),
            excluded_preference_ids=tuple(sorted(excluded)),
        )

    def _profile_eligible(
        self,
        profile: UserCommunicationProfileBundleV1,
        *,
        now: str,
        request_user_id: str,
        request_workspace_id: str,
    ) -> bool:
        if self.selected_profile_version and (
            profile.profile_version != self.selected_profile_version
        ):
            return False
        if profile.repository_binding != "Ryan9876/atlas-ros":
            return False
        if profile.user_id != request_user_id:
            return False
        if profile.workspace_id != request_workspace_id:
            return False
        return _parse_timestamp(now) < _parse_timestamp(profile.review_due_at)

    def _preference_eligible(
        self,
        preference: CommunicationPreferenceV1,
        *,
        context: CommunicationContext,
        now: str,
        consequential: bool,
    ) -> bool:
        if preference.preference_id in self.disabled_preference_ids:
            return False
        if preference.user_override_state is UserOverrideState.FORCED_OFF:
            return False
        if context not in preference.applicable_contexts:
            return False
        if preference.expires_at and _parse_timestamp(now) >= _parse_timestamp(
            preference.expires_at
        ):
            return False
        if preference.contradiction_state is ContradictionState.OPEN:
            return False
        if preference.confirmation_state in {
            PreferenceConfirmationState.REJECTED,
            PreferenceConfirmationState.SUPERSEDED,
            PreferenceConfirmationState.CONTRADICTED,
            PreferenceConfirmationState.PROVISIONAL,
        }:
            return False
        if preference.confirmation_state is PreferenceConfirmationState.USER_CONFIRMED:
            confidence_floor = 0.50
        else:
            confidence_floor = 0.80 if consequential else 0.70
        if preference.confidence < confidence_floor:
            return False
        if preference.sensitivity is SensitivityLevel.RESTRICTED and (
            context is not CommunicationContext.SENSITIVE_STRESSFUL
        ):
            return False
        return True


def _bounded_unique(values: list[str], limit: int) -> tuple[str, ...]:
    result: list[str] = []
    for value in values:
        normalized = value.strip()
        if normalized and normalized not in result:
            result.append(normalized)
        if len(result) == limit:
            break
    return tuple(result)


def _parse_timestamp(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        raise ValueError("timestamps must include a timezone")
    return parsed.astimezone(UTC)
