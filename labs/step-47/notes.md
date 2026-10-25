# Step 47: Make completion durably idempotent

Duplicate, simultaneous, discarded-response, and rollback-waiting completion requests resolve one durable work-order operation without duplicate stock or audit.

Authorization precedes result disclosure. Ticket and order locks serialize the operation; completed status resolves the frozen outcome before unfinished-state checks, even after closure or rework. Only the owning currently assigned technician or a scoped administrator with completed-work read permission may retrieve it. Administrators still cannot initiate unfinished completion. Unique consumption identities and immutable child snapshots support the durable result; current ticket state, stock, display names and catalog prices are excluded. Two real-backend races prove commit and rollback behavior.

Predict the successful and rejected outcomes before running the experiment; inspect the emitted SQL/counts and committed observations. Explain why each failure rolls back or is denied.

```powershell
.\labs\step-47\verify.ps1 -WriteEvidence
```

Pass -PythonExecutable for an explicit installed interpreter. Requires Docker and the ignored environment installed from [requirements](../../requirements.txt). No real personal data is used.

Verified 2026-10-25: **24 checks passed in both PowerShell 7 and Windows PowerShell 5.1**. [Evidence](evidence.txt) includes independent SQL observation and exact-run guarded cleanup. [Phase guide](../../docs/WORKFLOW_PHASE_31_50.md).
