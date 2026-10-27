# Step 62: Make deployment reproducible

Learn: Separate database readiness, migrations, application startup, settings, and persistent storage.

  Apply: Provide a Docker Compose setup and commands that create the database and run reviewed migrations before use.

  Prove: Start from fresh local volumes in a disposable environment and complete a repair without manual schema edits.

Run from PowerShell with Docker ready and the pinned environment installed:

```powershell
.\labs\step-62\verify.ps1 -WriteEvidence
```

The experiment uses synthetic data in an isolated schema. Review python_lab.py before running; predict results and explain each rejection. The independent observer checks committed values, and cleanup requires the exact run marker. Secrets and temporary operational artifacts stay under ignored .local/.

Verified: 24 checks passed in both installed PowerShell versions. Fresh Compose deployment runs owner migrations, non-owner runtime HTTP repair/proof/verification and independent SQL acceptance, then removes only its generated project.

See [captured evidence](evidence.txt).
