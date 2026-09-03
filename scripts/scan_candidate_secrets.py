from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

PATTERNS = {
    "private-key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "aws-access-key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "github-token": re.compile(r"\b(?:ghp|github_pat)_[A-Za-z0-9_]{20,}\b"),
    "slack-token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
    "generic-secret-assignment": re.compile(
        r"(?i)\b(?:password|passwd|secret|api[_-]?key|access[_-]?token)\s*[:=]\s*[\"']?([^\s\"']{12,})"
    ),
}

EXCLUDED_PARTS = {
    ".git",
    ".venv",
    "build",
    "dist",
    "clean-wheel",
    "extracted",
    "source-verification",
    "test-results",
}

TEXT_SUFFIXES = {
    ".cfg",
    ".ini",
    ".json",
    ".md",
    ".py",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}

PLACEHOLDERS = {
    "changeme",
    "example",
    "placeholder",
    "redacted",
    "secret-value",
    "test-only-value",
    "your-token-here",
}


def _is_python_expression(path: Path, finding_type: str, candidate: str) -> bool:
    """Reject code expressions that are not embedded credential literals."""
    if path.suffix.casefold() != ".py" or finding_type != "generic-secret-assignment":
        return False
    normalized = candidate.strip()
    return (
        "(" in normalized
        or normalized.startswith(
            (
                "self.",
                "cls.",
                "os.",
                "env.",
                "keyring.",
                "subprocess.",
            )
        )
    )


def scan(root: Path) -> dict[str, Any]:
    findings: list[dict[str, Any]] = []
    files_scanned = 0
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.suffix.casefold() not in TEXT_SUFFIXES:
            continue
        if any(part in EXCLUDED_PARTS for part in path.parts):
            continue
        files_scanned += 1
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            for name, pattern in PATTERNS.items():
                for match in pattern.finditer(line):
                    candidate = match.group(1) if match.lastindex else match.group(0)
                    normalized = re.sub(
                        r"['\";,.)]+$",
                        "",
                        candidate.casefold().strip(),
                    )
                    if _is_python_expression(path, name, candidate):
                        continue
                    if normalized in PLACEHOLDERS or any(
                        marker in normalized
                        for marker in ("${{", "<secret>", "example.com", "dummy")
                    ):
                        continue
                    findings.append(
                        {
                            "type": name,
                            "path": str(path.relative_to(root)),
                            "line": line_number,
                            "match_fingerprint": __import__("hashlib").sha256(
                                candidate.encode("utf-8")
                            ).hexdigest(),
                        }
                    )
    return {
        "scanner": "atlas-candidate-secret-patterns-v1",
        "root": str(root),
        "files_scanned": files_scanned,
        "finding_count": len(findings),
        "findings": findings,
        "passed": not findings,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path("."))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = scan(args.root.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
