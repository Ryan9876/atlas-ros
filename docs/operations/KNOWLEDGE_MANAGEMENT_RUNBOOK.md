# Knowledge and Management V2 Runbook

Validate locally with:

```bash
ruff check .
python scripts/validate_architecture.py
mypy src
pytest
python scripts/evaluate_knowledge_management.py \
  --dataset benchmarks/knowledge-management-v2.json \
  --output knowledge-management-evidence/report.json
python -m build
```

For `decision_required`, review missing context and decision points; supply authoritative context
and rerun composition. Do not edit a signed package. For unknown versions, cycles, conflicts, or
ambiguous providers, correct declarative registry configuration and repeat all gates. Never bypass
digest verification or convert an unsafe V2 package to V1.

Candidate restoration requires only the checksum-bound source distribution or wheel. Install in a
clean environment, load default registries, run the benchmark evaluator, and verify both package
digests. Production promotion remains a separate Ryan-authorized action.
