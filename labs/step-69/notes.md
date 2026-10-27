# Step 69: Derived ORM attributes

Learn: Explore hybrid properties, column_property, SQL-expression attributes, and deferred projections. Prerequisites: 32, 49.

  Apply: Express a repair-derived value in Python and in a query, checking the SQL shape.

  Prove: Show equivalent values and reject a formulation that hides N+1 queries or incorrect aggregation.

Run from PowerShell with Docker ready and the pinned environment installed:

```powershell
.\labs\step-69\verify.ps1 -WriteEvidence
```

The experiment uses synthetic data in an isolated schema. Review python_lab.py before running; predict results and explain each rejection. The independent observer checks committed values, and cleanup requires the exact run marker. Secrets and temporary operational artifacts stay under ignored .local/.

Verified: 17 checks passed in both installed PowerShell versions. Exact hybrid costs work in Python and SQL; deferred-column I/O and column_property projection behavior are measured without schema drift.

See [captured evidence](evidence.txt).
