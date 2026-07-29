"""Deterministic parser for explicit @atlas lifecycle commands."""

from __future__ import annotations

import re
from dataclasses import dataclass

from atlas_ros.contracts.operational_awareness import (
    AtlasCommandType,
    AtlasCommandV1,
    CommandSourceRefV1,
)
from atlas_ros.policy.operational_awareness import OperationalAwarenessPolicy

_COMMAND_RE = re.compile(r"^@atlas\s+(?P<command>[a-z-]+)(?::\s*(?P<subject>[^\n;]+))?", re.I)


class CommandParseError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class AtlasCommandParser:
    policy: OperationalAwarenessPolicy

    def parse(self, source: CommandSourceRefV1) -> AtlasCommandV1:
        text = source.source_command_text.strip()
        match = _COMMAND_RE.match(text)
        if match is None:
            raise CommandParseError("command must begin with an explicit @atlas command")
        try:
            command_type = AtlasCommandType(match.group("command").lower())
        except ValueError as error:
            raise CommandParseError("unsupported @atlas command") from error
        if command_type not in self.policy.command.allowed_commands:
            raise CommandParseError("command is not enabled by compiled policy")
        subject = (match.group("subject") or "").strip() or None
        remainder = text[match.end() :].strip()
        fields: dict[str, str] = {}
        for raw in re.split(r"[\n;]+", remainder):
            line = raw.strip()
            if not line:
                continue
            if ":" not in line:
                raise CommandParseError(f"unrecognized command field: {line}")
            key, value = line.split(":", 1)
            normalized_key = key.strip().lower().replace("_", "-")
            normalized_value = value.strip()
            if not normalized_key or not normalized_value:
                raise CommandParseError("command fields require a name and value")
            if normalized_key in fields:
                raise CommandParseError(f"duplicate command field: {normalized_key}")
            fields[normalized_key] = normalized_value
        return AtlasCommandV1.create(
            command_type=command_type,
            source=source,
            subject=subject,
            fields=fields,
        )
