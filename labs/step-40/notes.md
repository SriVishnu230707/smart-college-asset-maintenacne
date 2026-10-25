# Step 40: Complete repairs in one transaction

Authorized completion verifies proof, locks stock, captures final prices, consumes parts, and commits work order, ticket, ledger and audit as one result.

The initial protocol locks ticket, order and sorted stock rows. Every part must be available, proof bytes must match metadata, and exact per-repair totals must fit numeric(12,2). Child snapshots flush before the parent becomes immutable. Completion accepts no editable fields; costs in the returned stable-shaped result are decimal strings. A labor-only zero-cost repair remains valid. Later steps inject failures, compare stock protocols, prove contention, and add durable retry semantics; no cross-request snapshot or retry claim is inferred from this single-success proof.

Predict the successful and rejected outcomes before running the experiment; inspect the emitted SQL/counts and committed observations. Explain why each failure rolls back or is denied.

```powershell
.\labs\step-40\verify.ps1 -WriteEvidence
```

Pass -PythonExecutable for an explicit installed interpreter. Requires Docker and the ignored environment installed from [requirements](../../requirements.txt). No real personal data is used.

Verified 2026-10-25: **22 checks passed in both PowerShell 7 and Windows PowerShell 5.1**. [Evidence](evidence.txt) includes independent SQL observation and exact-run guarded cleanup. [Phase guide](../../docs/WORKFLOW_PHASE_31_50.md).
