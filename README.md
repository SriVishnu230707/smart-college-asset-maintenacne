# Smart College Asset & Maintenance Management System

Learn PostgreSQL and SQLAlchemy by building a college maintenance system one step at a time.

Steps 1-19 are available. The [project contract](docs/PROJECT_CONTRACT.md) and [Step 1 lab](labs/step-01/notes.md) define the business rules. The [Step 2 lab](labs/step-02/notes.md) starts and inspects PostgreSQL. The [relational model](docs/RELATIONAL_MODEL.md) and [Step 3 lab](labs/step-03/notes.md) explain entities and normalization. The [Step 4 decisions](docs/IDENTIFIERS_AND_TYPES.md) and [lab](labs/step-04/notes.md) verify identifiers and ordinary types. The [Step 5 decisions](docs/MONEY_AND_TIME.md) and [lab](labs/step-05/notes.md) cover exact money and event/reporting time. The [Step 6 decisions](docs/ROW_VALIDITY.md) and [lab](labs/step-06/notes.md) verify row constraints, NULL, defaults, and uniqueness. The [Step 7 decisions](docs/REFERENTIAL_INTEGRITY.md) and [lab](labs/step-07/notes.md) cover foreign keys and history-preserving deletion policies. The [Step 8 guide](docs/SQL_CRUD_AND_TRANSACTIONS.md) and [lab](labs/step-08/notes.md) verify CRUD, RETURNING, and explicit transactions. The [Step 9 guide](docs/FILTERING_AND_ORDERING.md) and [lab](labs/step-09/notes.md) cover predicates, text search, casts, and deterministic ordering with LIMIT. The [Step 10 guide](docs/SQL_JOINS.md) and [lab](labs/step-10/notes.md) cover inner, left, and self joins with distinct reporter/assignee aliases. The [Step 11 guide](docs/SQL_AGGREGATION.md) and [lab](labs/step-11/notes.md) cover grouped ticket counts, conditional aggregates, and exact completed-labor totals. The [Step 12 guide](docs/SQL_EXISTENCE_AND_SUBQUERIES.md) and [lab](labs/step-12/notes.md) cover scalar/correlated subqueries, EXISTS/NOT EXISTS, nullable NOT IN, and set operations. The [Step 13 guide](docs/PYTHON_DATABASE_LAYERS.md) and [lab](labs/step-13/notes.md) introduce a shared SQLAlchemy Engine, the psycopg driver, pool reuse, and a traced Core query. The [Step 14 guide](docs/CORE_CONNECTIONS_AND_BINDING.md) and [lab](labs/step-14/notes.md) cover bound values, identifier allowlisting, related-write transactions, and cleanup. The [Step 15 guide](docs/SCHEMA_METADATA_AND_REFLECTION.md) and [lab](labs/step-15/notes.md) cover schema metadata, inspection, reflection, and migration boundaries. The [Step 16 guide](docs/CORE_DML_AND_RESULTS.md) and [lab](labs/step-16/notes.md) cover Core CRUD, RETURNING, and result contracts. The [Step 17 guide](docs/TYPED_ORM_MAPPINGS.md) and [lab](labs/step-17/notes.md) introduce five typed mapped classes and distinguish mapping from installed database enforcement. The [Step 18 guide](docs/ORM_SESSION_PERSISTENCE.md) and [lab](labs/step-18/notes.md) cover short-lived Sessions, asset CRUD, SQL logging, and cleanup after commits and errors.

Start here:

1. Read the [project contract](docs/PROJECT_CONTRACT.md).
2. Work through the [Step 1 proofs](labs/step-01/notes.md).
3. Run the [Step 2 database lab](labs/step-02/notes.md).
4. Study and run the [Step 3 relational-model lab](labs/step-03/notes.md).
5. Run the [Step 4 identifier/type lab](labs/step-04/notes.md).
6. Run the [Step 5 money/time lab](labs/step-05/notes.md).
7. Run the [Step 6 row-validity lab](labs/step-06/notes.md).
8. Run the [Step 7 referential-integrity lab](labs/step-07/notes.md).
9. Run the [Step 8 CRUD/transaction lab](labs/step-08/notes.md).
10. Run the [Step 9 filtering/ordering lab](labs/step-09/notes.md).
11. Run the [Step 10 join lab](labs/step-10/notes.md).
12. Run the [Step 11 aggregation lab](labs/step-11/notes.md).
13. Run the [Step 12 existence/subquery lab](labs/step-12/notes.md).
14. Run the [Step 13 Python database-layer lab](labs/step-13/notes.md).
15. Run the [Step 14 Core connection/binding lab](labs/step-14/notes.md).
16. Run the [Step 15 metadata/reflection lab](labs/step-15/notes.md).
17. Run the [Step 16 Core DML/results lab](labs/step-16/notes.md).
18. Run the [Step 17 typed-mapping lab](labs/step-17/notes.md).
19. Run the [Step 18 ORM persistence lab](labs/step-18/notes.md), then run the [Step 19 lifecycle lab](labs/step-19/notes.md) before Step 20 in the [learning path](docs/LEARNING_PATH.md).

With Docker Desktop running and Python 3.10+ installed, use PowerShell in this project directory. Create the ignored environment once and install the [pinned learning dependencies](requirements.txt):

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\tests\run.ps1 -WriteEvidence
docker compose exec postgres sh /labs/step-02/psql.sh
```

The [regression suite](tests/README.md) starts the database and checks all eighteen executable labs with one command. It covers 547 lab checks plus seven runner regression checks in PowerShell 7 and Windows PowerShell 5.1. Individual lessons retain their own verification commands. See the [PowerShell 7 result](tests/evidence-powershell7.txt) and [Windows PowerShell 5.1 result](tests/evidence-powershell5.txt).

The database is `college_learning`, with the non-superuser login `college_learner`. PostgreSQL is published on `127.0.0.1:55432`. Credentials are generated locally under the Git-ignored `.local/` directory. See the [captured verification output](labs/step-02/evidence.txt).

Step 3's [captured model-verification output](labs/step-03/evidence.txt) demonstrates its design and normalization examples. The SQL probe leaves no persistent application tables behind.

Step 4's [captured identifier/type output](labs/step-04/evidence.txt) proves a fresh UUID cannot bypass a duplicate asset code, alongside generator, string, and boolean comparisons. Its probe is also rolled back.

Step 5's [captured SQL/Python output](labs/step-05/evidence.txt) verifies exact Decimal costs, strict raw-money validation, aware timestamps, and reporting around Kolkata midnight. It requires Python 3.10+ with the [lab requirements](labs/step-05/requirements.txt); the runner checks virtual-environment, PATH, and existing bundled candidates before executing SQL. The SQL probe is rolled back.

Step 6's [captured constraint output](labs/step-06/evidence.txt) records 48 PostgreSQL checks, including 37 expected rejections for invalid inserts/updates. It explains required values versus defaults, CHECK's NULL behavior, independent business uniqueness, and a composite primary key. All demonstration objects are rolled back; no Python dependency is needed.

Step 7's [captured reference-policy output](labs/step-07/evidence.txt) records 43 PostgreSQL checks, including 28 expected rejections. It verifies seven project foreign keys, nullable and composite links, deletion actions, and preserved ticket department history after transfer. All objects are rolled back; no Python dependency is needed.

Step 8's [captured CRUD/transaction output](labs/step-08/evidence.txt) records 23 verification checks, including three deliberate errors. It temporarily commits a small baseline, rolls back writes, verifies the original rows through another connection, and commits guarded cleanup. No study objects remain afterward; no Python dependency is needed.

Step 9's [captured filtering/ordering output](labs/step-09/evidence.txt) records 37 PostgreSQL checks, including three expected rejections. It verifies active/unassigned lists, NULL and blank-text behavior, LIKE/ILIKE and literal wildcards, casts, and unique ordering before LIMIT. All objects are rolled back; no Python dependency is needed.

Step 10's [captured join output](labs/step-10/evidence.txt) records 26 PostgreSQL checks, including three expected query rejections. It verifies complete ticket display rows, optional assignees, ON versus WHERE, historical department paths, and one-to-many/self-join multiplicity. All objects are rolled back and cleanup is checked through a fresh connection; no Python dependency is needed.

Step 11's [captured aggregation output](labs/step-11/evidence.txt) records 25 PostgreSQL checks, including three expected query rejections. It verifies all twelve department/priority buckets, COUNT variants, WHERE/HAVING/FILTER/CASE differences, completed-labor SUM/AVG, absent versus zero values, and numeric report range. All objects are rolled back and cleanup is checked through a fresh connection; no Python dependency is needed.

Step 12's [captured existence/subquery output](labs/step-12/evidence.txt) records 31 PostgreSQL checks, including three expected SQL rejections. It verifies unused assets, current versus historical technician assignments, scalar and correlated subqueries, the nullable NOT IN trap, and UNION/UNION ALL/INTERSECT/EXCEPT. All objects are rolled back and cleanup is checked through a fresh connection; it reuses the shared PowerShell runner.

Step 13's [captured Python/SQL output](labs/step-13/evidence.txt) records 23 checks with SQLAlchemy 2.1.6 and psycopg 3.3.6. It traces a Core expression through the PostgreSQL dialect and psycopg cursor, distinguishes Engine/Connection/Session, verifies lazy connection creation and pool reuse, and recovers from a server error. Final disposal is checked independently through psql. The first [application Engine configuration](college_maintenance/database.py) reads the ignored learner credential; no application schema or mapped ORM model is created.

Step 14's [captured Core connection/binding output](labs/step-14/evidence.txt) records 32 checks using the same Engine. It verifies parameterized lookup, identifier allowlisting, autobegin, successful related writes, rollback on connection closure and exceptions, and resource cleanup. An independent psql connection checks the committed rows and stored injection-shaped text before exact-run guarded cleanup removes the fixture.

Step 15's [captured metadata/reflection output](labs/step-15/evidence.txt) records 31 checks. It compares Core declarations with real PostgreSQL columns, constraints, and indexes, reflects into a separate registry, detects deliberate schema drift, and proves create_all does not migrate existing tables. Its entire schema transaction is rolled back, with cleanup checked independently.

Step 16's [captured Core DML/results output](labs/step-16/evidence.txt) records 40 checks. It verifies explicit generated-ID RETURNING, asset CRUD, Row/mapping/scalar shapes, zero/one/many cardinality, NULL versus absence, result consumption, and matched-row counts. Core and raw SQL agree on the final rows; all fixture objects are rolled back and cleanup is independently confirmed.

Step 17's [captured typed-mapping output](labs/step-17/evidence.txt) records 48 checks for the five [application mapped classes](college_maintenance/models.py). It compares annotations, mapper properties, and installed columns/constraints, and proves database enforcement through eleven direct-SQL rejections. The disposable schema rolls back, and independent psql confirms cleanup and disposal.

Step 18's [captured ORM persistence output](labs/step-18/evidence.txt) records 32 checks. It uses the shared Session factory and lesson-local CRUD helpers to prove committed changes, rollback on close/errors, exact emitted asset SQL, and Session resource release. Independent psql confirms final rows and writer disposal before guarded cleanup removes the committed study fixture.

Step 19's [lifecycle guide](docs/ORM_OBJECT_LIFECYCLE.md), [lab](labs/step-19/notes.md), and [evidence](labs/step-19/evidence.txt) record 39 checks at 15 state checkpoints, including dirty versus modified, queued versus flushed deletion, detachment, rollback restoration, and exact SQL. Independent psql and guarded cleanup verify the final survivor and complete study-schema removal.

The [mastery guide](docs/POSTGRESQL_SQLALCHEMY_MASTERY.md) explains how later SQL, ORM, transaction, and reporting lessons connect to the project.

Current deliverable: the business contract, a running PostgreSQL learning environment, a verified relational model, identifier/money/time decisions, row/reference constraints, SQL proofs, a shared SQLAlchemy Engine, bound Core transactions, metadata/inspection/reflection, Core CRUD, five verified typed ORM column mappings, and short-lived Session persistence with asset CRUD and verified object lifecycle states. Permanent application schema installation, relationships, migrations, API routes, and full business-rule enforcement follow in later learning steps.
