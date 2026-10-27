# Step 56: Measure realistic workloads

Learn: Use deterministic correctness fixtures, skewed larger seeds, ANALYZE, query budgets, and repeated measurements.

  Apply: Keep a benchmark note with query parameters, data distribution, plans, and observation conditions.

  Prove: Explain how cardinality estimates and skew can change an index decision; avoid tuning from a tiny fixture.

Run from PowerShell with Docker ready and the pinned environment installed:

```powershell
.\labs\step-56\verify.ps1 -WriteEvidence
```

The experiment uses synthetic data in an isolated schema. Review python_lab.py before running; predict results and explain each rejection. The independent observer checks committed values, and cleanup requires the exact run marker. Secrets and temporary operational artifacts stay under ignored .local/.

Verified: 16 checks passed in both installed PowerShell versions. Skewed 100000-row fixtures, ANALYZE statistics and repeated plans justify selective indexing and common-row sequential scans.

See [captured evidence](evidence.txt).
