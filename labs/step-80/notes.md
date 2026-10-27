# Step 80: Independent feature and reference audit

Learn: Practice choosing a design, finding exact API options, identifying unsupported assumptions, and updating dependencies. Prerequisite: 64 and relevant extension gates.

  Apply: Design a stock-reservation or preventive-maintenance feature from a blank page; maintain a reference coverage ledger.

  Prove: Produce requirements, schema/migration, SQL, ORM, failure tests, concurrency evidence, plans, and recovery considerations without copying the original implementation.

Run from PowerShell with Docker ready and the pinned environment installed:

```powershell
.\labs\step-80\verify.ps1 -WriteEvidence
```

The experiment uses synthetic data in an isolated schema. Review python_lab.py before running; predict results and explain each rejection. The independent observer checks committed values, and cleanup requires the exact run marker. Secrets and temporary operational artifacts stay under ignored .local/.

Verified: 33 checks passed in both installed PowerShell versions. Independent preventive scheduling includes explicit migration, scoped API, durable request keys, versioned cancellation, actual overlap contention, audit, query plan and real restore.

See [captured evidence](evidence.txt).
