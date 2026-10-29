# PostgreSQL regression verification

Install the root pinned requirements in .venv and start Docker Desktop. Run:

```powershell
.\tests\run.ps1 -WriteEvidence
```

The current suite contains **79 executable labs (Steps 2–80), 1769 lab checks and 14 runner regression checks: 1783 checks**. Step 1 is documented business reasoning. The runner does not advance the learning checklist. Each lesson also has labs/step-NN/verify.ps1. Use sequential execution because fixed study namespaces are shared.

The final full-suite [PowerShell 7 evidence](evidence-powershell7.txt) and [Windows PowerShell 5.1 evidence](evidence-powershell5.txt) each cover the current implementation. Steps 51–80 were also individually verified in both shells and through all three debug batches below.

| Batch | PowerShell 7 | Windows PowerShell 5.1 |
|---|---|---|
| 51–60 | [Evidence](evidence-steps51-60-powershell7.txt) | [Evidence](evidence-steps51-60-powershell5.txt) |
| 61–70 | [Evidence](evidence-steps61-70-powershell7.txt) | [Evidence](evidence-steps61-70-powershell5.txt) |
| 71–80 | [Evidence](evidence-steps71-80-powershell7.txt) | [Evidence](evidence-steps71-80-powershell5.txt) |

Run tests/debug-batch.ps1 -FromStep 51, 61, or 71 to repeat a checkpoint. Arbitrary subsets use tests/run.ps1 -FromStep NN -ThroughStep NN -WriteEvidence, saving separate range-specific evidence. Batch 61–70 predates the extra Step 64 HTTP row-budget assertion; that follow-up was reverified individually in both shells and is included in the current full suite.

Coverage includes actual PostgreSQL integrity/transactions, exact money/time, SQL/Core/ORM results, migrations, HTTP authorization, immutable history, real independent-backend locks/isolation, rollback and durable retries, reports and query budgets, executed plans, imports, runtime-role denial, deployment, backup/restore, native types, RLS, async streaming, real physical/logical replication and PITR, and independent preventive-slot contention/recovery.

Every committed lab retains an independent SQL observer and exact-run cleanup guard. Tests run from an unrelated working directory. Larger temporary fixtures are dropped or reduced before snapshots. Generated roles/databases, fresh Compose projects and scratch recovery clusters have explicit bounded cleanup scopes; the persistent learning volume and unrelated projects are not reset.

Python resolution checks the project virtual environment, PATH and an existing bundled candidate, respects -PythonExecutable, and checks dependencies before SQL. Async steps additionally require Python 3.11+ and pinned greenlet. No packages are installed automatically by the suite. Compilation/query plan evidence is rewritten only when explicitly capturing evidence, keeping ordinary regression runs from dirtying tracked plan files.

Full native process logs and failures remain under ignored .local/test-results/. Expected SQLSTATEs and conflicts are assertions, not skipped behavior. There is no SQLite substitution. A failure, changed check count, bad cleanup, or unexpected exit fails the run; success evidence is not saved for a failed individual lesson. See [debug review](../docs/DEBUG_CHECKPOINTS.md).

## Campus Care interface checks

The additional dashboard checks run separately from the original numbered labs:

```powershell
.\tests\dashboard.ps1 -WriteEvidence
powershell.exe -NoProfile -File tests/dashboard.ps1 -WriteEvidence
```

They require the existing local PostgreSQL container and installed Python dependencies. Each run creates and removes its own generated schema. See the [dashboard verification record](../docs/UI_VERIFICATION.md) for evidence and browser coverage.
