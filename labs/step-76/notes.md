# Step 76: Advanced query and index laboratories

Learn: Compare GIN, GiST, SP-GiST, BRIN, hash, planner statistics, prepared statements, compiled SQL caches, and plan changes as separate sub-exercises. Prerequisites: 54–56.

  Apply: Use targeted JSON/search/range/time-ordered workloads rather than installing indexes indiscriminately.

  Prove: Distinguish SQL compilation caching from cached data and demonstrate one justified choice plus rejected alternatives.

Run from PowerShell with Docker ready and the pinned environment installed:

```powershell
.\labs\step-76\verify.ps1 -WriteEvidence
```

The experiment uses synthetic data in an isolated schema. Review python_lab.py before running; predict results and explain each rejection. The independent observer checks committed values, and cleanup requires the exact run marker. Secrets and temporary operational artifacts stay under ignored .local/.

Verified: 18 checks passed in both installed PowerShell versions. BRIN, hash, spatial SP-GiST/GiST, explicitly scoped multicolumn statistics, bound compilation caching and server custom/generic plans are measured.

See [captured evidence](evidence.txt).
