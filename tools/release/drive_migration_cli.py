"""CLI for compiling and verifying checksum-bound Drive migration ledgers.

This tool consumes normalized inventory JSON and never reads, writes, moves, or
deletes Google Drive content. Provider inventory collection remains a separate,
read-only adapter responsibility.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from tools.release.drive_migration_ledger import (
    DriveMigrationLedger,
    load_and_compile,
    load_ledger,
    write_ledger,
)


def compile_inventory(input_path: Path, output_path: Path) -> DriveMigrationLedger:
    """Compile normalized inventory, write it, and verify deterministic readback."""
    ledger = load_and_compile(input_path)
    write_ledger(ledger, output_path)
    readback = load_ledger(output_path)
    if readback != ledger:
        raise ValueError("compiled Drive migration ledger failed deterministic readback")
    return ledger


def verify_ledger(path: Path) -> DriveMigrationLedger:
    """Verify all item evidence, derived totals, and the ledger digest."""
    return load_ledger(path)


def summary(ledger: DriveMigrationLedger) -> dict[str, object]:
    return {
        "schema_version": ledger.schema_version,
        "generated_for_release": ledger.generated_for_release,
        "item_count": len(ledger.items),
        "unresolved_authoritative_items": ledger.unresolved_authoritative_items,
        "staged_current_dependencies": ledger.staged_current_dependencies,
        "verified_github_representations": ledger.verified_github_representations,
        "complete_for_promotion_readiness": ledger.complete_for_promotion_readiness,
        "ready_for_post_promotion_retirement": (
            ledger.ready_for_post_promotion_retirement
        ),
        "ledger_sha256": ledger.ledger_sha256,
        "provider_actions_performed": 0,
        "destructive_actions_performed": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(prog="atlas-drive-ledger")
    subcommands = parser.add_subparsers(dest="command", required=True)

    compile_command = subcommands.add_parser("compile")
    compile_command.add_argument("inventory", type=Path)
    compile_command.add_argument("output", type=Path)

    verify_command = subcommands.add_parser("verify")
    verify_command.add_argument("ledger", type=Path)

    args = parser.parse_args()
    if args.command == "compile":
        ledger = compile_inventory(args.inventory, args.output)
    else:
        ledger = verify_ledger(args.ledger)
    print(json.dumps(summary(ledger), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
