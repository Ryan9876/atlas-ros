# Atlas ROS v8.1.0 Independent Candidate Readback

Status: **PASSED** — verification only; no publication or production authority change.

## Bound identities

- Package source commit: `8843a97e58efe46e632335df95487855b7971a75`
- Candidate workflow run: `30593561321`
- Candidate artifact: `8779256493`
- Candidate artifact SHA-256: `dc2f5d93f1d3aafe34d680f6c797fd190d0b2570e9e854cc2917057d0591a22a`
- Independent workflow run: `30593728650`
- Independent readback artifact: `8779299052`
- Independent readback artifact SHA-256: `8d990e20ca01bcc2a48a48d383cec1e41fb0aeeff155761f4f1e4ddde9601af7`
- Independent receipt SHA-256: `96fd1045d7c9ec5696214902b5b49a487a119d5f677272719af50dff74133b91`

## Independent checks

The verifier downloaded the retained candidate through the GitHub Actions artifact API and did not rebuild it. It verified:

- outer artifact digest;
- source commit and build count;
- all package and evidence checksums;
- exact package index values;
- 1,042 tests with zero failures, errors, or skips;
- total coverage above the required threshold;
- zero provider, Notion, and Todoist writes;
- zero production schema changes;
- clean source-distribution installation;
- clean wheel installation;
- installed identity `8.1.0` and `valid: true` from both formats;
- v8.0.0 Active restoration identity;
- v7.8.0 immediate rollback restoration identity;
- live authority remained unchanged.

## Result

The retained candidate is internally consistent, reproducible through clean installation, and independently bound to its exact package identity. Package rebuild: `false`.
