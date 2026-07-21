# Dependency Security Runbook

## Release gates

A release is blocked unless all of the following are true:

1. `requirements.runtime.lock` exists, contains exact versions, and supplies at least one SHA-256 artifact hash for every direct and transitive runtime requirement.
2. `pip-audit` produces a valid JSON report against at least one current advisory service during the same candidate validation run. PyPI and OSV are both attempted for defense in depth.
3. `scripts/evaluate_dependency_audit.py` confirms that no known vulnerability remains unless a current, explicitly approved entry exists in `security/vulnerability-exceptions.yml` for the exact vulnerability, package, and version.
4. JSON results, stdout/stderr, the evaluation summary, lock file, exception register, workflow outcomes, and SHA-256 checksums are retained as the `dependency-audit-evidence` workflow artifact.

Lookup, DNS, TLS, proxy, malformed-output, and network failures are infrastructure failures, never clean audit results. The evaluator requires at least one parseable current-service JSON report.

## Refreshing the lock

Run `scripts/refresh_dependency_lock.sh` in a network-enabled, controlled CPython 3.12 Linux x86_64 build environment. Review the dependency diff before committing the resulting lock file. The committed lock is validated independently by `scripts/validate_dependency_lock.py`.

## Exceptions

The default action is block. Exceptions require a vulnerability identifier, exact package and version, documented business justification, compensating controls, accountable owner and approver, approval date, and an expiration no more than 30 days later. Expired or malformed exceptions fail CI. An exception applies only to the exact `(vulnerability ID, package, affected version)` tuple.
