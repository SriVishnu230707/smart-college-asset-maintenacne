# Step 32: Bound relationship loading

The fixed ticket page uses two SELECTs, while joined loading, raiseload, deferred columns, and collection paging have explicit proofs.

Select-in loading avoids joined row multiplication. Joined collection results require unique(); this deduplicates ORM parents rather than reducing SQL rows. Response DTOs are constructed before Session close. Parent limits do not bound child collection size, so large comment histories use the separately scoped comment_page query. See [loader options](https://docs.sqlalchemy.org/en/21/orm/queryguide/relationships.html) and [column loading](https://docs.sqlalchemy.org/en/21/orm/queryguide/columns.html).

Predict the successful and rejected outcomes before running the experiment; inspect the emitted SQL/counts and committed observations. Explain why each failure rolls back or is denied.

```powershell
.\labs\step-32\verify.ps1 -WriteEvidence
```

Pass -PythonExecutable for an explicit installed interpreter. Requires Docker and the ignored environment installed from [requirements](../../requirements.txt). No real personal data is used.

Verified 2026-10-25: **21 checks passed in both PowerShell 7 and Windows PowerShell 5.1**. [Evidence](evidence.txt) includes independent SQL observation and exact-run guarded cleanup. [Phase guide](../../docs/WORKFLOW_PHASE_31_50.md).
