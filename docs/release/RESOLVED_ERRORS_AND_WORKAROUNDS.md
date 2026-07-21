# Resolved errors and workarounds

| Issue | Resolution | Residual risk |
|---|---|---|
| Active package exposes only three readable documents | Treated as an inherited package limitation; candidate has local inventory/checksum tooling | Full active artifact checksum validation remains unavailable |
| Connector proxy cannot upload raw ZIP | Built candidate package locally; no Drive upload attempted | Manual authorized transport remains required |
| Managed environment corrupts virtualenv symlinks | Used base Python and isolated runtime directory for smoke validation | Clean-install CI remains pending network-capable runner |
| Package registry unavailable through proxy | Retained minimal dependencies and performed stdlib/Pydantic smoke tests | Full pytest/lint/mypy/security suite awaits dependency-capable runner |
| Home directory read-only | `ATLAS_RUNTIME_DIR` supports controlled runtime location | Deployment must set runtime path where home is restricted |

