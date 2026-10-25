# Step 39: Manage drafts and protect repair history

Assigned technicians manage one active order, consolidated part lines and exact labor estimates; drafts reserve nothing and completed facts reject edits.

Ticket/order locks protect create/start/edit/discard and child changes. Discarding a draft removes its metadata and leaves bytes for age-gated orphan collection. Stored estimates become final snapshots at the successful completion introduced in Step 40. This lesson uses a synthetic completed fixture to isolate price-history and immutability proofs. Reviewed database triggers protect completed parents and both old/new parents of child moves; audit, inventory and comment history reject UPDATE/DELETE. Direct SQL proofs bypass the ORM. The study installs the exact frozen revision guard, while Alembic owns the application installation.

Predict the successful and rejected outcomes before running the experiment; inspect the emitted SQL/counts and committed observations. Explain why each failure rolls back or is denied.

```powershell
.\labs\step-39\verify.ps1 -WriteEvidence
```

Pass -PythonExecutable for an explicit installed interpreter. Requires Docker and the ignored environment installed from [requirements](../../requirements.txt). No real personal data is used.

Verified 2026-10-25: **23 checks passed in both PowerShell 7 and Windows PowerShell 5.1**. [Evidence](evidence.txt) includes independent SQL observation and exact-run guarded cleanup. [Phase guide](../../docs/WORKFLOW_PHASE_31_50.md).
