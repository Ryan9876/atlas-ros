# Atlas ROS v4.5.2 Dependency Security Gate Status

Date: 2026-07-21
Candidate: Atlas ROS v4.5.2
Production authority changed: No

## Result

The dependency security implementation is complete, deterministic, and locally validated. Final current-service execution is blocked by the validation environment's inability to resolve either `pypi.org` or `api.osv.dev` and by the absence of an authoritative Atlas ROS executable-source repository among the connected GitHub repositories.

## Gate status

| Gate | Status | Evidence |
|---|---|---|
| Exact dependency lock with hashes | PASS | `requirements.runtime.lock`; `scripts/validate_dependency_lock.py` |
| Successful current-service `pip-audit` | BLOCKED | PyPI and OSV attempts both failed DNS resolution; stderr retained under `release/evidence/dependency-audit-blocked/` |
| Zero unapproved known vulnerabilities | BLOCKED | Default-deny exception policy and evaluator are complete, but a current advisory report is required before this gate can pass |
| JSON evidence retained | IMPLEMENTED / PENDING RUN | CI retains both service reports, logs, evaluation summary, policy, lock, workflow outcomes, and checksums for 90 days; no valid JSON can be produced without advisory-service connectivity |

## Implemented controls

- Exact direct and transitive runtime versions are committed in `requirements.runtime.lock`.
- Every logical requirement has at least one SHA-256 artifact hash.
- `security/vulnerability-exceptions.yml` defaults to block and currently contains no exceptions.
- Exceptions are constrained to an exact vulnerability/package/version tuple and expire within 30 days.
- CI attempts both PyPI and OSV, requires at least one valid current-service JSON report, and rejects every unapproved finding.
- CI retains complete audit evidence with SHA-256 checksums.
- Network, DNS, TLS, proxy, malformed-output, and lookup failures are treated as blocking infrastructure failures rather than clean scans.

## Hard blocker and required decision

Choose one controlled execution target:

1. Connect or identify the authoritative Atlas ROS executable-source GitHub repository so the included workflow can run on a GitHub-hosted runner; or
2. Run the included workflow or equivalent commands on another approved CPython 3.12 Linux x86_64 runner with outbound HTTPS/DNS access to PyPI or OSV and return the generated `dependency-audit-evidence` artifact.

The connected `ros-executive-console` repository is not an acceptable substitute because its documented role is presentation/observability and it explicitly does not replace ROS authority sources.
