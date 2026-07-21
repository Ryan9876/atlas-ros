from __future__ import annotations

import re
import sys
from pathlib import Path

PIN_RE = re.compile(r"^[A-Za-z0-9_.-]+==[^\\s;]+")
HASH_RE = re.compile(r"--hash=sha256:[0-9a-f]{64}")


def validate(path: Path) -> list[str]:
    errors: list[str] = []
    text = path.read_text(encoding="utf-8")
    logical_lines: list[str] = []
    current = ""
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        current += (" " if current else "") + stripped.rstrip("\\").strip()
        if not stripped.endswith("\\"):
            logical_lines.append(current)
            current = ""
    if current:
        logical_lines.append(current)
    if not logical_lines:
        errors.append("lock file contains no requirements")
    for line in logical_lines:
        if line.startswith("--"):
            continue
        if not PIN_RE.match(line):
            errors.append(f"requirement is not exactly pinned: {line}")
        if not HASH_RE.search(line):
            errors.append(f"requirement has no SHA-256 hash: {line}")
    return errors


def main() -> int:
    path = Path(sys.argv[1] if len(sys.argv) > 1 else "requirements.runtime.lock")
    if not path.is_file():
        print(f"missing dependency lock: {path}", file=sys.stderr)
        return 2
    errors = validate(path)
    if errors:
        print("dependency lock validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1
    print(f"validated exact, hash-protected dependency lock: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
