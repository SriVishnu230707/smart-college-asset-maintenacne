# Step 33: Expose the thin HTTP boundary

FastAPI reads validate requests, resolve opaque bearer identity, authorize database scope, and serialize values inside one operation transaction.

Request validation returns 422, missing/invalid credentials 401, inactive actors 403, absent scoped rows 404, domain filter errors 400, and integrity conflicts 409. Request Sessions always close and response values need no database work afterward. Opaque token digests and aware expiry live in an ignored file; tokens are provisioned out of band for this local example. No client role or actor ID is trusted. See [API operation](API.md) and [FastAPI security](https://fastapi.tiangolo.com/tutorial/security/first-steps/).

Predict the successful and rejected outcomes before running the experiment; inspect the emitted SQL/counts and committed observations. Explain why each failure rolls back or is denied.

```powershell
.\labs\step-33\verify.ps1 -WriteEvidence
```

Pass -PythonExecutable for an explicit installed interpreter. Requires Docker and the ignored environment installed from [requirements](../../requirements.txt). No real personal data is used.

Verified 2026-10-25: **23 checks passed in both PowerShell 7 and Windows PowerShell 5.1**. [Evidence](evidence.txt) includes independent SQL observation and exact-run guarded cleanup. [Phase guide](../../docs/WORKFLOW_PHASE_31_50.md).
