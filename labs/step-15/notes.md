# Step 15 lab: describe and inspect schema metadata

Read the [metadata and reflection guide](../../docs/SCHEMA_METADATA_AND_REFLECTION.md), inspect [schema.py](schema.py), then run [python_lab.py](python_lab.py) through the verifier. This implements Step 15 of the [learning path](../../docs/LEARNING_PATH.md).

## Run the lab

Reuse the ignored Python environment and [root requirements](../../requirements.txt) from [Step 13](../step-13/notes.md). No new dependency is needed. With Docker Desktop running, from the project root in PowerShell:

```powershell
.\labs\step-02\start.ps1
.\labs\step-15\verify.ps1 -WriteEvidence
```

The verifier checks Python 3.10+, SQLAlchemy 2.1.6, psycopg 3.3.6, and psycopg-binary 3.3.6 before connecting. PowerShell 7 and Windows PowerShell 5.1 are supported. A specific compatible interpreter can be supplied:

```powershell
.\labs\step-15\verify.ps1 -PythonExecutable C:\path\to\python.exe -WriteEvidence
```

Paths are resolved from the script location. The shared Engine privately reads the existing learner credential from ignored `.local/`; the verifier installs no packages. If the published database port changes, set COLLEGE_POSTGRES_PORT consistently for Compose and Python.

## Predict the metadata and inspection results

The schema has three tables, no data fixture, and no ORM mappings. Departments and categories each contain id, code, name, and is_archived. Assets contain id, asset_code, name, department_id, category_id, location, and status. The declaration source is the exact fixture specification; its limited fields do not install the complete application model.

| Question | Prediction |
|---|---|
| Does importing the declarations or compiling DDL connect? | No physical connection opens |
| Table registry keys | college_step15.departments, college_step15.asset_categories, college_step15.assets |
| Required versus optional asset fields | All declared fields required except location |
| CREATE TABLE dependency order | Both parents precede assets; parents may appear in either order |
| UUID, business-code, and status defaults | gen_random_uuid(), no code default, active status |
| Constraint names | Convention-generated PK, unique, check, and FK names |
| Asset references | Required schema-qualified parents; ON DELETE/UPDATE RESTRICT |
| Explicit asset indexes | department_id and category_id; unique backing indexes compared as constraints |
| Can schema-qualified inspection work outside search_path? | Yes |
| Does reflection reuse the declaration objects? | No; a fresh MetaData receives separate tables |
| Which defaults does reflection recover? | Database defaults; no Python default or Table.info |
| Missing FK target at compilation | NoReferencedTableError before a physical connection opens |
| Reflect an absent table | NoSuchTableError; no table is created |
| Inspector after deliberate DDL | Explicitly clear its cache before comparing; caching behavior varies |

The verifier compares columns and constraints for all three tables. Fixed-expression normalization removes PostgreSQL's added text casts, parentheses, and whitespace. This helper is intentionally limited to the fixture; it is not a production schema-diff engine or a general test of SQL semantic equivalence.

## Predict the deliberate drift

The lab adds audit_note text to the database and drops ck_assets_status_allowed. The original declarations still contain seven asset columns and the status check. The old reflected registry also remains unchanged. Refreshed inspection finds exactly the additional column and missing check; fresh reflection captures that changed structure.

A third registry copies the declarations and adds a hypothetical planned_label varchar(40). Calling create_all against existing tables leaves all three differences intact: planned_label is still absent, audit_note remains, and the status check remains absent. The cursor trace verifies that this call emits no CREATE or ALTER statement.

Explain why changing a Python Table or accepting a fresh reflected snapshot does not supply reviewed migration history. These ALTER statements exist solely within the disposable lab transaction. Permanent application schema ownership and Alembic setup belong to later learning steps.

## Cleanup and recorded result

The lab refuses an existing college_step15 schema. Its finally block rolls back the entire transaction, including schema creation and every deliberate alteration. Connection contexts then return their checkouts, and the short-lived lab disposes the shared Engine. No committed fixture or destructive DROP cleanup is needed.

[reconnect.sql](reconnect.sql) receives the writer PID and uses independent psql to confirm the learner identity, different backend, absent writer, and absent study schema. The [shared SQL failure handler](../shared/fail.sql) returns nonzero if a proof fails.

The live run on **24 October 2026** passed **31 checks**: 29 Python observations/assertions and two independent psql checks. The [saved evidence](evidence.txt) contains compiled DDL, actual creation order, inspected column/constraint shapes, the exact drift, and independent cleanup. Unexpected results or exceptions prevent successful evidence from being saved.

Before continuing, explain MetaData versus database schema, predict generated names and dependency order, identify which properties reflection can recover, and reproduce drift detection without treating create_all as a migration tool. Step 16 next develops Core DML and result handling.
