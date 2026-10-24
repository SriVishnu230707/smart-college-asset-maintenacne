# Step 16 lab: execute Core DML and understand results

Read the [Core DML and results guide](../../docs/CORE_DML_AND_RESULTS.md), then inspect [python_lab.py](python_lab.py) and [schema.py](schema.py). This implements Step 16 of the [learning path](../../docs/LEARNING_PATH.md), translating earlier SQL asset operations to Core while proving result contracts.

## Run the lab

Reuse the ignored Python environment and [root requirements](../../requirements.txt) from [Step 13](../step-13/notes.md). With Docker Desktop running, execute from the project root:

```powershell
.\labs\step-02\start.ps1
.\labs\step-16\verify.ps1 -WriteEvidence
```

The verifier checks Python 3.10+, SQLAlchemy 2.1.6, psycopg 3.3.6, and psycopg-binary 3.3.6 before connecting. It supports PowerShell 7 and Windows PowerShell 5.1 and resolves paths from the script location. Supply a compatible interpreter explicitly when needed:

```powershell
.\labs\step-16\verify.ps1 -PythonExecutable C:\path\to\python.exe -WriteEvidence
```

No new dependencies are needed. Credentials remain in ignored `.local/`. If the published port changes, set COLLEGE_POSTGRES_PORT consistently for Compose and Python.

## Predict the fixture and result shapes

The declarations adapt the reduced three-table Step 15 fixture into college_step16 so the two lessons remain independently runnable. This is a lab schema, not permanent application or migration ownership. INSERT RETURNING obtains generated UUIDs and associates them by business code; no returned-row order is assumed.

| Asset | Department / category | Initial location | Initial status |
|---|---|---|---|
| PC-001 / Lab Computer | CSE / COMPUTER | Computer Lab 1 | active |
| PC-002 / Electronics Computer | ECE / COMPUTER | NULL | active |
| PRJ-001 / Classroom Projector | CSE / PROJECTOR | Lecture Hall A | active |

The initial SELECT projects asset_code, asset_name, and location ordered by unique asset_code. Predict the result before every execution:

| Scenario | Expected result |
|---|---|
| all | Three Rows; calling all again on the exhausted result yields an empty sequence |
| Row access | Matching position, attribute, label, and Column mapping values |
| mappings | Three RowMapping values; explicit dict conversion retains all fields |
| scalars | Three code strings; index 1 instead returns the names |
| one for PC-001 | Exactly the required Row |
| one_or_none for PC-002 / MISSING | Existing Row / None |
| first for CSE | PC-001 accepted despite another matching asset; no automatic SQL LIMIT |
| one for MISSING / CSE | NoResultFound / MultipleResultsFound |
| one_or_none for CSE | MultipleResultsFound |
| scalar_one for a unique ID / missing ID / CSE IDs | UUID / NoResultFound / MultipleResultsFound |
| scalar_one for PC-002 location | None, although the asset exists |
| one_or_none for that location / missing asset location | Row `(None,)` / no Row |
| Read after first / read non-returning DML | ResourceClosedError |

The seven expected client errors are checked by exact type: two NoResultFound, three MultipleResultsFound, and two ResourceClosedError. They are distinct from a PostgreSQL constraint error and do not abort this transaction. A later COUNT proves the connection remains usable.

## Predict the writes

The lab inserts LAB-TEMP and checks its returned UUID through a subsequent SELECT. It updates PRJ-001 to Room 204 / under_maintenance and verifies every returned field. A missing-code UPDATE RETURNING yields no row. Updating PC-001 to its already equal location reports one matched row; a non-returning update of MISSING reports zero.

DELETE RETURNING identifies LAB-TEMP's removed UUID. Repeating that delete returns no row. After removing the temporary asset, the CSE update returns exactly PC-001 and PRJ-001; compare those identities as a set, independently of result order or rowcount. Finally, deleting PC-002 returns its original UUID.

The final rows inside the transaction must be PC-001 / Lab Computer / Computer Lab 1 / under_maintenance and PRJ-001 / Classroom Projector / Room 204 / under_maintenance. Core and raw SQL must return the same ordered values. These assets have no historical tickets; the delete demonstration does not replace the project's retirement/history rules.

## Recorded result and cleanup

The live run on **24 October 2026** passed **40 checks**: 38 Python assertions/observations and two independent psql checks. [Saved evidence](evidence.txt) includes compiled bound INSERT/SELECT/UPDATE/DELETE SQL, returned UUIDs, exact result-error types, final rows, and cleanup confirmation.

The lab refuses an existing college_step16 schema. The entire schema and data fixture live in one transaction, rolled back in finally even after a failure. A later checkout confirms absence, then Engine disposal closes its physical connection. [reconnect.sql](reconnect.sql) independently checks the learner identity, different backend, absent writer, and absent study schema. Evidence is saved only after the full proof succeeds.

Choose a method based on both the desired shape and allowed row count, explain why first does not prove uniqueness, and distinguish a NULL field from a missing row. Continue to Step 17's typed ORM mappings when you can reproduce these choices without copying the expected results.
