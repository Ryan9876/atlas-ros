# Legacy and Compatibility Isolation Report — v7.1 Candidate

Production runtime no longer falls back to the legacy CLI. Runtime imports from provider, migration, release, and legacy packages are rejected by architecture validation. Remaining compatibility entry points are listed in `governance/compatibility-paths.yaml` with owners, tests, review conditions, and `production_reachable: false`.

Historical source packages remain immutable evidence rather than active runtime dependencies. No compatibility path is retained solely for convenience.
