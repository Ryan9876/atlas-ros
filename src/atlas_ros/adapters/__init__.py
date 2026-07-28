"""Replaceable provider and local-state adapters with lazy compatibility exports."""

from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

from atlas_ros.adapters.local_sqlite import (
    ExecutionJournalError,
    JournalTransactionSnapshot,
    SQLiteExecutionJournal,
)

if TYPE_CHECKING:
    from atlas_ros.adapters.keychain import MacOSKeychain
    from atlas_ros.adapters.notion import (
        FakeNotionAdapter,
        LiveNotionAdapter,
        NotionAdapter,
        NotionPage,
    )
    from atlas_ros.adapters.todoist import (
        FakeTodoistAdapter,
        LiveTodoistAdapter,
        TodoistAdapter,
        TodoistProject,
        TodoistTask,
    )

_LEGACY_EXPORTS: dict[str, tuple[str, str]] = {
    "MacOSKeychain": ("atlas_ros.adapters.keychain", "MacOSKeychain"),
    "FakeNotionAdapter": ("atlas_ros.adapters.notion", "FakeNotionAdapter"),
    "LiveNotionAdapter": ("atlas_ros.adapters.notion", "LiveNotionAdapter"),
    "NotionAdapter": ("atlas_ros.adapters.notion", "NotionAdapter"),
    "NotionPage": ("atlas_ros.adapters.notion", "NotionPage"),
    "FakeTodoistAdapter": ("atlas_ros.adapters.todoist", "FakeTodoistAdapter"),
    "LiveTodoistAdapter": ("atlas_ros.adapters.todoist", "LiveTodoistAdapter"),
    "TodoistAdapter": ("atlas_ros.adapters.todoist", "TodoistAdapter"),
    "TodoistProject": ("atlas_ros.adapters.todoist", "TodoistProject"),
    "TodoistTask": ("atlas_ros.adapters.todoist", "TodoistTask"),
}

__all__ = [
    "ExecutionJournalError",
    "FakeNotionAdapter",
    "FakeTodoistAdapter",
    "JournalTransactionSnapshot",
    "LiveNotionAdapter",
    "LiveTodoistAdapter",
    "MacOSKeychain",
    "NotionAdapter",
    "NotionPage",
    "SQLiteExecutionJournal",
    "TodoistAdapter",
    "TodoistProject",
    "TodoistTask",
]


def __getattr__(name: str) -> Any:
    try:
        module_name, symbol = _LEGACY_EXPORTS[name]
    except KeyError as error:
        raise AttributeError(name) from error
    value = getattr(import_module(module_name), symbol)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(set(globals()) | set(__all__))
