# Step 34: Enforce resource-scoped permissions

Direct API requests prove own-ticket, assigned-technician, department-admin, and Super Admin boundaries for reads and mutations.

Creation derives reporter and department on the server. Original text requires the current-department reporter and open state; triage requires an in-scope administrator. Historical read access after transfer never grants mutation access. Archived departments and retired assets reject new reports. The read policy reuses server-derived scope; unauthorized details conceal resource existence. Database roles are distinct from these application roles.

Predict the successful and rejected outcomes before running the experiment; inspect the emitted SQL/counts and committed observations. Explain why each failure rolls back or is denied.

```powershell
.\labs\step-34\verify.ps1 -WriteEvidence
```

Pass -PythonExecutable for an explicit installed interpreter. Requires Docker and the ignored environment installed from [requirements](../../requirements.txt). No real personal data is used.

Verified 2026-10-25: **25 checks passed in both PowerShell 7 and Windows PowerShell 5.1**. [Evidence](evidence.txt) includes independent SQL observation and exact-run guarded cleanup. [Phase guide](../../docs/WORKFLOW_PHASE_31_50.md).
