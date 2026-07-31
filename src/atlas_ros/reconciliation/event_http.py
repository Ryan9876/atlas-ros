from __future__ import annotations

import json
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from atlas_ros.reconciliation.events import (
    DurableEventQueue,
    notion_envelope,
    todoist_envelope,
)

StartResponse = Callable[[str, list[tuple[str, str]]], Any]


@dataclass(frozen=True)
class EventReceiverConfig:
    todoist_client_secret: str
    notion_verification_token: str
    policy_version: str
    ingress_enabled: bool = False
    max_body_bytes: int = 1_048_576


class EventReceiverApplication:
    """Deployable WSGI webhook receiver; TLS and secret injection belong to the runtime."""

    def __init__(self, queue: DurableEventQueue, config: EventReceiverConfig) -> None:
        self.queue = queue
        self.config = config

    @staticmethod
    def _response(
        start_response: StartResponse,
        status: str,
        payload: Mapping[str, Any],
    ) -> Iterable[bytes]:
        body = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        start_response(
            status,
            [("Content-Type", "application/json"), ("Content-Length", str(len(body)))],
        )
        return [body]

    @staticmethod
    def _headers(environ: Mapping[str, Any]) -> dict[str, str]:
        return {
            key.removeprefix("HTTP_").replace("_", "-").casefold(): str(value)
            for key, value in environ.items()
            if key.startswith("HTTP_")
        }

    def __call__(
        self, environ: Mapping[str, Any], start_response: StartResponse
    ) -> Iterable[bytes]:
        path = str(environ.get("PATH_INFO", ""))
        if path == "/healthz":
            return self._response(start_response, "200 OK", {"status": "healthy"})
        if path == "/readyz":
            status = "200 OK" if self.config.ingress_enabled else "503 Service Unavailable"
            return self._response(
                start_response,
                status,
                {"status": "ready" if self.config.ingress_enabled else "activation_blocked"},
            )
        if str(environ.get("REQUEST_METHOD", "")).upper() != "POST":
            return self._response(
                start_response, "405 Method Not Allowed", {"error": "POST required"}
            )
        if not self.config.ingress_enabled:
            return self._response(
                start_response,
                "503 Service Unavailable",
                {"error": "event ingress is not activated"},
            )
        try:
            length = int(str(environ.get("CONTENT_LENGTH") or "0"))
        except ValueError:
            return self._response(
                start_response, "400 Bad Request", {"error": "invalid content length"}
            )
        if length <= 0 or length > self.config.max_body_bytes:
            return self._response(
                start_response, "413 Payload Too Large", {"error": "invalid body size"}
            )
        stream = environ.get("wsgi.input")
        if stream is None or not hasattr(stream, "read"):
            return self._response(
                start_response, "400 Bad Request", {"error": "request body required"}
            )
        raw_body = stream.read(length)
        if not isinstance(raw_body, bytes) or len(raw_body) != length:
            return self._response(
                start_response, "400 Bad Request", {"error": "incomplete request body"}
            )
        headers = self._headers(environ)
        try:
            if path == "/webhooks/todoist":
                event = todoist_envelope(
                    raw_body,
                    headers,
                    client_secret=self.config.todoist_client_secret,
                    policy_version=self.config.policy_version,
                )
                accepted = self.queue.accept(event)
                return self._response(
                    start_response,
                    "200 OK",
                    {"event_id": accepted.event_id, "state": accepted.state.value},
                )
            if path == "/webhooks/notion":
                event = notion_envelope(
                    raw_body,
                    headers,
                    verification_token=self.config.notion_verification_token,
                    policy_version=self.config.policy_version,
                )
                accepted = self.queue.accept(event)
                return self._response(
                    start_response,
                    "202 Accepted",
                    {"event_id": accepted.event_id, "state": accepted.state.value},
                )
        except PermissionError as exc:
            return self._response(start_response, "401 Unauthorized", {"error": str(exc)})
        except (ValueError, json.JSONDecodeError) as exc:
            return self._response(start_response, "400 Bad Request", {"error": str(exc)})
        return self._response(start_response, "404 Not Found", {"error": "unknown endpoint"})
