from __future__ import annotations

import json

from atlas_ros.validation.architecture import validate


def main() -> None:
    violations = validate()
    print(json.dumps({"valid": not violations, "violations": violations}, indent=2))
    if violations:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
