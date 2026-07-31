# Atlas ROS v8.2.0 Exact Actions Requiring Ryan Authorization

Preparation and validation of the candidate branch and retained build artifacts do not authorize production promotion.

Separate explicit authorization is required for:

1. **Exact package acceptance:** accept the specified source commit, candidate artifact ID, source/wheel/SBOM/evidence hashes, test result, coverage, and rollback evidence.
2. **Governing records:** create or activate the exact Decision and Acceptance Review for that package.
3. **Default-branch integration:** merge the exact reviewed implementation PR when required by the approved release sequence.
4. **Immutable publication:** publish the exact retained artifacts under the exact tag and GitHub Release without rebuilding.
5. **Independent publication verification:** run and accept read-only tag, asset, checksum, installation, and rollback verification.
6. **No-migration acceptance:** accept the verified conclusion that production Notion schema changes are zero.
7. **Authority activation:** activate the exact release and live-resolved immediate rollback in GitHub and Notion only after publication verification.
8. **Production reconciliation apply:** authorize each attended reconciliation transaction by exact plan digest, event IDs, actor, and provider operations. Release approval does not authorize an individual apply.
9. **Rollback execution:** restore the live-resolved immediate rollback and authority records if a consequential promotion step fails.

No authorization is inferred from implementation, CI, code review, artifact retention, or previous release/reconciliation approvals.
