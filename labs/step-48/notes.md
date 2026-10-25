# Step 48: Reject stale edits optimistically

Ticket mapper versions and required HTTP expected versions reject stale report/priority edits; explicit Core predicates demonstrate the bulk-write boundary.

Two independently loaded entities prove ORM StaleDataError and preservation of the winner. Core DML without a version predicate bypasses mapper protection, so that counterexample is rolled back; a qualified predicate matches zero stale rows. The API returns current versions, requires positive expected_version on protected edits, and emits no success audit for rejected changes. Earlier permission/audit HTTP fixtures now supply the new transport field while preserving their original assertions. A reviewed migration backfills version 1 for existing rows. See [SQLAlchemy version counters](https://docs.sqlalchemy.org/en/21/orm/versioning.html).

Predict the successful and rejected outcomes before running the experiment; inspect the emitted SQL/counts and committed observations. Explain why each failure rolls back or is denied.

```powershell
.\labs\step-48\verify.ps1 -WriteEvidence
```

Pass -PythonExecutable for an explicit installed interpreter. Requires Docker and the ignored environment installed from [requirements](../../requirements.txt). No real personal data is used.

Verified 2026-10-25: **20 checks passed in both PowerShell 7 and Windows PowerShell 5.1**. [Evidence](evidence.txt) includes independent SQL observation and exact-run guarded cleanup. [Phase guide](../../docs/WORKFLOW_PHASE_31_50.md).
