# Step 36: Commit business audit with changes

Every implemented ticket mutation records actor, target, request, department, time, and change details inside its owning transaction.

A fault injected after the business flush but before audit persistence rolls back both; a fresh independent connection verifies the result. Failed attempts are operational failures, not successful business history. Administrator audit reads enforce ticket/department scope. No history edit/delete endpoint exists; database append-only history protection is added with the completed-work guards in Step 39.

Predict the successful and rejected outcomes before running the experiment; inspect the emitted SQL/counts and committed observations. Explain why each failure rolls back or is denied.

```powershell
.\labs\step-36\verify.ps1 -WriteEvidence
```

Pass -PythonExecutable for an explicit installed interpreter. Requires Docker and the ignored environment installed from [requirements](../../requirements.txt). No real personal data is used.

Verified 2026-10-25: **18 checks passed in both PowerShell 7 and Windows PowerShell 5.1**. [Evidence](evidence.txt) includes independent SQL observation and exact-run guarded cleanup. [Phase guide](../../docs/WORKFLOW_PHASE_31_50.md).
