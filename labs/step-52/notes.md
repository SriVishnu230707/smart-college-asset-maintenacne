# Step 52: Build time-based reports

Learn: Use date_trunc, explicit reporting zones, intervals, conditional aggregates, and missing-period handling.

  Apply: Produce department-month costs and repair durations, with a complete month series where required.

  Prove: Test local-midnight boundaries, open tickets, missing months, and the chosen rework-duration definition.

Run from PowerShell with Docker ready and the pinned environment installed:

```powershell
.\labs\step-52\verify.ps1 -WriteEvidence
```

The experiment uses synthetic data in an isolated schema. Review python_lab.py before running; predict results and explain each rejection. The independent observer checks committed values, and cleanup requires the exact run marker. Secrets and temporary operational artifacts stay under ignored .local/.

Verified: 17 checks passed in both installed PowerShell versions. Month grids, Kolkata-midnight boundaries, empty departments, lag and unfinished-duration NULLs match exact fixtures.

See [captured evidence](evidence.txt).
