# Step 65: JSONB and mutation tracking

Learn: Explore JSONB operators, containment/path queries, expression/GIN indexes, JSON null versus SQL NULL, and ORM mutation tracking. Prerequisites: 32, 54–56.

  Apply: Add varying asset specifications while preserving typed relational columns; compare replacement and nested in-place edits.

  Prove: Reload through a new Session and verify persistence; justify any JSON index with its query.

Run from PowerShell with Docker ready and the pinned environment installed:

```powershell
.\labs\step-65\verify.ps1 -WriteEvidence
```

The experiment uses synthetic data in an isolated schema. Review python_lab.py before running; predict results and explain each rejection. The independent observer checks committed values, and cleanup requires the exact run marker. Secrets and temporary operational artifacts stay under ignored .local/.

Verified: 17 checks passed in both installed PowerShell versions. Fresh Sessions expose shallow versus nested JSON mutation, SQL/JSON null differences and measured selective GIN containment; mutable parents retain an explicit object reference.

See [captured evidence](evidence.txt).
