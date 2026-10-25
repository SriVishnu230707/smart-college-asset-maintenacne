# Step 41: Prove completion rollback at fault boundaries

Four injected failures and a real unique-constraint failure leave all seven participating tables unchanged, as read independently after rollback.

The private test-only checkpoint seam is unavailable through HTTP. Faults fire after balance/price flush, after ledger insertion, before completion, and after audit insertion. PostgreSQL fingerprints retain exact numeric JSON text rather than float conversions. A multi-part shortage consumes nothing; a new authorized correction permits a fresh successful attempt. The transaction context propagates errors, rolls back, closes the Session, and returns its checkout.

Predict the successful and rejected outcomes before running the experiment; inspect the emitted SQL/counts and committed observations. Explain why each failure rolls back or is denied.

```powershell
.\labs\step-41\verify.ps1 -WriteEvidence
```

Pass -PythonExecutable for an explicit installed interpreter. Requires Docker and the ignored environment installed from [requirements](../../requirements.txt). No real personal data is used.

Verified 2026-10-25: **23 checks passed in both PowerShell 7 and Windows PowerShell 5.1**. [Evidence](evidence.txt) includes independent SQL observation and exact-run guarded cleanup. [Phase guide](../../docs/WORKFLOW_PHASE_31_50.md).
