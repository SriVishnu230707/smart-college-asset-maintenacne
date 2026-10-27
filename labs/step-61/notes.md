# Step 61: Budget and clean up connections

Learn: Use pool_size, max_overflow, checkout timeout, worker counts, connection failure handling, and transaction cleanup.

  Apply: Set a deliberate connection budget and force success/error paths through the API.

  Prove: Connections return to the pool, requests do not leave idle transactions, and exhaustion produces a controlled diagnosis.

Run from PowerShell with Docker ready and the pinned environment installed:

```powershell
.\labs\step-61\verify.ps1 -WriteEvidence
```

The experiment uses synthetic data in an isolated schema. Review python_lab.py before running; predict results and explain each rejection. The independent observer checks committed values, and cleanup requires the exact run marker. Secrets and temporary operational artifacts stay under ignored .local/.

Verified: 19 checks passed in both installed PowerShell versions. Finite pool exhaustion, HTTP success/error cleanup, stale-backend pre-ping and independent disposal checks pass.

See [captured evidence](evidence.txt).
