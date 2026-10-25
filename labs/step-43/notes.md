# Step 43: Use guarded arithmetic stock updates

Completion uses stock=stock-quantity with stock>=quantity and RETURNING; two technicians on independent backends compete for one unit and only one commits.

A positive-quantity guard is enforced before SQL. RETURNING captures the price while the arithmetic update owns the stock-row lock. PostgreSQL blocking is observed with pg_blocking_pids, then the winner is released; the waiter rechecks the predicate after the commit. The losing complete transaction leaves its order unfinished and creates no consumption or audit. Sorted part IDs, parent locks, exact cost validation and rollback remain part of the overall protocol. The contention harness uses an explicitly separate NullPool test Engine so the one-slot learning pool cannot accidentally serialize the test before PostgreSQL does.

Predict the successful and rejected outcomes before running the experiment; inspect the emitted SQL/counts and committed observations. Explain why each failure rolls back or is denied.

```powershell
.\labs\step-43\verify.ps1 -WriteEvidence
```

Pass -PythonExecutable for an explicit installed interpreter. Requires Docker and the ignored environment installed from [requirements](../../requirements.txt). No real personal data is used.

Verified 2026-10-25: **18 checks passed in both PowerShell 7 and Windows PowerShell 5.1**. [Evidence](evidence.txt) includes independent SQL observation and exact-run guarded cleanup. [Phase guide](../../docs/WORKFLOW_PHASE_31_50.md).
