# Step 38: Reconcile stock with a movement ledger

Opening balances, supplier receipts, and reasoned adjustments update stock and append signed movements in one transaction.

Only Super Admin manages central stock. Zero opening stock creates no movement; positive stock creates one opening entry. Row locks serialize balance changes, negative balances are rejected, and failure after the balance flush rolls back the ledger and balance together. A reviewed migration adopts any pre-existing positive balance as a clearly marked legacy opening, without inventing a human actor; all new commands require a real actor. Partial unique indexes protect opening and consumption identities. Movement immutability is added in Step 39.

Predict the successful and rejected outcomes before running the experiment; inspect the emitted SQL/counts and committed observations. Explain why each failure rolls back or is denied.

```powershell
.\labs\step-38\verify.ps1 -WriteEvidence
```

Pass -PythonExecutable for an explicit installed interpreter. Requires Docker and the ignored environment installed from [requirements](../../requirements.txt). No real personal data is used.

Verified 2026-10-25: **23 checks passed in both PowerShell 7 and Windows PowerShell 5.1**. [Evidence](evidence.txt) includes independent SQL observation and exact-run guarded cleanup. [Phase guide](../../docs/WORKFLOW_PHASE_31_50.md).
