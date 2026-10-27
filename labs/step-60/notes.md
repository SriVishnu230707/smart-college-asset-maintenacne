# Step 60: Diagnose database maintenance and blocking

Learn: Distinguish VACUUM, ANALYZE, dead tuples, idle transactions, activity views, locks, and query workload statistics.

  Apply: Observe update traffic and a blocked repair; identify the blocking connection and relevant query.

  Prove: Explain the cause from PostgreSQL observations and the effect of long-lived transactions.

Run from PowerShell with Docker ready and the pinned environment installed:

```powershell
.\labs\step-60\verify.ps1 -WriteEvidence
```

The experiment uses synthetic data in an isolated schema. Review python_lab.py before running; predict results and explain each rejection. The independent observer checks committed values, and cleanup requires the exact run marker. Secrets and temporary operational artifacts stay under ignored .local/.

Verified: 16 checks passed in both installed PowerShell versions. Actual blocking and idle transactions are diagnosed through backend IDs, pg_locks and activity views; VACUUM ANALYZE and workload counters are observed.

See [captured evidence](evidence.txt).
