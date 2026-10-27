# Step 71: Inheritance and polymorphic mapping

Learn: Compare single-table, joined-table, and concrete inheritance with category-plus-specifications modeling. Prerequisites: 27, 32, 65.

  Apply: Model computer/projector subtypes in an isolated lab and inspect polymorphic queries.

  Prove: Explain extra joins, constraints, migration cost, and whether inheritance improves the base design.

Run from PowerShell with Docker ready and the pinned environment installed:

```powershell
.\labs\step-71\verify.ps1 -WriteEvidence
```

The experiment uses synthetic data in an isolated schema. Review python_lab.py before running; predict results and explain each rejection. The independent observer checks committed values, and cleanup requires the exact run marker. Secrets and temporary operational artifacts stay under ignored .local/.

Verified: 17 checks passed in both installed PowerShell versions. Single-table, joined-table and concrete polymorphic mappings are exercised against PostgreSQL with observed query and row shapes.

See [captured evidence](evidence.txt).
