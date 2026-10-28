# Debug checkpoints

Run `tests/debug-batch.ps1 -FromStep 51`, then repeat with 61 and 71 after those groups complete. Each checkpoint runs its ten labs from an unrelated working directory in both installed PowerShell versions, checks exact assertion counts, runs shared runner regressions, and confirms schema cleanup. Evidence is saved under tests/evidence-stepsNN-NN-powershellN.txt. A failed checkpoint is fixed and rerun before advancing.

The first 51–60 run found a working-directory bug in Step 58: its temporary credential directory used a relative `.local` path. Both Step 58 and the same pattern in Step 63 now derive the path from the script's absolute project root. The retained success evidence is produced by the corrected rerun. Local process logs are operational artifacts and can be replaced by subsequent runs.

Checkpoint 61-70 passed in both shells: 191 lab checks and 14 runner regression checks per shell. Fresh container deployment, custom-format restore, real contention acceptance, scoped search and isolated mapping/type labs all passed from an unrelated directory. No additional defect was found in this batch.

Checkpoint 71–80 passed in both shells: 195 lab checks and 14 runner regression checks per shell. It covers native PostgreSQL RLS, Windows-selector async execution, explicit statistics namespaces, measured index alternatives, partition recovery, real PITR/physical/logical replication, local outbox crash recovery, and independent scheduling contention/restore.

Final review added a validated row cap to ranked HTTP reporting and made Step 64's month-boundary fixture use its reporting timezone. Step 64 was reverified in both shells with 30 checks (one more than the earlier batch snapshot), with a separate follow-up commit. Ordinary regression runs now preserve checked-in execution-plan artifacts; explicit evidence capture is required to refresh them.

Final whole-project checkpoint: all 79 executable labs (Steps 2-80), 1769 lab checks and 14 runner regressions (1783 checks) passed in both PowerShell 7 and Windows PowerShell 5.1. This includes the current 30-check Step 64 proof. [PowerShell 7 evidence](../tests/evidence-powershell7.txt), [PowerShell 5.1 evidence](../tests/evidence-powershell5.txt).
