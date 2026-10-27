# Step 57: Import data with explicit failure policy

Learn: Compare batch ORM work, Core bulk INSERT, COPY/staging, ON CONFLICT, and savepoints.

  Apply: Import an asset file with duplicates and invalid records; document all-or-nothing versus per-row rejection.

  Prove: Rejected rows and accepted rows match policy; demonstrate begin_nested flushing behavior rather than assuming isolation from earlier pending changes.

Run from PowerShell with Docker ready and the pinned environment installed:

```powershell
.\labs\step-57\verify.ps1 -WriteEvidence
```

The experiment uses synthetic data in an isolated schema. Review python_lab.py before running; predict results and explain each rejection. The independent observer checks committed values, and cleanup requires the exact run marker. Secrets and temporary operational artifacts stay under ignored .local/.

Verified: 15 checks passed in both installed PowerShell versions. Atomic and per-row imports, duplicate handling, real COPY staging and independent committed-row checks pass.

See [captured evidence](evidence.txt).
