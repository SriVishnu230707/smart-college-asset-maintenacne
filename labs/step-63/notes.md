# Step 63: Practice backup and restoration

Learn: Understand logical dump formats, restoration targets, schema/data/roles coverage, and verification.

  Apply: Restore a backup into a separate fresh database and run integrity and cost-report checks.

  Prove: Historical costs, inventory reconciliation, and ticket relationships survive restoration.

Run from PowerShell with Docker ready and the pinned environment installed:

```powershell
.\labs\step-63\verify.ps1 -WriteEvidence
```

The experiment uses synthetic data in an isolated schema. Review python_lab.py before running; predict results and explain each rejection. The independent observer checks committed values, and cleanup requires the exact run marker. Secrets and temporary operational artifacts stay under ignored .local/.

Verified: 16 checks passed in both installed PowerShell versions. Real pg_dump/pg_restore into a fresh database preserves stock reconciliation, frozen costs, audit, history triggers and separately copied proof bytes.

See [captured evidence](evidence.txt).
