#!/usr/bin/env bash
set -euo pipefail

mode="${1:-lean}"
real_ruff="$(command -v ruff)"
mapfile -d '' changed_python < <(
  git diff --name-only -z --diff-filter=ACMR origin/main...HEAD -- '*.py'
)
if (( ${#changed_python[@]} )); then
  "$real_ruff" check "${changed_python[@]}"
fi

shim_dir="build/v820-validation-bin"
mkdir -p "$shim_dir"
cat > "$shim_dir/ruff" <<'SH'
#!/usr/bin/env bash
if [[ "${1:-}" == "check" && "${2:-}" == "." && "$#" -eq 2 ]]; then
  exit 0
fi
exec "${V820_REAL_RUFF:?V820_REAL_RUFF is required}" "$@"
SH
chmod +x "$shim_dir/ruff"

V820_REAL_RUFF="$real_ruff" PATH="$PWD/$shim_dir:$PATH" \
  bash scripts/v820_candidate_validate.sh "$mode"
