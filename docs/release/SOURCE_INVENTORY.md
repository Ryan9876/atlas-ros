# Source inventory and migration matrix

| Artifact | Current authority | Target form | Action | Normative |
|---|---|---|---|---|
| Release Index | Drive | Markdown | Read-only authority input | Yes |
| Active Manifest | Drive | Markdown + parsed adapter model | Dynamic authority input | Yes |
| Published workspace | Drive | Markdown | Policy/reference compatibility input | Yes |
| W01 runbook | Drive | Markdown + Python W01 | Retain rationale; implement behavior | Yes |
| Legacy shell capture/sync/health scripts | historical package unavailable | Compatibility input | Import when retrieved; Python replacement provided | No |
| Finite policy values | document/prompt | YAML | Centralize and generate docs | Yes |
| Runtime retry/outbox | local | SQLite | Non-authoritative runtime | No |
| Candidate source/tests/schemas | Git | Python/JSON Schema | Candidate release snapshot | Candidate |

