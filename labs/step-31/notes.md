# Step 31: Measure lazy relationship queries

A three-ticket page records its 1+N comment SELECTs and detached serialization failure.

The comment table has a reviewed migration and RESTRICT history references. Loading the ticket list does not load its collections; each first comments access issues SQL, including the empty collection. Count statements with fresh Sessions so the identity map cannot hide round trips. Step 32 optimizes this same fixture. See [relationship loading](https://docs.sqlalchemy.org/en/21/orm/queryguide/relationships.html).

Predict the successful and rejected outcomes before running the experiment; inspect the emitted SQL/counts and committed observations. Explain why each failure rolls back or is denied.

```powershell
.\labs\step-31\verify.ps1 -WriteEvidence
```

Pass -PythonExecutable for an explicit installed interpreter. Requires Docker and the ignored environment installed from [requirements](../../requirements.txt). No real personal data is used.

Verified 2026-10-25: **18 checks passed in both PowerShell 7 and Windows PowerShell 5.1**. [Evidence](evidence.txt) includes independent SQL observation and exact-run guarded cleanup. [Phase guide](../../docs/WORKFLOW_PHASE_31_50.md).
