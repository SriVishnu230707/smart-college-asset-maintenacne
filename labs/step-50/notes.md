# Step 50: Structure advanced report expressions

Equivalent LATERAL, correlated scalar and DISTINCT ON CTE reports preserve ticket grain, deterministic ties, absent-child NULLs and scoped access.

LATERAL naturally selects a bounded child row per ticket; a scalar subquery suits individual values, while DISTINCT ON supports a reusable latest-row CTE. Every method orders created_at DESC, id DESC. MAX(body) is deliberately shown to answer a different question. UNION/UNION ALL, INTERSECT, EXCEPT and NOT EXISTS have explicit identity/multiplicity proofs, and the completed-cost expression composes as a CTE. No performance winner is claimed without later execution-plan evidence. Final migration review found doubled CHECK names from earlier naming conventions; a forward-only correction preserves published revisions, and an exact catalog-name test covers what autogenerate omits. The full chain is also tested from a fresh database through a populated pre-ledger balance. See [SQLAlchemy SELECT expressions](https://docs.sqlalchemy.org/en/21/tutorial/data_select.html) and [PostgreSQL LATERAL](https://www.postgresql.org/docs/18/queries-table-expressions.html#QUERIES-LATERAL). CTE query-count regression now classifies compiled WITH statements by SQLAlchemy statement type, and the pinned HTTP client follows Starlette 1.10 with HTTPX 2 instead of its deprecated fallback.

Predict the successful and rejected outcomes before running the experiment; inspect the emitted SQL/counts and committed observations. Explain why each failure rolls back or is denied.

```powershell
.\labs\step-50\verify.ps1 -WriteEvidence
```

Pass -PythonExecutable for an explicit installed interpreter. Requires Docker and the ignored environment installed from [requirements](../../requirements.txt). No real personal data is used.

Verified 2026-10-25: **31 checks passed in both PowerShell 7 and Windows PowerShell 5.1**. [Evidence](evidence.txt) includes independent SQL observation and exact-run guarded cleanup. [Phase guide](../../docs/WORKFLOW_PHASE_31_50.md).
