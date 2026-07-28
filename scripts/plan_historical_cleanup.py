#!/usr/bin/env python3
"""Plan or dry-run a provider-neutral historical cleanup transaction."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from atlas_ros.capabilities.historical_cleanup import HistoricalCleanupPlanner
from atlas_ros.contracts.history import CleanupAuthorization, HistoricalInventory

_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(_REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPOSITORY_ROOT))


def _load(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    from tools.release.historical_cleanup import (
        InMemoryHistoricalStore,
        execute_cleanup,
    )

    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--transaction-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--authorization", type=Path)
    parser.add_argument("--fixture-store", type=Path)
    args = parser.parse_args()

    inventory = HistoricalInventory.model_validate(_load(args.inventory))
    plan = HistoricalCleanupPlanner().plan(
        inventory, transaction_id=args.transaction_id
    )
    result: object = plan.model_dump(mode="json")
    if args.authorization or args.fixture_store:
        if not args.authorization or not args.fixture_store:
            parser.error("dry-run requires both --authorization and --fixture-store")
        authorization = CleanupAuthorization.model_validate(_load(args.authorization))
        raw_store = _load(args.fixture_store)
        if not isinstance(raw_store, dict):
            parser.error("fixture store must be an object")
        store = InMemoryHistoricalStore(
            items={
                str(item_id): (str(value[0]), str(value[1]))
                for item_id, value in raw_store.items()
                if isinstance(value, list) and len(value) == 2
            }
        )
        result = execute_cleanup(plan, authorization, store, dry_run=True).model_dump(
            mode="json"
        )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
