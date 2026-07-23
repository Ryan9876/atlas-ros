from __future__ import annotations

import hashlib
import hmac
from pathlib import Path


def inventory(root: Path) -> list[Path]:
    root = root.resolve()
    excluded = {
        ".git",
        ".deps",
        ".atlas-runtime",
        "__pycache__",
        "dist",
        "build",
        ".coverage",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        "audit",
        "test-results",
        "candidate-evidence",
        "publication",
        "extracted",
        "clean-wheel",
    }
    return sorted(
        path
        for path in root.rglob("*")
        if path.is_file()
        and not (excluded & set(path.parts))
        and not any(part.startswith(".venv") for part in path.parts)
        and path.name not in {"CHECKSUMS.sha256", "PKG-INFO"}
        and not path.name.endswith(".zip.sha256")
        and path.suffix not in {".zip", ".whl", ".gz"}
    )


def checksums(root: Path, target: Path) -> list[str]:
    root = root.resolve()
    target = target.resolve()
    lines = [
        f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(root).as_posix()}"
        for path in inventory(root)
        if path != target
    ]
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return lines


def _safe_member(root: Path, relative: str) -> Path:
    if not relative or "\x00" in relative:
        raise ValueError("invalid checksum path")
    root = root.resolve()
    candidate = (root / relative).resolve()
    if candidate == root or root not in candidate.parents:
        raise ValueError(f"checksum path escapes release root: {relative}")
    return candidate


def verify(root: Path, checksum_file: Path) -> list[str]:
    errors: list[str] = []
    for number, line in enumerate(checksum_file.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            digest, relative = line.split("  ", 1)
            if len(digest) != 64 or any(c not in "0123456789abcdefABCDEF" for c in digest):
                raise ValueError("invalid digest")
            path = _safe_member(root, relative)
        except ValueError:
            errors.append(f"line {number}")
            continue
        actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""
        if not hmac.compare_digest(actual, digest.lower()):
            errors.append(relative)
    return errors
