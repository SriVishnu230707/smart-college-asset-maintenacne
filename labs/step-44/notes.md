# Step 44: Prove the parent and row-lock protocol

Completion can lock sorted stock rows explicitly, while concurrent edited and newly inserted part lines wait for parent protection and reject completed work.

Every service child edit locks/rechecks ticket then order, including proof changes and draft deletion. Completion holds those parents before selecting line membership and sorted parts. PostgreSQL blocking is observed for both an existing-line edit and a new-line insert; neither bypasses the frozen set. A direct SQL completed-child insert is independently rejected by the reviewed trigger. The application default remains guarded arithmetic; the internal stock_strategy option compares equivalent row-lock behavior and is not client-selectable.

Predict the successful and rejected outcomes before running the experiment; inspect the emitted SQL/counts and committed observations. Explain why each failure rolls back or is denied.

```powershell
.\labs\step-44\verify.ps1 -WriteEvidence
```

Pass -PythonExecutable for an explicit installed interpreter. Requires Docker and the ignored environment installed from [requirements](../../requirements.txt). No real personal data is used.

Verified 2026-10-25: **16 checks passed in both PowerShell 7 and Windows PowerShell 5.1**. [Evidence](evidence.txt) includes independent SQL observation and exact-run guarded cleanup. [Phase guide](../../docs/WORKFLOW_PHASE_31_50.md).
