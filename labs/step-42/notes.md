# Step 42: Observe READ COMMITTED visibility

Two real backend connections prove committed statement snapshots, own-write visibility, rollback, and the separate behavior of ORM identity-map caching.

An uncommitted write is invisible to the other reader. After its commit, a later statement in an already-open READ COMMITTED transaction sees the new row version. An existing Python entity can remain stale until refresh even though a column projection is fresh. No ORM cache is treated as a PostgreSQL isolation snapshot. Every explicit transaction is ended before independent observation. See [PostgreSQL isolation](https://www.postgresql.org/docs/18/transaction-iso.html).

Predict the successful and rejected outcomes before running the experiment; inspect the emitted SQL/counts and committed observations. Explain why each failure rolls back or is denied.

```powershell
.\labs\step-42\verify.ps1 -WriteEvidence
```

Pass -PythonExecutable for an explicit installed interpreter. Requires Docker and the ignored environment installed from [requirements](../../requirements.txt). No real personal data is used.

Verified 2026-10-25: **21 checks passed in both PowerShell 7 and Windows PowerShell 5.1**. [Evidence](evidence.txt) includes independent SQL observation and exact-run guarded cleanup. [Phase guide](../../docs/WORKFLOW_PHASE_31_50.md).
