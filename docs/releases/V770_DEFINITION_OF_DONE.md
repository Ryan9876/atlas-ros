# Atlas ROS v7.7.0 Definition of Done

The candidate is complete only when all items below are evidenced for one frozen commit.

## Implementation

- [ ] Typed state machine contains every required state and no terminal outgoing transition.
- [ ] Operation-scoped capability profile is active before the first provider call.
- [ ] Exact capability and target are checked before every provider invocation.
- [ ] Clean cold path executes exactly six ordered external reads.
- [ ] Clean warm path validates authenticated cached immutable documents and executes exactly four external reads.
- [ ] Cache rejection permits one deterministic cold fallback without exploratory reads.
- [ ] One bounded transient retry is implemented; permanent and integrity failures are not retried.
- [ ] Terminal lock rejects every later initialization-scoped call before provider invocation.
- [ ] Quick Initialization and Full Validation are separate operations.
- [ ] Intent memory, user profile, communication policy, and playbooks are isolated from Quick Initialization.

## Receipt and compatibility

- [ ] Receipt schema is versioned and accepted v1 fields are preserved.
- [ ] Receipt contains operation, identity, agreement, trace, budget, retry, rejection, lock, timing, and integration evidence.
- [ ] `provider_writes`, `google_drive_reads`, and `post_terminal_executed_calls` are all zero.
- [ ] CLI identity and fail-closed behavior remain compatible.
- [ ] Existing v7.1.1 initialization tests pass unchanged except additive schema expectations where required.

## Validation

- [ ] Ruff passes.
- [ ] Strict Mypy passes.
- [ ] Architecture and development-tool boundaries pass.
- [ ] Complete test suite and branch-coverage threshold pass.
- [ ] Adversarial and failure-injection tests prove denied calls do not invoke providers.
- [ ] Secret scan has zero findings.
- [ ] PyPI and OSV dependency audits have no unaccepted vulnerabilities.
- [ ] Source and wheel clean-install successfully and report v7.7.0.
- [ ] Source manifest, SPDX SBOM, checksums, and nested checksums verify.
- [ ] Build count equals one.
- [ ] Active v7.6.1 and rollback v7.6.0 artifacts restore and install cleanly.

## Candidate checkpoint

- [ ] One implementation branch and one draft PR exist.
- [ ] Exact source commit is frozen.
- [ ] One full non-publishing candidate workflow passes for that commit.
- [ ] Retained artifact ID and digest are known.
- [ ] Authorization block includes all required identities, digests, read counts, terminal-lock proof, zero post-terminal calls, workflow run, and elapsed time.
- [ ] Publication and production activation remain false.
- [ ] Candidate stops for Ryan’s separate exact-package authorization.
