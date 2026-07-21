# Install and validate Atlas ROS v4.2.0-rc.7 on macOS

This candidate is inactive and the connectivity check is read-only. It does not promote a
release, create Notion pages, or create Todoist tasks.

1. Download and unzip `atlas-ros-4.2.0rc7-candidate.zip`.
2. In Terminal, change into the unzipped `atlas-ros` directory.
3. Create a local environment: `python3.12 -m venv .venv`.
4. Activate it: `source .venv/bin/activate`.
5. Install the candidate: `python -m pip install .`.
6. Confirm the local CLI is installed: `atlas status`.
7. Run `atlas connectivity --keychain`.

Expected result:

```json
{"valid": true, "writes": false, "notion_identity_confirmed": true, "todoist_project_count": 1}
```

The Todoist project count varies. Do not share tokens or full command output if it contains an
unexpected error. To exit the local environment, run `deactivate`.

## v4.4 shared W04 state

Configure the shared state ledger so CLI and Atlas ChatGPT use the same replay checkpoint:

```bash
export ATLAS_RECONCILIATION_STATE_DATA_SOURCE_ID="afbb753c-3112-4784-9165-f786b503d1f7"
```

Persist this alongside the other Atlas data-source environment variables. The local SQLite ledger remains a recovery fallback only when this variable is absent.
