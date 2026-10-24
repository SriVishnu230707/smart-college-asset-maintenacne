# Step 18 lab: perform ORM persistence

Read the [Session persistence guide](../../docs/ORM_SESSION_PERSISTENCE.md), inspect the [shared Session factory](../../college_maintenance/sessions.py) and [lesson-local asset helpers](asset_crud.py), then run [python_lab.py](python_lab.py). This implements only Step 18 of the [learning path](../../docs/LEARNING_PATH.md).

## Run the proof

Reuse the ignored Python environment and [root requirements](../../requirements.txt). With Docker Desktop running, from the project root:

```powershell
.\labs\step-02\start.ps1
.\labs\step-18\verify.ps1 -WriteEvidence
```

The verifier supports PowerShell 7 and Windows PowerShell 5.1. It resolves files from its own location, requires Python 3.10+ with SQLAlchemy 2.1.6, psycopg 3.3.6, and psycopg-binary 3.3.6, and installs nothing. Select a compatible interpreter explicitly if needed:

```powershell
.\labs\step-18\verify.ps1 -PythonExecutable C:\path\to\python.exe -WriteEvidence
```

The existing Engine reads its learner credential privately from ignored `.local/`. Set COLLEGE_POSTGRES_PORT consistently for Compose and Python if changing the published port. All data is synthetic; the fixture's hash string is not a real login credential.

## Predict before executing

The lab refuses a pre-existing college_step18 namespace. It commits two departments (CSE/ECE), one COMPUTER category, one ECE student reporter, KEEP-001, and an open ticket referencing KEEP-001. The lab-bound factory uses schema translation with the existing pool; application model metadata stays unqualified.

| Question | Expected observation |
|---|---|
| Construct an unused Session from the shared factory | No connection checkout; bound to the existing Engine |
| Add PC-001 and LAB-TEMP, then commit | Real Asset instances receive UUIDs and active defaults |
| Fresh Session.get(Asset, id) | SELECT returns a mapped object with committed values |
| Select all / filter CSE | KEEP-001, LAB-TEMP, PC-001 / LAB-TEMP, PC-001 |
| Assign PC-001's location and flush | SELECT then UPDATE; commit stores Computer Lab 2 |
| Delete LAB-TEMP | SELECT then DELETE; committed fixture removal |
| Missing get, update, delete | None, None, False; three SELECTs and no DML |
| Insert NO-COMMIT inside only the Session context | INSERT occurs, but closing rolls it back |
| Raise an application error after update and insert | Neither write survives; Session releases its checkout |
| Update PC-001 then insert its code again | 23505 / uq_assets_asset_code; earlier update also rolls back |
| Delete ticket-referenced KEEP-001 | 23001 / fk_tickets_asset; asset and ticket remain |
| Final fresh ORM and Core reads | Exactly KEEP-001 and PC-001 with expected IDs/locations |
| Independent psql after Python disposal | Same committed rows; writer backend absent |
| Cleanup with another run UUID | Refused, exit 3 / SQLSTATE 22023; data still available |
| Cleanup with the matching run UUID | Known objects removed; another connection sees no schema |

Each operation owns a distinct short-lived Session. Helpers borrow it and never commit or close it. Copy IDs/values within its context; do not rely on reading committed, expired objects after closing. The explicit flushes expose generated IDs and immediate write errors; detailed lifecycle and failed-Session recovery experiments belong to Steps 19-21.

## Evidence and learning gate

The live run on **24 October 2026** passed **32 checks**: 25 Python observations/assertions and seven wrapper/psql checks. [Saved evidence](evidence.txt) includes SQL with automatic parameters hidden, the exact attempted asset SQL sequences, structured expected errors, final rows, independent backend observations, and guarded cleanup.

The trace distinguishes attempted writes from committed outcomes. Reads close their implicit transactions; successful write contexts commit; errors escape the transaction context and roll back before the Session closes. Pool events balance, all used identity maps and transaction state are cleared, and disposal closes the physical writer connection. Default Session.close resets resources and allows reuse; the lab checks resource release rather than an invented closed flag.

The fixture is intentionally committed for independent visibility. [verify.ps1](verify.ps1) attempts exact-run cleanup in finally even if Python or an observer fails. [cleanup.sql](cleanup.sql) checks schema ownership and the recorded run UUID, drops only known tables in dependency order without CASCADE, and commits. [cleanup-check.sql](cleanup-check.sql) verifies removal from another connection. The different-run refusal is followed by [reconnect.sql](reconnect.sql), proving its refusal left the fixture intact.

The lesson-local delete helper practices ORM DELETE on disposable rows. Production assets follow the contract's retirement/history policy; authorization and full workflows are later work. No permanent application tables are installed.

Explain why a Session factory is shared but each operation gets a Session, why closing alone does not commit, which SQL each helper emitted, and how a successful UPDATE can disappear after a later error. Reproduce cleanup on success and error before proceeding to Step 19.
