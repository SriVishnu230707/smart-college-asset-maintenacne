# Step 14 lab: control a Core connection and bind values

Read the [Core connections and binding guide](../../docs/CORE_CONNECTIONS_AND_BINDING.md), then inspect [python_lab.py](python_lab.py). This implements Step 14 of the [learning path](../../docs/LEARNING_PATH.md) using the one [application Engine](../../college_maintenance/database.py) introduced in Step 13.

## Run the exercise

Reuse the ignored Python environment and [root requirements](../../requirements.txt) installed for [Step 13](../step-13/notes.md). No new dependency is required. With Docker Desktop running, from the project root in PowerShell:

```powershell
.\labs\step-02\start.ps1
.\labs\step-14\verify.ps1 -WriteEvidence
```

The verifier supports PowerShell 7 and Windows PowerShell 5.1. It resolves a Python 3.10+ interpreter with SQLAlchemy 2.1.6, psycopg 3.3.6, and psycopg-binary 3.3.6 before connecting. Supply a specific compatible interpreter when needed:

```powershell
.\labs\step-14\verify.ps1 -PythonExecutable C:\path\to\python.exe -WriteEvidence
```

The Engine reads the learner password privately from ignored `.local/`. If the host port changes, set COLLEGE_POSTGRES_PORT consistently for Compose and Python. The verifier creates a fresh UUID run marker; this synthetic marker can appear in evidence and is not a credential. Paths are anchored to the script location, so the command also works when launched from another directory.

## Predict the fixture and transactions

The lab commits a disposable `college_step14` schema containing departments, one category, assets, and a run-metadata table. It refuses to reuse an existing schema. The initial department is CSE / Computer Science; the category is COMPUTER. Assets PC-001 / Zebra Computer and PC-002 / Alpha Computer both reference CSE and COMPUTER.

| Operation | Expected database outcome |
|---|---|
| Bound PC-001 lookup | Exactly the Zebra Computer row; SELECT autobegins |
| Bound tautology or stacked-statement text | No matching asset; unchanged SQL and separate values |
| Bind asset_code as a supposed column identifier | Two repeated string values, not asset codes |
| Sort by allowlisted code / name | PC-001, PC-002 / PC-002, PC-001 |
| Unsupported sort key | ValueError before cursor execution |
| Missing lookup parameter | Client-side StatementError wrapping InvalidRequestError |
| Begin again after an autobegun SELECT | InvalidRequestError; rollback ends the original transaction |
| Create MECH and NO-COMMIT through connect(), then close | Both are visible inside the transaction; neither persists |
| Create ECE and PC-003 through begin(), then exit normally | Both commit; the department name is Department ECE |
| Create CIVIL and APP-ROLLBACK, then raise InjectedFailure | Both inserts succeed before the exception; both roll back |
| Create EEE, then insert duplicate PC-001 | Second write raises 23505; the preceding department insert rolls back |
| Close every context and dispose the lab's Engine | No checkout remains; the physical writer connection closes |

The successful PC-003 name is the literal string `O'Brien'); DROP TABLE college_step14.assets; --`. Predict why its quote and DROP TABLE text do not execute. Then explain why the sort key needs an allowlist even though the lookup and insert values are bound.

Department UUIDs end in 001 through 005; asset UUIDs end in 001 through 006. Explicit IDs let both Python and psql check each attempted pair. The final committed rows must be:

| Asset | Name | Department |
|---|---|---|
| PC-001 | Zebra Computer | CSE |
| PC-002 | Alpha Computer | CSE |
| PC-003 | O'Brien'); DROP TABLE college_step14.assets; -- | ECE |

## Follow the proof and cleanup

`register_pair` borrows the caller's Connection for both inserts. It neither begins a second transaction nor commits. Each expected exception is caught outside the transaction context; an unexpected exception or result fails the process. The duplicate-code proof inspects both the original psycopg exception and constraint name, rather than accepting any database error.

The cursor listener records statement text and parameters only to prove value separation. Printed values are synthetic fixture inputs. SQLAlchemy's automatic parameter logging remains hidden by the existing Engine configuration; hiding automatic parameters does not redact custom prints.

After Python closes its checkouts and disposes the Engine, [reconnect.sql](reconnect.sql) uses an independent psql backend. It checks the exact run marker, the disconnected writer PID, all committed parent/asset values and relationships, and the absence of every rolled-back pair. These observations establish persistence independently of Python's assertions or pooled connection reuse.

The verifier first calls [cleanup.sql](cleanup.sql) with a different marker. It must refuse with psql exit 3 and SQLSTATE 22023. No object is removed, and the subsequent observer must still find the expected fixture. A `finally` block then attempts cleanup with the correct marker, including after a failed exercise. Cleanup requires the learner database/role, schema ownership, and exactly one matching metadata row. It removes only the known tables in dependency order and the schema, without CASCADE. An unexpected dependency makes that cleanup transaction fail.

[cleanup-check.sql](cleanup-check.sql) confirms committed removal through another connection. If cleanup fails, the verifier fails rather than recording successful evidence. Inspect the failed run's marker and ownership before any manual cleanup; do not replace the guards with a broad schema deletion.

## Recorded result and learning gate

The live run on **24 October 2026** passed **32 checks**: 25 Python checks, four independent persistence checks, the wrong-run refusal, guarded cleanup, and fresh-connection cleanup confirmation. The [saved evidence](evidence.txt) contains the real SQL/parameter trace, transaction observations, expected errors, observer PIDs, final rows, and cleanup. The cleanup-refusal ERROR 22023 is intentional and checked; it is not an unexpected failure.

Explain who owns the Connection and transaction, when SELECT autobegins, why closing connect() does not commit, and why exceptions must reach the begin() context. Reproduce the two-write rollback and predict the bound-text and identifier results before executing them. Step 15 next introduces metadata, Table, Column, schema qualification, and reflection; no mapped application model or permanent application schema is introduced here.
