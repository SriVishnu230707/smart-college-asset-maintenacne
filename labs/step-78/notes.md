# Step 78: WAL, PITR, and replication

Learn: Study WAL durability, base backups, continuous archiving/recovery targets, physical versus logical replication, and lag in separate operations labs. Prerequisite: 63.

  Apply: Demonstrate a verified point-in-time recovery first, then inspect a replica experiment.

  Prove: Explain RPO/RTO and distinguish backups from replicas; do not claim an untested archive is recoverable.

Run from PowerShell with Docker ready and the pinned environment installed:

```powershell
.\labs\step-78\verify.ps1 -WriteEvidence
```

The experiment uses synthetic data in an isolated schema. Review python_lab.py before running; predict results and explain each rejection. The independent observer checks committed values, and cleanup requires the exact run marker. Secrets and temporary operational artifacts stay under ignored .local/.

Verified: 20 checks passed in both installed PowerShell versions. Real physical backup, WAL archiving and named-point recovery, physical standby and logical subscription execute in four private scratch clusters with exact-marker cleanup.

See [captured evidence](evidence.txt).
