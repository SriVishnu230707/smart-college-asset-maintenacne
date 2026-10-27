# Step 74: Row-level security

Learn: Explore RLS USING/WITH CHECK, policy combinations, ownership/BYPASSRLS, and transaction-local request context. Prerequisites: 34, 58, 61.

  Apply: Add department isolation for a selected resource and test with the real limited runtime role.

  Prove: Prove another department cannot read/write and that pooled connection context does not leak between requests.

Run from PowerShell with Docker ready and the pinned environment installed:

```powershell
.\labs\step-74\verify.ps1 -WriteEvidence
```

The experiment uses synthetic data in an isolated schema. Review python_lab.py before running; predict results and explain each rejection. The independent observer checks committed values, and cleanup requires the exact run marker. Secrets and temporary operational artifacts stay under ignored .local/.

Verified: 18 checks passed in both installed PowerShell versions. Real non-owner RLS reads and writes, WITH CHECK, owner/superuser behavior and pooled transaction-context cleanup are verified.

See [captured evidence](evidence.txt).
