# Atlas ROS v8.1.0 Acceptance Review Template

Status: proposed review; no acceptance is recorded.

## Review subject

Exact retained Atlas ROS v8.1.0 context-aware clarification candidate.

## Acceptance checks

- [ ] Exact candidate commit matches the retained package index.
- [ ] Build count is one.
- [ ] Source and wheel digests match the retained artifacts.
- [ ] SPDX SBOM, source-tree, validation, and clarification-evidence digests match.
- [ ] All required tests pass with required coverage.
- [ ] The LEW fixture produces the approved question and preserves LEW as an entity.
- [ ] Unknown entities are not automatically treated as typos.
- [ ] Every required ambiguity category is covered.
- [ ] The first ambiguous item interrupts before the next batch item.
- [ ] Later independent work remains eligible to continue.
- [ ] Duplicate resolution is ignored and conflicting resolution fails closed.
- [ ] v7.5.2 clarification behavior remains compatible.
- [ ] Provider, Notion, and Todoist writes equal zero.
- [ ] Production schema changes equal zero.
- [ ] Active and immediate rollback restoration pass.
- [ ] Required integrations remain ready.

## Review outcome

`Passed`, `Passed with conditions`, or `Failed`.

A passed review recommends exact-package authorization only. It does not authorize merge, publication, authority activation, or any provider write unless those exact actions are separately authorized.
