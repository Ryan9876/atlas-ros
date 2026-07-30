from __future__ import annotations


class AdapterError(RuntimeError):
    """Safe, redacted external-system failure with optional retry guidance."""

    def __init__(
        self,
        system: str,
        operation: str,
        message: str,
        *,
        retryable: bool = False,
        retry_after_seconds: float | None = None,
    ) -> None:
        super().__init__(f"{system} {operation}: {message}")
        self.system = system
        self.operation = operation
        self.retryable = retryable
        self.retry_after_seconds = (
            retry_after_seconds
            if retryable and retry_after_seconds is not None and retry_after_seconds >= 0
            else None
        )


def parse_retry_after(value: str | None) -> float | None:
    """Parse deterministic Retry-After delta-seconds; malformed values are ignored.

    HTTP-date parsing is intentionally excluded because wall-clock interpretation would
    introduce nondeterministic adapter behavior. The governed orchestrator owns bounds.
    """
    if value is None:
        return None
    candidate = value.strip()
    if not candidate or not candidate.isascii() or not candidate.isdigit():
        return None
    try:
        seconds = int(candidate)
    except ValueError:
        return None
    return float(seconds) if seconds >= 0 else None


class AdapterConfigurationError(AdapterError):
    pass
