# Step 35: Enforce explicit ticket transitions

Administrative transitions validate eligible assignees, rejection reasons, rework and verification conditions, and terminal-state conflicts.

Ticket-row locks serialize these administrative commands. Approval and assignment are one operation. Reassignment rejects existing orders; only active same-department technicians qualify. Verification/rework require completed work and no active order. Repair start and completion are intentionally work-order commands, implemented in Steps 39-40; this lesson uses explicit synthetic repair-state fixtures to test the administrator edges. A reviewed revision preserves separate verification and rework notes.

Predict the successful and rejected outcomes before running the experiment; inspect the emitted SQL/counts and committed observations. Explain why each failure rolls back or is denied.

```powershell
.\labs\step-35\verify.ps1 -WriteEvidence
```

Pass -PythonExecutable for an explicit installed interpreter. Requires Docker and the ignored environment installed from [requirements](../../requirements.txt). No real personal data is used.

Verified 2026-10-25: **23 checks passed in both PowerShell 7 and Windows PowerShell 5.1**. [Evidence](evidence.txt) includes independent SQL observation and exact-run guarded cleanup. [Phase guide](../../docs/WORKFLOW_PHASE_31_50.md).
