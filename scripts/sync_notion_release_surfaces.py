from __future__ import annotations

import argparse
import json
from datetime import date

from atlas_ros.release.surface_sync import (
    LiveNotionContentAdapter,
    ReleaseAuthority,
    ReleaseSurfaceSyncService,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Synchronize live Notion release references from one governed payload."
    )
    parser.add_argument("--active-release", required=True)
    parser.add_argument("--package-version", required=True)
    parser.add_argument("--rollback-release", required=True)
    parser.add_argument("--active-package-url", required=True)
    parser.add_argument("--review-date", required=True)
    parser.add_argument("--authorization-ref", default="")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    authority = ReleaseAuthority(
        active_release=args.active_release,
        package_version=args.package_version,
        rollback_release=args.rollback_release,
        active_package_url=args.active_package_url,
        review_date=date.fromisoformat(args.review_date),
    )
    service = ReleaseSurfaceSyncService(LiveNotionContentAdapter.from_environment())
    plan = service.plan(authority)
    payload: dict[str, object] = {
        "mode": "apply" if args.apply else "dry-run",
        "plan": plan.as_dict(),
    }
    if not plan.valid:
        print(json.dumps(payload))
        raise SystemExit(2)
    if args.apply:
        payload["result"] = service.apply(
            plan,
            confirmed=True,
            authorization_ref=args.authorization_ref,
        ).as_dict()
    print(json.dumps(payload))


if __name__ == "__main__":
    main()
