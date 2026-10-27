# Step 58: Separate database ownership and runtime privileges

Learn: Study database roles, ownership, GRANT/REVOKE, schema access, and trusted connection configuration.

  Apply: Use a limited application role and a separate migration owner; protect credentials and exclude them from logs.

  Prove: The runtime can perform required operations but cannot make unauthorized schema changes.

Run from PowerShell with Docker ready and the pinned environment installed:

```powershell
.\labs\step-58\verify.ps1 -WriteEvidence
```

The experiment uses synthetic data in an isolated schema. Review python_lab.py before running; predict results and explain each rejection. The independent observer checks committed values, and cleanup requires the exact run marker. Secrets and temporary operational artifacts stay under ignored .local/.

Verified: 16 checks passed in both installed PowerShell versions. A real non-owner runtime login can write application rows but cannot CREATE, ALTER, TRUNCATE or create schemas; URL secrets remain outside Git.

See [captured evidence](evidence.txt).
