# Step 54: Read execution plans

Learn: Use EXPLAIN (ANALYZE, BUFFERS), estimates versus actuals, loops, scans, joins, sorts, and result width.

  Apply: Capture a representative slow ticket/report SELECT on a larger, unevenly distributed fixture.

  Prove: Explain where time/work is spent and identify evidence rather than assuming every sequential scan is bad.

Run from PowerShell with Docker ready and the pinned environment installed:

```powershell
.\labs\step-54\verify.ps1 -WriteEvidence
```

The experiment uses synthetic data in an isolated schema. Review python_lab.py before running; predict results and explain each rejection. The independent observer checks committed values, and cleanup requires the exact run marker. Secrets and temporary operational artifacts stay under ignored .local/.

Verified: 16 checks passed in both installed PowerShell versions. Captured JSON plans demonstrate actual cardinality, scans, sorts, loops, buffer observations and explicit workload assumptions.

See [captured evidence](evidence.txt).
