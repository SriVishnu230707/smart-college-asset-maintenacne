# Step 46: Compare stronger transaction isolation

Repeatable Read retains a snapshot and can abort stale row updates, while Serializable rejects a demonstrated two-row write-skew history.

The availability predicate is a clearly isolated teaching fixture encoded in asset location, not a new application requirement. Both disjoint Repeatable Read writes commit; Serializable rejects one with 40001, requiring full transaction retry. SQLAlchemy isolation configuration is set before autobegin and resets on pool return. The project keeps READ COMMITTED with explicit ticket/order/stock protection, guarded arithmetic and bounded deadlock/serialization retries; stronger isolation is not treated as a replacement for state, authorization or idempotency rules. See [PostgreSQL isolation](https://www.postgresql.org/docs/18/transaction-iso.html).

Predict the successful and rejected outcomes before running the experiment; inspect the emitted SQL/counts and committed observations. Explain why each failure rolls back or is denied.

```powershell
.\labs\step-46\verify.ps1 -WriteEvidence
```

Pass -PythonExecutable for an explicit installed interpreter. Requires Docker and the ignored environment installed from [requirements](../../requirements.txt). No real personal data is used.

Verified 2026-10-25: **19 checks passed in both PowerShell 7 and Windows PowerShell 5.1**. [Evidence](evidence.txt) includes independent SQL observation and exact-run guarded cleanup. [Phase guide](../../docs/WORKFLOW_PHASE_31_50.md).
