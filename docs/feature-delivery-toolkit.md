# Atlas Feature Delivery Toolkit v1

## Governing rule

Development validation may be incremental and impact-aware. Release-candidate validation remains complete, clean, exact, and authoritative.

## v7.4.0 production scope

The first release is additive and development-only:

- `FeatureImplementationContractV1` with stable digest and fail-closed authority checks;
- `FeatureDefinitionOfDoneV1` and release-readiness evidence checks;
- one local/CI validation planner with edit, feature, branch, and candidate tiers;
- conservative change-impact analysis operating only in shadow mode;
- development validation receipts;
- runtime-to-devtools import boundary enforcement;
- lean draft CI and full candidate validation kept separate;
- manual command fallback.

Impact analysis in v7.4.0 is advisory. It cannot suppress existing or candidate gates.

## Commands

```bash
atlas dev compile-contract feature.yaml
atlas dev explain-impact src/atlas_ros/example.py
atlas dev validate --tier edit --execute
atlas dev validate --tier branch --execute --receipt build/branch-receipt.json
atlas dev release-readiness --dod feature-dod.yaml
```

Without `--execute`, validation produces a deterministic plan and performs no subprocess work.

## Runtime boundary

Production runtime code must not import `atlas_ros.devtools_cli`. Development entry points may import production contracts, but production entry points and capabilities may not import development tooling.

## Manual fallback

The toolkit is not release authority and is not a single point of failure. Recovery may run the established commands directly:

```bash
ruff check .
mypy src
python scripts/validate_architecture.py
pytest
python -m build
```

Existing release controllers, restoration procedures, checksums, and provider safeguards remain authoritative.

## Future prompt template

1. State the feature objective and user-visible workflow.
2. Attach a `FeatureImplementationContractV1` specification.
3. State release-specific scope and exclusions.
4. Provide acceptance scenarios and Ryan-reserved decisions.
5. Identify unusual migration, compatibility, or security requirements.
6. Instruct Atlas to use the canonical Feature Delivery Toolkit.

Future prompts do not need to restate validation tiers, build-once policy, routine fixtures, traceability expectations, or standard release evidence requirements.
