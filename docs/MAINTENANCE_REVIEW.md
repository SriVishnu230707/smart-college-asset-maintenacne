# Maintenance review: reliable failures and simpler runners

Review date: 24 October 2026. This fixes the implemented Steps 2-20 without advancing the learning checklist.

## Reproduced bugs

| Case | Before | After |
|---|---|---|
| Python fails, then cleanup fails | CLEANUP_FAILURE replaced PRIMARY_LAB_FAILURE; cleanup-check.sql never ran | The original error and both cleanup errors are reported; both exact-run checks are attempted |
| A child fails after a previous successful suite | The old STALE_PASSED_LOG remained because output was saved only after exit validation | Current stdout/stderr replaces the log before the nonzero exit propagates |
| An executable cannot be found | An older child log could remain | The log is cleared before executable lookup |

The original Step 20 wrapper was reproduced with scoped process/SQL replacements, so no database failure or foreign schema was needed. The stale-log case used a real child process that wrote CURRENT_FAILURE and exited 4. The failed child left the older log untouched under the former suite ordering.

## Changes

[The shared PowerShell helper](../labs/shared/verify.ps1) now owns the committed-lab flow for Steps 8, 14, 18, 19, and 20. Each entry point keeps its step title, expected behavior, and evidence option in seven lines. Python entry points retain interpreter overrides; SQL-only Step 8 resolves no Python interpreter. The helper retains the mismatched-run refusal, independent observation, ownership/run-ID cleanup guards, and successful evidence structure. The refusal uses a fixed empty UUID distinct from the generated run UUID, removing a repeated random-ID retry loop.

Cleanup and its independent verification are attempted separately. A cleanup failure cannot suppress the original lab error or skip the second attempt. The run fails if either cleanup check fails, and success evidence is emitted only after the whole flow succeeds. Missing Python still fails before SQL starts.

Invoke-LabProcess accepts an optional LogPath. It clears a prior log before command lookup, captures stdout/stderr, saves the current output, then checks the exit code. [The suite](../tests/run.ps1) delegates logging to that helper so failing children cannot bypass log creation.

[The Python observation helper](../labs/shared/observations.py) groups statements in one pass for Steps 18-20, preserving empty phases and statement order. Previously, each predicted phase rescanned the full trace. Checkpoint tests still retain their original trace lists. Explicit lab packaging keeps the shared import local to this repository.

The changed runtime/helper files total **920 lines instead of 1,091**, a reduction of **171 lines**. This measures those files against the Step 20 commit; documentation and the new regression tests are excluded. It is a code-size comparison, not a runtime benchmark.

## Verification and evidence

[Seven new runner regressions](../tests/runner-regressions.ps1) exercise failed child logs, launch failure, simultaneous primary/cleanup errors, observer failure, cleanup-only failure, successful guarded execution, and SQL-only execution without Python. Synthetic process logs are isolated by PID. The native-process tests use the current shell; the cleanup tests inject faults without connecting to PostgreSQL or overwriting lesson evidence.

The complete suite retains **582 lab checks** and adds these cases to the existing seven runner checks, for **14 runner checks and 596 total checks**. See the saved [PowerShell 7 summary](../tests/evidence-powershell7.txt) and [Windows PowerShell 5.1 summary](../tests/evidence-powershell5.txt). Both runs require exact lesson pass counts, process exit propagation, and a fresh connection confirming no study schemas remain.

Existing business constraints, lesson predictions, Session transaction boundaries, and the learning checklist through Step 20 are preserved. Local logs and credentials stay in ignored `.local/`.
