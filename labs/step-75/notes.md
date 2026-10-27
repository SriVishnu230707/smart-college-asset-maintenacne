# Step 75: Async execution and large-result streaming

Learn: Explore AsyncEngine/AsyncSession, explicit I/O, one Session per task, stream/yield_per, and loader compatibility. Prerequisites: 32, 48, 61.

  Apply: Port one proven use case and export a large result without materializing everything.

  Prove: Preserve transaction tests, avoid shared concurrent Sessions, and explain driver/cursor and eager-loading limitations.

Run from PowerShell with Docker ready and the pinned environment installed:

```powershell
.\labs\step-75\verify.ps1 -WriteEvidence
```

The experiment uses synthetic data in an isolated schema. Review python_lab.py before running; predict results and explain each rejection. The independent observer checks committed values, and cleanup requires the exact run marker. Secrets and temporary operational artifacts stay under ignored .local/.

Verified: 17 checks passed in both installed PowerShell versions. Windows selector-loop async commit and rollback, schema-consistent run_sync/streaming, distinct concurrent Sessions, explicit loading and backend disposal pass.

See [captured evidence](evidence.txt).
