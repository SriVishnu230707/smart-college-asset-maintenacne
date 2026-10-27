# Debug checkpoints

Run `tests/debug-batch.ps1 -FromStep 51`, then repeat with 61 and 71 after those groups complete. Each checkpoint runs its ten labs from an unrelated working directory in both installed PowerShell versions, checks exact assertion counts, runs shared runner regressions, and confirms schema cleanup. Evidence is saved under tests/evidence-stepsNN-NN-powershellN.txt. A failed checkpoint is fixed and rerun before advancing.

The first 51–60 run found a working-directory bug in Step 58: its temporary credential directory used a relative `.local` path. Both Step 58 and the same pattern in Step 63 now derive the path from the script's absolute project root. The retained success evidence is produced by the corrected rerun; the original failed log remains under ignored `.local/debug51-60.log` until replaced by another local run.

Checkpoint 61-70 passed in both shells: 191 lab checks and 14 runner regression checks per shell. Fresh container deployment, custom-format restore, real contention acceptance, scoped search and isolated mapping/type labs all passed from an unrelated directory. No additional defect was found in this batch.
