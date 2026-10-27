# Step 73: Events, triggers, and database functions

Learn: Explore Session/mapper/connection events, SQL/PLpgSQL functions, and row triggers in separate experiments. Prerequisites: 36, 59.

  Apply: Compare explicit audit writes with a trigger for a selected table and test ORM versus direct SQL paths.

  Prove: Explain actor propagation, transaction rollback, bulk-write coverage, and how duplicate audit entries are avoided.

Run from PowerShell with Docker ready and the pinned environment installed:

```powershell
.\labs\step-73\verify.ps1 -WriteEvidence
```

The experiment uses synthetic data in an isolated schema. Review python_lab.py before running; predict results and explain each rejection. The independent observer checks committed values, and cleanup requires the exact run marker. Secrets and temporary operational artifacts stay under ignored .local/.

Verified: 17 checks passed in both installed PowerShell versions. ORM hooks and database triggers are compared against direct SQL, trusted actor context, rollback and one-authority audit policy; stored functions are called through func.

See [captured evidence](evidence.txt).
