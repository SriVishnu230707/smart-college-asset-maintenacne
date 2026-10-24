# Step 20 lab: distinguish flush from commit

Read the [flush/commit guide](../../docs/ORM_FLUSH_AND_COMMIT.md), then predict the SQL and visibility in [python_lab.py](python_lab.py). The experiment uses MaintenanceTicket, the existing Session factory, and one shared Engine, plus a separate read-only psycopg observer.

## Run

With Docker Desktop running and the ignored environment installed from [root requirements](../../requirements.txt):

```powershell
.\labs\step-02\start.ps1
.\labs\step-20\verify.ps1 -WriteEvidence
```

Python 3.10+, SQLAlchemy 2.1.6, psycopg 3.3.6, and psycopg-binary 3.3.6 are preflight requirements. The verifier supports PowerShell 7 and Windows PowerShell 5.1 from unrelated working directories and installs no dependency. Select an interpreter explicitly if needed:

```powershell
.\labs\step-20\verify.ps1 -PythonExecutable C:\path\to\python.exe -WriteEvidence
```

The Engine privately reads the existing ignored learner credential. Both connections use its host/port/database configuration, including COLLEGE_POSTGRES_PORT. The observer has a five-second connection/statement timeout and verifies read-only READ COMMITTED behavior with a distinct backend PID. Synthetic fixture data and UUID markers contain no real user data.

## Predictions

| Experiment | Predict before running |
|---|---|
| Add COMMIT-TICKET | Pending, no INSERT, observer count zero |
| Flush it | INSERT returns UUID/defaults; writer query sees it, observer count zero |
| Commit it | Observer count becomes one |
| Flush then roll back ROLLBACK-TICKET | Writer saw it, but afterward both readers find no row |
| Query with pending AUTO-TICKET | INSERT precedes SELECT; rollback removes it |
| Query in no_autoflush | SELECT finds no pending row; explicit flush inside the block still inserts |
| Commit with autoflush=False | Earlier SELECT does not insert; commit still flushes and persists COMMIT-NOAUTO |
| Flush UPDATE and BEFORE-ERROR, then invalid priority | 23514 / ck_maintenance_tickets_priority; both earlier writes disappear |
| Query the failed Session before rollback | PendingRollbackError; no statement reaches the cursor |
| Explicit rollback and reuse the same Session | Original values return; valid RECOVERED can commit |
| Final readers | Exactly COMMIT-NOAUTO, COMMIT-TICKET, RECOVERED with expected UUIDs/priorities/defaults |

The guide lists exact measured statement sequences. The observer is simultaneous with the active writer; using a fresh Session on the same connection would not establish independent visibility. The writer's one-slot pool configuration stays unchanged. This tests successful flush versus commit/rollback, rather than a database crash.

## Evidence and cleanup

The live run on **24 October 2026** passed **35 checks**: 29 Python assertions and six wrapper/psql assertions. [Saved evidence](evidence.txt) records visibility checkpoints, exact expected errors, statement ordering, final ticket IDs/values, and both closed Python backends.

The fixture commits one department, category, reporter, and asset for valid ticket references. Only three ticket rows survive. A fresh ORM Session and the driver observer agree; [reconnect.sql](reconnect.sql) independently verifies those rows, original descriptions, defaults, and references after disposal. Aborted, autoflushed-then-rolled-back, and invalid tickets are absent.

Python finally closes Sessions and the observer and disposes the Engine even after unexpected failure. PowerShell finally always attempts matching-run cleanup. A different run UUID is first refused with exit 3 / SQLSTATE 22023, leaving the data available for independent inspection. Matching cleanup requires schema ownership and the recorded UUID, drops only known objects child-first without CASCADE, commits, and verifies absence from another connection.

No permanent application schema, authorization, or full ticket workflow is installed. Explain both connection views, flush triggers, and same-Session recovery before moving to Step 21.
