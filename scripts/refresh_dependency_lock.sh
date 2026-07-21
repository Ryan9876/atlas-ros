#!/usr/bin/env bash
set -euo pipefail
python -m pip install --disable-pip-version-check --upgrade \
  'pip-tools==7.5.0'
python -m piptools compile \
  --resolver=backtracking \
  --generate-hashes \
  --strip-extras \
  --output-file=requirements.runtime.lock \
  requirements.runtime.in
python scripts/validate_dependency_lock.py requirements.runtime.lock
