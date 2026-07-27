from __future__ import annotations

import json

from atlas_ros.validation.architecture import validate
from atlas_ros.validation.architecture_v7 import validate_v7


def main() -> None:
    violations = [*validate(), *validate_v7()]
    print(json.dumps({"valid": not violations, "violations": violations}, indent=2))
    if violations:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
