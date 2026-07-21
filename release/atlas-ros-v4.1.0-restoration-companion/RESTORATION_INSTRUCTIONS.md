# Restoration Instructions

1. Verify the live Release Index still identifies v4.1.0 as Active and v4.0.1 as immutable rollback.
2. Verify this package with `sha256sum -c CHECKSUMS.sha256`.
3. Restore policy documents only to a separate recovery workspace; do not overwrite the Active release.
4. Reconcile System State and all Notion authorities by live read before enabling attended operations.
5. Do not reconstruct or deploy unpublished legacy executable source from this package. Use v4.0.1 rollback or the approved Python candidate as applicable.
