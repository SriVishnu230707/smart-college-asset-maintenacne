# Step 59: Build PostgreSQL integration tests

Learn: Choose fixtures, real commits, separate connections, synchronization barriers, and rollback/savepoint test scope.

  Apply: Automate integrity, authorization, report, migration, and contention cases against PostgreSQL.

  Prove: State which tests require independent committed transactions; do not substitute SQLite for PostgreSQL-specific evidence.

Run from PowerShell with Docker ready and the pinned environment installed:

```powershell
.\labs\step-59\verify.ps1 -WriteEvidence
```

The experiment uses synthetic data in an isolated schema. Review python_lab.py before running; predict results and explain each rejection. The independent observer checks committed values, and cleanup requires the exact run marker. Secrets and temporary operational artifacts stay under ignored .local/.

Verified: 12 checks passed in both installed PowerShell versions. Eight unittest cases exercise actual PostgreSQL constraints, rollback, commits, distinct-backend locks, authentication, authorization and report scope without skips.

See [captured evidence](evidence.txt).
