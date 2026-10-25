# Step 17 lab: define typed mapped classes

Historical scope: Steps 17-20 use the [frozen column-only model snapshot](../shared/column_models.py) so their original mapping and SQL predictions remain reproducible. Current application mappings evolve from Step 22 onward.


Read the [typed-mapping guide](../../docs/TYPED_ORM_MAPPINGS.md), inspect the [application models](../../college_maintenance/models.py), then run [python_lab.py](python_lab.py). This implements Step 17 of the [learning path](../../docs/LEARNING_PATH.md). It introduces mapped column definitions; Session persistence is Step 18.

## Run the proof

Reuse the existing ignored Python environment and [root requirements](../../requirements.txt). With Docker Desktop running, from the project root:

```powershell
.\labs\step-02\start.ps1
.\labs\step-17\verify.ps1 -WriteEvidence
```

The verifier requires Python 3.10+, SQLAlchemy 2.1.6, psycopg 3.3.6, and psycopg-binary 3.3.6. It supports PowerShell 7 and Windows PowerShell 5.1, resolves paths from its own location, and installs no dependency. A compatible interpreter can be selected explicitly:

```powershell
.\labs\step-17\verify.ps1 -PythonExecutable C:\path\to\python.exe -WriteEvidence
```

The existing Engine reads credentials privately from ignored `.local/`. Set COLLEGE_POSTGRES_PORT consistently for Compose and Python if the published port changes. The hash string used in the fixture is synthetic and is never a real login credential.

## Predict the mapping observations

| Question | Expected result |
|---|---|
| Registry contents | Exactly Department, AssetCategory, Asset, User, MaintenanceTicket |
| Shared metadata | Five Tables, 36 columns; all belong to Base.metadata |
| Annotations | Every mapped column has a Mapped annotation |
| Mapper columns | Same attributes and columns as each class's Table |
| Class attribute | InstrumentedAttribute referring to a Core column |
| Optional references | User department and ticket assignee are nullable |
| Required references | Asset parents and ticket asset/reporter/recorded department are NOT NULL |
| Lifecycle times | Aware SQL timestamps; required creation and optional later events |
| Plain annotated object | No mapper; runtime assignment can violate its hint |
| Mapped Department with a bad code and None name | Construction succeeds without validating those values |
| Department with an unknown keyword | TypeError |
| Server defaults before inserting | No generated UUID or archival value on the new object |
| Import, inspect, and compile | No physical database connection |
| ORM relationship attributes | None yet; the FK columns are mapped now |

The lab imports all models explicitly, configures their registry, and checks it rather than assuming table registration happened. SQL compilation of Asset and its Table agrees. It does not use a Session or persist the invalid Python object.

## Predict database enforcement

The app models have unqualified table names. Only the lab Connection maps them into college_step17. It refuses a pre-existing lab schema, creates all tables in one transaction, and inspects that explicit namespace. Literal SQL statements are already qualified, because schema translation does not rewrite SQL text.

The valid fixture contains one department, one category, three users (student, technician, Super Admin), one asset, and one open ticket. The Super Admin has no department; the other two users do. Core inserts through mapped Tables expose server defaults without advancing to ORM persistence. The ticket has an aware creation timestamp and NULL assignment/later-event fields.

| Direct SQL attempt | Expected SQLSTATE / diagnostic |
|---|---|
| Omit department name | 23502 / name column |
| Store noncanonical department code | 23514 / ck_departments_code |
| Duplicate asset code with a generated UUID | 23505 / uq_assets_asset_code |
| Invalid asset status | 23514 / ck_assets_status |
| Unknown asset department UUID | 23503 / fk_assets_department |
| Noncanonical email | 23514 / ck_users_email |
| Unrecognized user role | 23514 / ck_users_role |
| Student with NULL department | 23514 / ck_users_department |
| Unrecognized ticket priority | 23514 / ck_maintenance_tickets_priority |
| Unknown optional assignee UUID | 23503 / fk_tickets_assignee |
| Whitespace-only ticket title | 23514 / ck_maintenance_tickets_title |

Each case checks structured PostgreSQL diagnostics and leaves the valid fixture unchanged. A savepoint isolates the expected failure so the outer transaction can continue. These are verification mechanics; flush/commit and Session error recovery remain later lessons.

## Evidence and learning gate

The live run on **24 October 2026** passed **48 checks**: 46 Python observations/assertions and two independent psql checks. [Saved evidence](evidence.txt) includes mapper/table comparisons, compiled DDL, installed database columns and constraint checks, eleven exact rejections, and cleanup.

The lab finally rolls back schema creation and all inserts/probes. It returns every checkout and disposes the short-lived Engine. [reconnect.sql](reconnect.sql) independently verifies the learner identity, different backend, absent writer, and absent study schema. Application metadata remains unqualified and unchanged. No permanent application schema is installed.

Explain why Mapped annotations, a configured mapper, and installed PostgreSQL constraints are different guarantees. Predict optional membership versus the same-row role guard, generated defaults versus constructor values, and foreign-key existence versus assignment eligibility. Continue to Step 18 when you can reproduce those distinctions.
