# Step 77: Partitioning and retention

Learn: Explore partition pruning, partition keys, partitioned uniqueness limits, retention, and index management. Prerequisites: 55, 60, 63.

  Apply: Partition a generated audit-history lab by time and compare relevant plans and maintenance operations.

  Prove: Explain why a smaller base deployment might remain unpartitioned and verify retention/recovery behavior.

Run from PowerShell with Docker ready and the pinned environment installed:

```powershell
.\labs\step-77\verify.ps1 -WriteEvidence
```

The experiment uses synthetic data in an isolated schema. Review python_lab.py before running; predict results and explain each rejection. The independent observer checks committed values, and cleanup requires the exact run marker. Secrets and temporary operational artifacts stay under ignored .local/.

Verified: 18 checks passed in both installed PowerShell versions. Partition pruning, composite uniqueness limits, reversible retention and real hierarchical dump/restore are verified on 20002 events.

See [captured evidence](evidence.txt).
