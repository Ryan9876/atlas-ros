# Exact Actions Requiring Ryan Authorization

This development transaction authorizes implementation on a dedicated branch only. It does not authorize any production or release action below.

Separate explicit authorization is required for each applicable step:

1. **Exact candidate validation** — authorize a specified branch/commit and validation workflow to build and retain the candidate artifacts and evidence.
2. **Governing records** — authorize creation or activation of the exact Decision and Acceptance Review governing the candidate package.
3. **Exact package publication** — authorize the named commit, retained artifacts, checksums, immutable tag, and GitHub Release without rebuilding.
4. **Additive migration application** — after independent publication readback, authorize only the exact validated reconciliation-ledger migration against the live-resolved data source.
5. **Release authority activation** — after publication and migration readback, authorize the exact Active release, immediate rollback, GitHub authority change, and Notion System State change.
6. **Default-branch merge** — authorize merging the exact reviewed pull request/commit into the governed target branch when required by the approved release sequence.
7. **Production reconciliation apply** — authorize an attended plan by exact plan digest, event IDs, actor, and target provider operations. Approval of the software release does not authorize individual reconciliation transactions.
8. **Rollback execution** — authorize restoration of the live-resolved immediate rollback and related authority records if promotion verification fails after a consequential step.

No authorization may be inferred from planning, code review, branch creation, CI execution, or a prior package/reconciliation approval.
