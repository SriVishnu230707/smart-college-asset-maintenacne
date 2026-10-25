# Step 49: Aggregate reports before child joins

Hand-counted cost and failure reports avoid parts/comments fan-out, exclude unfinished estimates, and retain recorded department history.

Parts first aggregate to one row per work order, then completed work to one row per department. Comments and proof never join those money aggregates. The naive fixture totals 137.00 incorrectly; raw SQL and SQLAlchemy correctly return 52.00. SUM(DISTINCT amount) is not a repair for fan-out because legitimate equal amounts may belong to different rows. Zero-cost completed repairs count, empty departments retain zero totals, and failures count tickets at department/asset grain. The transfer fixture closes every ticket before moving its asset and proves historical costs remain with ticket.department_id. Report APIs permit only scoped department administrators or Super Admin.

Predict the successful and rejected outcomes before running the experiment; inspect the emitted SQL/counts and committed observations. Explain why each failure rolls back or is denied.

```powershell
.\labs\step-49\verify.ps1 -WriteEvidence
```

Pass -PythonExecutable for an explicit installed interpreter. Requires Docker and the ignored environment installed from [requirements](../../requirements.txt). No real personal data is used.

Verified 2026-10-25: **19 checks passed in both PowerShell 7 and Windows PowerShell 5.1**. [Evidence](evidence.txt) includes independent SQL observation and exact-run guarded cleanup. [Phase guide](../../docs/WORKFLOW_PHASE_31_50.md).
