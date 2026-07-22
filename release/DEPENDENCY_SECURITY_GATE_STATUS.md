# Atlas ROS v4.5.2 Dependency Security Gate Status

Date: 2026-07-21
Candidate: Atlas ROS v4.5.2

## Result

PASS in GitHub Actions for commit `85f780e` as observed by the release owner: the complete CI workflow returned a green result. The workflow validates the deterministic lock and exception policy, audits against PyPI and OSV with at least one current advisory-service result required, blocks unapproved findings, and retains checksummed evidence for 90 days.

## Controls

- Exact direct and transitive runtime versions are committed in `requirements.runtime.lock` with artifact hashes.
- `security/vulnerability-exceptions.yml` defaults to block and contains no standing exceptions.
- Exceptions, when authorized, are constrained to an exact vulnerability/package/version tuple and expire within 30 days.
- CI attempts both PyPI and OSV and rejects every unapproved finding.
- Network, DNS, TLS, proxy, malformed-output, and lookup failures are treated as blocking unless the alternate current advisory service produces valid evidence.
- Audit reports, logs, policy, lock, workflow outcomes, and SHA-256 checksums are retained as the `dependency-audit-evidence` artifact for 90 days.

The release owner must preserve the successful workflow run and its artifact as release evidence.
