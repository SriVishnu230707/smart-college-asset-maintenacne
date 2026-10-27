# Step 51: Use window functions

Learn: Distinguish aggregation from window calculations, partitions, ordering, frames, and rankings.

  Apply: Rank failing assets within each department and compute changes using lag().

  Prove: Choose a tie policy deliberately and explain rows versus groups in a running total.

Run from PowerShell with Docker ready and the pinned environment installed:

```powershell
.\labs\step-51\verify.ps1 -WriteEvidence
```

The experiment uses synthetic data in an isolated schema. Review python_lab.py before running; predict results and explain each rejection. The independent observer checks committed values, and cleanup requires the exact run marker. Secrets and temporary operational artifacts stay under ignored .local/.

Verified: 16 checks passed in both installed PowerShell versions. Dense-rank ties, deterministic row numbering, explicit window frames and lag agree with hand-counted PostgreSQL results.

See [captured evidence](evidence.txt).
