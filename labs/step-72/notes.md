# Step 72: Custom types and attribute validation

Learn: Explore TypeDecorator, value conversion, cache_ok decisions, validators, and custom comparators. Prerequisites: 16, 27, 54.

  Apply: Build a small domain conversion type and compare validation via Python, Core, and direct SQL.

  Prove: Round-trip values and prove that Python validators alone do not establish database integrity.

Run from PowerShell with Docker ready and the pinned environment installed:

```powershell
.\labs\step-72\verify.ps1 -WriteEvidence
```

The experiment uses synthetic data in an isolated schema. Review python_lab.py before running; predict results and explain each rejection. The independent observer checks committed values, and cleanup requires the exact run marker. Secrets and temporary operational artifacts stay under ignored .local/.

Verified: 17 checks passed in both installed PowerShell versions. Custom bind/result conversion, cache configuration, escaped comparators and validator-versus-database enforcement boundaries are exercised.

See [captured evidence](evidence.txt).
