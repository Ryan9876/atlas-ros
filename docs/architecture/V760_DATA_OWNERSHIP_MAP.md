# Atlas ROS v7.6.0 Data Ownership Map

| Data | Authoritative owner | v7.6.0 use | Write boundary |
|---|---|---|---|
| Release identity, package, manifest, rollback | GitHub authority and immutable release | Read and bind | Release-controlled only |
| Dynamic production state | Notion System State | Read and later update after exact authorization | Readback required |
| Integration status and permission state | Notion Integration Inventory plus live connector reads | Read and verify | No scope change |
| Operational captures and routing state | Universal Inbox | Read operational references only | Not a historical learning store |
| Existing acceptance and implementation reviews | Review Records | Read as review evidence; not intent evidence by default | No reinterpretation |
| Governed intent evidence | Proposed Governed Intent Evidence data source | Sole durable evidence owner | Additive schema and exact migration authorization required |
| Active inference snapshot | Proposed Active Intent Memory Index data source | Deterministic active/excluded index | Derived records only after schema authorization |
| Corrections, retirement, forgetting receipts | Proposed Intent User Control Receipts data source | User-control audit owner | Exact attended action and readback required |
| Todoist tasks | Todoist Work and Personal | No use in this feature | Writes prohibited during implementation and migration dry run |
| Google Drive history | Google Drive | Not read for authority or migration | Optional and non-authoritative |

Immutable predecessor records are referenced, never rewritten. Public release artifacts contain digests and minimized fixtures, not raw sensitive intent text.
