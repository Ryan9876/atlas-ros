from __future__ import annotations


class AdapterError(RuntimeError):
    """Safe, redacted external-system failure."""

    def __init__(
        self, system: str, operation: str, message: str, *, retryable: bool = False
    ) -> None:
        super().__init__(f"{system} {operation}: {message}")
        self.system = system
        self.operation = operation
        self.retryable = retryable


class AdapterConfigurationError(AdapterError):
    pass
