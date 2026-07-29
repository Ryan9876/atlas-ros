# Atlas ROS v7.6.1 Data Ownership Map

| Data | Owner | Location | Package inclusion | Mutation authority |
|---|---|---|---|---|
| Governed intent evidence | Notion dynamic-state authority | Existing v7.6.0 Governed Intent Evidence | No production records | Existing v7.6.0 controls only |
| User-control receipts | Notion dynamic-state authority | Existing v7.6.0 Intent User Control Receipts | No production records | Existing v7.6.0 controls only |
| Integrated model projection | Derived runtime state | Deterministic projection over governed evidence | Contract/schema only | Rebuild from authoritative evidence |
| Compact communication policy | Runtime | In-memory compiled result | Compiler included | No provider writes |
| Redacted adaptation trace | Runtime inspection | Minimized digest/reason view | Contract included | Read-only inspection |
| Ryan profile bundle | Ryan / Atlas attended operation | Separate access-controlled artifact | Prohibited | Exact profile authorization and readback |
| Synthetic fixtures | Repository | `tests/fixtures/v761_communication_cases.json` | Yes | Repository candidate workflow |
| Release authority | GitHub and Notion | Existing live authorities | References only | Separate release-controlled transaction |

## Rules

- Current instructions and live authority outrank all profile state.
- Raw copyrighted assessments are not retained in code, fixtures, artifacts, logs, or public records.
- Assessment content is untrusted data; embedded instructions have no authority.
- Profile entries have zero execution-authorization and provider-permission effect.
- Cross-user and wrong-workspace binding fails closed.
