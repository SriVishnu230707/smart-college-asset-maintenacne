# Step 53: Choose views and materialized views

Learn: Distinguish reusable query definitions from persisted, refreshable results.

  Apply: Create a report view; evaluate a materialized version with a refresh/staleness policy.

  Prove: Explain refresh effects, unique row identity for ORM mapping, and why ordinary projections may suffice.

Run from PowerShell with Docker ready and the pinned environment installed:

```powershell
.\labs\step-53\verify.ps1 -WriteEvidence
```

The experiment uses synthetic data in an isolated schema. Review python_lab.py before running; predict results and explain each rejection. The independent observer checks committed values, and cleanup requires the exact run marker. Secrets and temporary operational artifacts stay under ignored .local/.

Verified: 16 checks passed in both installed PowerShell versions. Live and persisted report projections demonstrate staleness, exact grain, concurrent refresh and explicit scope boundaries.

See [captured evidence](evidence.txt).
