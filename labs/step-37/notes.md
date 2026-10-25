# Step 37: Authorize comments and private attachments

Authored append-only comments and separate ticket/work-order attachments follow their parent permissions; upload failures compensate staged bytes.

Bytes are private local objects with random validated keys, size limits and SHA-256 verification; downloads are authenticated and force attachment disposition. The database records ownership, uploader, filename, media type, size and digest. An upload writes bytes first, verifies them, then commits metadata and audit together. A database failure removes its own staged object; a process crash may leave an orphan, handled separately with an age grace period and referenced-key scan. Garbage collection must run in a maintenance window or with uploads paused; it is not a distributed storage transaction. Completed-proof protection is strengthened in Step 39.

Predict the successful and rejected outcomes before running the experiment; inspect the emitted SQL/counts and committed observations. Explain why each failure rolls back or is denied.

```powershell
.\labs\step-37\verify.ps1 -WriteEvidence
```

Pass -PythonExecutable for an explicit installed interpreter. Requires Docker and the ignored environment installed from [requirements](../../requirements.txt). No real personal data is used.

Verified 2026-10-25: **22 checks passed in both PowerShell 7 and Windows PowerShell 5.1**. [Evidence](evidence.txt) includes independent SQL observation and exact-run guarded cleanup. [Phase guide](../../docs/WORKFLOW_PHASE_31_50.md).
