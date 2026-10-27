# Step 55: Design workload-specific indexes

Learn: Compare B-tree, composite column order, partial predicates, expression indexes, and covering indexes.

  Apply: Evaluate indexes for the department's recent active-ticket queue and common FK lookups.

  Prove: Show useful before/after plans, account for write/storage cost, and reject a redundant candidate.

Run from PowerShell with Docker ready and the pinned environment installed:

```powershell
.\labs\step-55\verify.ps1 -WriteEvidence
```

The experiment uses synthetic data in an isolated schema. Review python_lab.py before running; predict results and explain each rejection. The independent observer checks committed values, and cleanup requires the exact run marker. Secrets and temporary operational artifacts stay under ignored .local/.

Verified: 18 checks passed in both installed PowerShell versions. Measured composite, partial covering and expression indexes preserve results and expose storage, ordering, predicate and redundancy tradeoffs.

See [captured evidence](evidence.txt).
