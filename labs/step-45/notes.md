# Step 45: Order locks and retry whole transactions

A real reversed-order deadlock is observed; consistent ordering succeeds, and only serialization/deadlock errors trigger bounded full-transaction retries.

Retryable SQLSTATEs are 40001 and 40P01. Each attempt reauthorizes and reruns all reads/writes in a fresh Session; rollback/close precede bounded backoff. Business conflicts, integrity failures, arbitrary SQL errors and ambiguous connection failures are not retried indiscriminately. Completion HTTP now delegates transaction ownership to this retry owner rather than opening a second request transaction. Exhausted retryable database errors return a controlled 503 without SQL parameters. See [explicit locking](https://www.postgresql.org/docs/18/explicit-locking.html).

Predict the successful and rejected outcomes before running the experiment; inspect the emitted SQL/counts and committed observations. Explain why each failure rolls back or is denied.

```powershell
.\labs\step-45\verify.ps1 -WriteEvidence
```

Pass -PythonExecutable for an explicit installed interpreter. Requires Docker and the ignored environment installed from [requirements](../../requirements.txt). No real personal data is used.

Verified 2026-10-25: **18 checks passed in both PowerShell 7 and Windows PowerShell 5.1**. [Evidence](evidence.txt) includes independent SQL observation and exact-run guarded cleanup. [Phase guide](../../docs/WORKFLOW_PHASE_31_50.md).
