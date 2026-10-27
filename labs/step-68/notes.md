# Step 68: PostgreSQL-specific type and constraint laboratories

Learn: Explore ARRAY, native ENUM lifecycle, ranges/multiranges, domains, generated columns, and exclusion constraints in separate sub-exercises. Prerequisites: 27, 55.

  Apply: Model preventive-maintenance time windows and compare an overlap constraint with an application-only check.

  Prove: Show concurrent overlap rejection; document which remaining types are useful or unnecessary for this project's requirements.

Run from PowerShell with Docker ready and the pinned environment installed:

```powershell
.\labs\step-68\verify.ps1 -WriteEvidence
```

The experiment uses synthetic data in an isolated schema. Review python_lab.py before running; predict results and explain each rejection. The independent observer checks committed values, and cleanup requires the exact run marker. Secrets and temporary operational artifacts stay under ignored .local/.

Verified: 19 checks passed in both installed PowerShell versions. ARRAY, enum transaction lifecycle, numeric domains, generated values, multiranges and real exclusion-constraint contention are verified.

See [captured evidence](evidence.txt).
