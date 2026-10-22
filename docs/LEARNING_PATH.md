**Sequential PostgreSQL and SQLAlchemy learning path for the college maintenance system**

This plan has no time estimates or deadlines. Work at your own pace and advance by evidence. Your starting point is Python and basic SQL; this path starts before SQLAlchemy and builds toward a complete, reliable maintenance application.

Steps 1–64 form the project path. Steps 65–80 are specialist extensions, each with prerequisites. Some extension steps contain several related sub-experiments; perform those individually. They need not all become production features.

“Every possible property” is an open-ended reference-library goal: both systems have extensive APIs, optional extensions, and server internals. This plan covers the main application engineering concepts systematically and gives you a reference-audit method for further coverage. It does not claim that one application exercises every flag, data type, driver, PostgreSQL extension, or internal subsystem.

Use PostgreSQL 18 and the SQLAlchemy 2.1 documentation consistently with the existing research guide, and pin the implementation's chosen versions. The lesson order and exercises are recommendations, not a sequence prescribed by the official documentation.

For every step:
1. Explain the concept in your own words.
2. Implement its smallest useful project example.
3. Compare SQL with its SQLAlchemy expression where applicable.
4. Inspect generated SQL, results, and object/transaction state.
5. Try an invalid input or competing action.
6. Save evidence and revisit the step without copying.

A step is complete only when its proof succeeds. Before SQLAlchemy is introduced, use raw SQL; after it is introduced, translate earlier exercises rather than learning unrelated examples.

Store observations under labs/step-NN/: notes.md, query.sql where appropriate, a Python experiment where appropriate, and a test or captured observation. Never store credentials or real student data in the labs or tracked files. Available labs cover [business rules](../labs/step-01/notes.md), [SQL inspection](../labs/step-02/notes.md), [relational design](../labs/step-03/notes.md), [identifiers/types](../labs/step-04/notes.md), [money/time](../labs/step-05/notes.md), [row validity](../labs/step-06/notes.md), and [referential integrity](../labs/step-07/notes.md). Add later labs as you reach their steps.

Use a disposable SQL-learning database for hand-written schema experiments. Once Alembic is introduced, let reviewed migrations own the application schema; do not mix independent schema-edit histories.

The detailed design and concurrency guidance remains in [the mastery guide](POSTGRESQL_SQLALCHEMY_MASTERY.md). This checklist supersedes that guide's former calendar-based roadmap.

**Steps 1–8: Foundation: define the system and understand PostgreSQL**

- [x] **01. Define the business invariants**

  Learn: Translate requirements into rules that must remain true after failures and concurrent requests.

  Apply: Write the role/resource permission matrix, ticket transitions, stock rules, immutable completion policy, and historical-cost policy.

  Prove: Explain what must happen when two technicians request the last part and when completion is submitted twice.

  Evidence: [Project contract](PROJECT_CONTRACT.md) and [worked proofs S01-S02](../labs/step-01/notes.md). This marks the written contract and reasoned examples complete; runtime enforcement belongs to later steps, and explaining the rules yourself remains your learning gate.

- [x] **02. Understand the running database**

  Learn: Distinguish server, database, schema, role, connection, and transaction; inspect PostgreSQL through psql.

  Apply: Start a disposable learning database; use connection information, table descriptions, current_database(), current_user, and SHOW search_path.

  Prove: Reconnect without a GUI and locate the current database, role, schema, tables, and server version.

  Evidence: [Step 2 instructions](../labs/step-02/notes.md), [inspection SQL](../labs/step-02/query.sql), and [executed PostgreSQL evidence](../labs/step-02/evidence.txt). PostgreSQL 18.6 was started; two authenticated psql connections confirmed the college_learning database, college_learner non-superuser role, public schema, table descriptions, and rollback. The technical proof passed; explaining the observations remains your learning gate.

- [x] **03. Design the relational model**

  Learn: Practice entities, cardinality, normalization, functional dependencies, and deliberate historical snapshots.

  Apply: Draw departments, categories, users, assets, and tickets; distinguish an asset's current department from a ticket's recorded department.

  Prove: Explain why repeated supplier details and comma-separated part IDs do not belong in ticket rows.

  Evidence: [Relational model and diagrams](RELATIONAL_MODEL.md), [Step 3 instructions](../labs/step-03/notes.md), and [executed PostgreSQL evidence](../labs/step-03/evidence.txt). The five-entity probe verified shared references, optional membership, separate reporter/assignee links, historical department attribution, and normalization counterexamples. Its tables and fixtures were rolled back, and a fresh connection confirmed cleanup. Explaining the design yourself remains your learning gate.

- [x] **04. Choose identifiers and ordinary types**

  Learn: Compare surrogate and natural keys, UUID and identity integers, text/string limits, booleans, and application versus server-generated values.

  Apply: Choose UUID primary keys plus independent unique department codes, asset codes, and part SKUs; document alternatives.

  Prove: Demonstrate that a new UUID does not allow an existing asset_code to be inserted again.

  Evidence: [Identifier/type decisions](IDENTIFIERS_AND_TYPES.md), [Step 4 instructions](../labs/step-04/notes.md), and [executed PostgreSQL evidence](../labs/step-04/evidence.txt). The lab verified client/server UUIDs, independent business-key uniqueness, identity integers and sequence gaps, character limits, and boolean defaults. A fresh UUID with an existing canonical asset code was rejected by the named asset-code constraint. All demonstration objects were rolled back and cleanup was checked through a fresh connection. Explaining the observations remains your learning gate.

- [x] **05. Represent money and time correctly**

  Learn: Map NUMERIC to Decimal and timestamptz to aware datetime; distinguish an instant, a calendar date, and a reporting timezone.

  Apply: Define costs and lifecycle timestamps; calculate an exact repair cost and display one instant in UTC and Asia/Kolkata.

  Prove: Explain rounding policy and group events around a local midnight without changing their instants.

  Evidence: [Money/time decisions](MONEY_AND_TIME.md), [Step 5 instructions](../labs/step-05/notes.md), and [executed SQL/Python evidence](../labs/step-05/evidence.txt). PostgreSQL and Python agreed on the exact 600.50 repair cost and reporting-day totals around Kolkata midnight. Raw monetary input was validated before scaled conversion, aware timestamps retained their instants across timezone displays, and SQL cleanup was confirmed through a new connection. The proof passed 21 PostgreSQL and 13 Python checks; explaining the policy and observations remains your learning gate.

- [x] **06. Enforce row-level validity**

  Learn: Study NULL and three-valued logic, NOT NULL, CHECK, UNIQUE, composite uniqueness, and named constraints.

  Apply: Reject negative stock, nonpositive consumption quantities, invalid statuses, and duplicate business identifiers; compare defaults with mandatory values.

  Prove: Attempt invalid inserts from psql and explain which constraint rejects each one, including NULL cases.

  Evidence: [Row-validity decisions](ROW_VALIDITY.md), [Step 6 instructions and rejection map](../labs/step-06/notes.md), and [executed PostgreSQL evidence](../labs/step-06/evidence.txt). All 48 checks passed, including 37 expected insert/update rejections with SQLSTATE and constraint/column assertions. The lab compared CHECK/NULL behavior, required values and defaults, allowed states, canonical business identities, composite keys, and nullable uniqueness. All objects were rolled back and cleanup was verified from a fresh connection. Explaining the failures yourself remains your learning gate.

- [x] **07. Enforce referential integrity**

  Learn: Study foreign keys, nullable links, composite references, and ON DELETE choices.

  Apply: Connect assets to departments/categories and tickets to assets/users; choose retirement/deactivation for records with history.

  Prove: Try deleting referenced records and show the chosen policy, without relying on Python validation.

  Evidence: [Reference/deletion decisions](REFERENTIAL_INTEGRITY.md), [Step 7 instructions and rejection map](../labs/step-07/notes.md), and [executed PostgreSQL evidence](../labs/step-07/evidence.txt). All 43 checks passed, including 28 expected rejections. Seven project foreign keys reject missing parents and protect referenced history with RESTRICT; comparison probes verify composite/NULL matches and deletion alternatives. Transfers retain the original ticket department, while retirement/deactivation/archive retain referenced identities. Catalog/index policy and rollback cleanup were checked, including a fresh connection. Explaining the policies yourself remains your learning gate.

- [ ] **08. Manipulate the first dataset in SQL**

  Learn: Practice INSERT, SELECT, UPDATE, DELETE, RETURNING, and explicit BEGIN/COMMIT/ROLLBACK.

  Apply: Seed a small department/asset dataset and perform reversible changes directly in psql.

  Prove: Roll back a change and verify its absence from an independent connection.

Checkpoint: You can build and inspect a small relational schema directly in PostgreSQL and explain each integrity rule.

Reference reading: [PostgreSQL SQL language](https://www.postgresql.org/docs/18/sql.html).

**Steps 9–16: Queries and SQLAlchemy Core: make the SQL visible**

- [ ] **09. Filter and order rows deliberately**

  Learn: Study predicates, NULL comparisons, IN, LIKE/ILIKE, functions, casts, deterministic ORDER BY, and LIMIT.

  Apply: List active assets and unassigned tickets; include a unique tiebreaker in ordering.

  Prove: Predict results for NULL, empty strings, duplicate timestamps, and case differences.

- [ ] **10. Join related data**

  Learn: Study inner, left, and self joins, explicit ON clauses, and aliases.

  Apply: Show ticket, asset, reporter, and assignee names while retaining unassigned tickets.

  Prove: Explain why a WHERE condition on the nullable side can change the effective result of an outer join.

- [ ] **11. Aggregate data**

  Learn: Study COUNT, SUM, AVG, GROUP BY, HAVING, CASE, COALESCE, and filtered aggregates.

  Apply: Count tickets by department and priority, including departments with no tickets.

  Prove: Verify results against a tiny hand-counted fixture and distinguish COUNT(*) from COUNT(column).

- [ ] **12. Ask existence questions**

  Learn: Study scalar/correlated subqueries, EXISTS/NOT EXISTS, and set operations.

  Apply: Find assets with no tickets and technicians with assigned work; compare alternative SQL formulations.

  Prove: Explain the NULL-related trap in a NOT IN query and produce a correct alternative.

- [ ] **13. Understand the Python database layers**

  Learn: Distinguish SQLAlchemy Engine, dialect, DBAPI/psycopg driver, pool, connection, Core, and ORM.

  Apply: Configure one application Engine and inspect SQL logging in a local learning environment.

  Prove: Trace one query from Python expression through driver to PostgreSQL without confusing an Engine with a Session.

- [ ] **14. Control a Core connection and bind values**

  Learn: Use engine.connect(), engine.begin(), parameter binding, exception propagation, and resource cleanup.

  Apply: Execute a parameterized lookup and a transaction containing two related writes.

  Prove: Show that injected user text is treated as a value and that an exception rolls back both writes; explain why identifiers need separate allowlisting.

- [ ] **15. Describe and inspect schema metadata**

  Learn: Use MetaData, Table, Column, constraints, naming conventions, schemas, reflection, and inspection.

  Apply: Represent the small SQL schema in Core metadata and inspect the real database.

  Prove: Compare declared metadata with actual columns and constraints; keep reflection experiments separate from migration ownership.

- [ ] **16. Execute Core DML and understand results**

  Learn: Use select/insert/update/delete, RETURNING, Row, mappings, scalar results, and expected cardinality.

  Apply: Reproduce the SQL asset operations through Core; explicitly request returned IDs.

  Prove: Choose correctly among all(), first(), one(), one_or_none(), scalar_one(), scalars(), and mappings() for specific result shapes.

Checkpoint: You can express and execute the same small use case in SQL and SQLAlchemy Core, including bound parameters and result handling.

Reference reading: [SQLAlchemy Unified Tutorial](https://docs.sqlalchemy.org/en/21/tutorial/index.html), [SQLAlchemy SELECT tutorial](https://docs.sqlalchemy.org/en/21/tutorial/data_select.html).

**Steps 17–24: ORM fundamentals: connect objects to rows**

- [ ] **17. Define typed mapped classes**

  Learn: Use DeclarativeBase, Mapped, mapped_column, __tablename__, table constraints, and metadata registration.

  Apply: Map Department, AssetCategory, Asset, User, and MaintenanceTicket to the agreed schema.

  Prove: Explain the difference between Python typing, ORM configuration, and a constraint actually installed in PostgreSQL.

- [ ] **18. Perform ORM persistence**

  Learn: Use sessionmaker and a short-lived Session for add/get/select/update/delete.

  Apply: Implement the smallest asset CRUD functions with SQL logging enabled.

  Prove: Identify the statements emitted and close the Session reliably on success and error.

- [ ] **19. Inspect object lifecycle states**

  Learn: Understand transient, pending, persistent, deleted, detached, and the unit of work.

  Apply: Observe inspect(obj), session.new/dirty/deleted, and state changes while creating and removing a disposable asset.

  Prove: Predict an object's state at each checkpoint before executing the code.

- [ ] **20. Distinguish flush from commit**

  Learn: Study autoflush, explicit flush, commit, rollback, and recovery after failed flush.

  Apply: Flush a new ticket, force a constraint error, and recover the Session using rollback.

  Prove: Prove that flush did not make the change independently visible or durable.

- [ ] **21. Understand identity and freshness**

  Learn: Study the identity map, Session.get, expire, refresh, commit expiration, detached objects, and merge semantics.

  Apply: Load one asset through repeated gets, change it in another Session, and experiment with reloading.

  Prove: Explain Python identity versus database freshness and why merge is not a universal atomic database upsert.

- [ ] **22. Map both ends of a relationship**

  Learn: Use relationship, back_populates, scalar/collection annotations, nullability, and foreign-key direction.

  Apply: Navigate Department.assets and Asset.department, and persist linked objects.

  Prove: Explain which part is enforced by PostgreSQL and which part provides ORM navigation and synchronization.

- [ ] **23. Map multiple paths to users**

  Learn: Disambiguate reporter and assignee relationships and query their separate aliases.

  Apply: Create reporter/assignee mappings with explicit foreign_keys and a ticket detail query.

  Prove: Return both names correctly when they differ, coincide, or the assignee is NULL.

- [ ] **24. Model part usage as an association object**

  Learn: Distinguish a plain many-to-many link from a link carrying quantity and historical unit cost.

  Apply: Add WorkOrderPart with a composite work-order/part key and explicit relationships.

  Prove: Record two units of a part with a cost snapshot; prevent duplicate consolidated lines for that order/part.

Checkpoint: You can map and persist the main relationships and explain object state, emitted SQL, and transaction state separately.

Reference reading: [ORM documentation](https://docs.sqlalchemy.org/en/21/orm/index.html), [Session basics](https://docs.sqlalchemy.org/en/21/orm/session_basics.html), [Relationship patterns](https://docs.sqlalchemy.org/en/21/orm/basic_relationships.html).

**Steps 25–32: Persistence policy, migrations, and efficient reads**

- [ ] **25. Choose ownership and deletion behavior**

  Learn: Compare ORM cascades, delete-orphan, passive_deletes, and database ON DELETE actions.

  Apply: Preserve ticket/work-order history; test deletion behavior on disposable owned children.

  Prove: Predict behavior for loaded and unloaded relationships and for direct SQL deletion.

- [ ] **26. Make Alembic own the application schema**

  Learn: Use revision history, target_metadata, upgrade, downgrade, and named constraints.

  Apply: Create a clean initial application migration; retain earlier hand-written DDL only in the disposable SQL lab.

  Prove: Create a fresh database from migrations alone and inspect the installed constraints.

- [ ] **27. Evolve populated data safely**

  Learn: Study manual migration review, renames, defaults, backfills, type/status changes, and DDL locking.

  Apply: Add a required attribute to an existing populated database using a deliberate backfill sequence.

  Prove: Preserve existing data and recognize a generated add/drop pair that should have been a rename; state downgrade limits.

- [ ] **28. Choose one transaction owner**

  Learn: Understand session scope, transaction scope, autobegin, explicit begin, and composable helper functions.

  Apply: Define a use-case transaction boundary; helpers may flush but do not independently commit.

  Prove: Compose two writes plus an audit entry and show they cannot commit separately; account for earlier reads in the Session.

- [ ] **29. Build explicit ORM read queries**

  Learn: Use select on entities versus columns, projections, labels, aliases, relationships, and composable authorized filters.

  Apply: Create read functions for asset detail, department tickets, and technician assignments.

  Prove: Compare SQL and ORM outputs for missing and nullable related rows.

- [ ] **30. Paginate the ticket feed**

  Learn: Study offset and keyset pagination, stable compound ordering, and changes between requests.

  Apply: Implement created_at/id cursors and documented filter/sort combinations.

  Prove: Page through equal timestamps without duplicates in a fixed dataset and describe limitations under concurrent inserts/updates.

- [ ] **31. Observe the N+1 problem**

  Learn: Connect relationship access to query round trips and serialization behavior.

  Apply: Build a ticket page with comments and measure SELECT counts before optimizing.

  Prove: Identify the exact accesses that trigger extra SQL; retain a regression query-count test.

- [ ] **32. Choose loader strategies**

  Learn: Compare selectinload, joinedload, unique(), raiseload, load_only, defer, and explicit collection pagination.

  Apply: Optimize the fixed ticket page and construct response data while required fields are available.

  Prove: Keep queries bounded for the fixture, explain joined row multiplication, and expose accidental unloaded access.

Checkpoint: The application schema has reviewed migration history and a predictable, correctly paginated ticket query.

Reference reading: [Cascades](https://docs.sqlalchemy.org/en/21/orm/cascades.html), [Alembic tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html), [Autogenerate](https://alembic.sqlalchemy.org/en/latest/autogenerate.html), [Loading relationships](https://docs.sqlalchemy.org/en/21/orm/queryguide/relationships.html).

**Steps 33–40: Build the actual maintenance workflow**

- [ ] **33. Expose a thin API boundary**

  Learn: Separate request validation, authentication identity, business logic, persistence, and response serialization.

  Apply: Add FastAPI routes around already-understood use cases, with a Session lifecycle that matches the chosen transaction owner.

  Prove: Trace errors to the right layer and avoid duplicate commits or database I/O after cleanup.

- [ ] **34. Apply resource-scoped permissions**

  Learn: Distinguish application roles from database roles and authorization from input validation.

  Apply: Implement own-ticket access, technician assignment scope, department administration, and Super Admin policy.

  Prove: Deny cross-department reads and writes through direct API requests; do not rely on hidden UI controls.

- [ ] **35. Implement ticket transitions**

  Learn: Represent allowed states, approvals, rejection reasons, and assignment rules explicitly.

  Apply: Implement report -> assigned -> in_progress -> awaiting_verification -> closed, plus defined rejection/rework paths.

  Prove: Reject invalid transitions and an assignee who exists but is not an authorized technician.

- [ ] **36. Write a transactional audit history**

  Learn: Distinguish business audit rows from request logs and failed-attempt logging.

  Apply: Write actor/action/entity/request data in the same transaction as each successful ticket change.

  Prove: Force rollback and show neither the business change nor a success audit event survives.

- [ ] **37. Add comments and attachments**

  Learn: Model authored child records and distinguish database transactions from external file storage.

  Apply: Add comments and separate ticket/work-order attachment metadata; define upload and orphan-cleanup behavior.

  Prove: Demonstrate how failed database work avoids leaving a valid-looking attachment record pointing to missing content.

- [ ] **38. Build inventory as balance plus ledger**

  Learn: Understand stock movements, signed deltas, receipts, adjustments, and reconciliation.

  Apply: Add opening balances and receipts with a ledger row for every balance change.

  Prove: Reconcile each stored stock balance with the sum of movements, including initial quantities.

- [ ] **39. Build draft work orders and freeze historical facts**

  Learn: Define part quantities, standard-cost snapshots, labor cost, immutability, and active-order policy.

  Apply: Allow one active work order per ticket, with consolidated part lines; freeze completed costs and use a new order for later repairs.

  Prove: Changing a current price does not alter completed costs; draft quantities do not silently reserve stock.

- [ ] **40. Complete a work order atomically**

  Learn: Combine authorization, state changes, stock deduction, cost snapshots, ledger movements, and audit history.

  Apply: Implement one outer completion transaction with an explicit concurrency protocol to refine in later steps.

  Prove: A successful completion produces internally consistent stock, ledger, costs, ticket state, and audit history.

Checkpoint: The project supports authorized reporting, assignment, repair work, inventory movements, and one atomic completion use case.

Reference reading: [Session transactions](https://docs.sqlalchemy.org/en/21/orm/session_transaction.html), [PostgreSQL constraints](https://www.postgresql.org/docs/18/ddl-constraints.html).

**Steps 41–48: Prove correctness under failure and concurrency**

- [ ] **41. Inject failures into completion**

  Learn: Understand transaction atomicity, error propagation, and Session recovery.

  Apply: Raise an error after balance deduction, after a ledger insert, and before completion/audit.

  Prove: After each failure, verify all participating tables from a new connection; nothing partial remains.

- [ ] **42. Observe MVCC and READ COMMITTED**

  Learn: Understand committed visibility, statement snapshots, and long transactions.

  Apply: Use two independent connections to read, update, commit, and repeat reads in a controlled order.

  Prove: Explain every observation without assuming the ORM identity map is a PostgreSQL snapshot.

- [ ] **43. Use an atomic guarded stock update**

  Learn: Understand arithmetic UPDATE, a stock predicate, RETURNING, and the database's concurrent row-update behavior.

  Apply: Try UPDATE ... SET stock=stock-qty WHERE stock>=qty RETURNING ... with positive quantities in both connections.

  Prove: Only one competing last-unit consumption succeeds; all other writes are rolled back when completion cannot proceed.

- [ ] **44. Implement the row-lock alternative**

  Learn: Use SELECT FOR UPDATE and a shared lock protocol around parents and stock rows.

  Apply: Lock ticket, work order, and sorted part rows; require line-edit paths to lock/recheck their parent too.

  Prove: A concurrent new/edited part line cannot bypass completion's chosen protocol; compare the guarded-update design.

- [ ] **45. Handle lock ordering, deadlocks, and retries**

  Learn: Understand blocking, deadlock detection, lock/statement timeouts, and retry scope.

  Apply: Create a deliberate reversed-order deadlock, then apply consistent ordering and bounded full-transaction retry for retryable errors.

  Prove: Explain why retrying only the last SQL statement or all errors indiscriminately is incorrect.

- [ ] **46. Compare stronger isolation levels**

  Learn: Contrast REPEATABLE READ and SERIALIZABLE with READ COMMITTED and identify retry requirements.

  Apply: Repeat visibility/conflict experiments at each level and reproduce a serialization failure.

  Prove: Choose an isolation/locking strategy for the project and justify it with observed behavior.

- [ ] **47. Make completion retries idempotent**

  Learn: Use durable operation state, a unique consumption identity, and transaction-level concurrency control.

  Apply: Issue duplicate and simultaneous completion requests, including a retry after the original response is lost.

  Prove: The caller receives the existing completed outcome and no additional stock movement or cost is created.

- [ ] **48. Detect stale edits optimistically**

  Learn: Use version_id_col or explicit expected-version predicates and inspect affected results.

  Apply: Load a ticket in two Sessions and attempt conflicting administrator edits.

  Prove: One stale edit is rejected; demonstrate that bulk/Core writes need deliberate version checks too.

Checkpoint: Failures and competing requests cannot corrupt stock, duplicate consumption, or silently overwrite protected edits.

Reference reading: [Isolation](https://www.postgresql.org/docs/18/transaction-iso.html), [Locking](https://www.postgresql.org/docs/18/explicit-locking.html), [Version counters](https://docs.sqlalchemy.org/en/21/orm/versioning.html).

**Steps 49–56: Analytics and performance with evidence**

- [ ] **49. Prevent report fan-out errors**

  Learn: State input/result grain and pre-aggregate child data before joining cost totals.

  Apply: Build cost-by-department and failure-frequency reports in SQL and SQLAlchemy.

  Prove: A work order with multiple parts and ticket comments retains its correct labor and part totals.

- [ ] **50. Structure advanced reporting queries**

  Learn: Use CTEs, correlated subqueries, LATERAL, DISTINCT ON, and set operations when appropriate.

  Apply: Implement latest comment per ticket and a reusable report expression, comparing alternatives.

  Prove: Explain row cardinality, tie handling, NULL behavior, and why the selected query fits the question.

- [ ] **51. Use window functions**

  Learn: Distinguish aggregation from window calculations, partitions, ordering, frames, and rankings.

  Apply: Rank failing assets within each department and compute changes using lag().

  Prove: Choose a tie policy deliberately and explain rows versus groups in a running total.

- [ ] **52. Build time-based reports**

  Learn: Use date_trunc, explicit reporting zones, intervals, conditional aggregates, and missing-period handling.

  Apply: Produce department-month costs and repair durations, with a complete month series where required.

  Prove: Test local-midnight boundaries, open tickets, missing months, and the chosen rework-duration definition.

- [ ] **53. Choose views and materialized views**

  Learn: Distinguish reusable query definitions from persisted, refreshable results.

  Apply: Create a report view; evaluate a materialized version with a refresh/staleness policy.

  Prove: Explain refresh effects, unique row identity for ORM mapping, and why ordinary projections may suffice.

- [ ] **54. Read execution plans**

  Learn: Use EXPLAIN (ANALYZE, BUFFERS), estimates versus actuals, loops, scans, joins, sorts, and result width.

  Apply: Capture a representative slow ticket/report SELECT on a larger, unevenly distributed fixture.

  Prove: Explain where time/work is spent and identify evidence rather than assuming every sequential scan is bad.

- [ ] **55. Design workload-specific indexes**

  Learn: Compare B-tree, composite column order, partial predicates, expression indexes, and covering indexes.

  Apply: Evaluate indexes for the department's recent active-ticket queue and common FK lookups.

  Prove: Show useful before/after plans, account for write/storage cost, and reject a redundant candidate.

- [ ] **56. Measure realistic workloads**

  Learn: Use deterministic correctness fixtures, skewed larger seeds, ANALYZE, query budgets, and repeated measurements.

  Apply: Keep a benchmark note with query parameters, data distribution, plans, and observation conditions.

  Prove: Explain how cardinality estimates and skew can change an index decision; avoid tuning from a tiny fixture.

Checkpoint: Reports are correct at their declared grain and performance choices are supported by actual plans and workload measurements.

Reference reading: [SQLAlchemy query expressions](https://docs.sqlalchemy.org/en/21/tutorial/data_select.html), [Window functions](https://www.postgresql.org/docs/18/functions-window.html), [EXPLAIN](https://www.postgresql.org/docs/18/using-explain.html), [Indexes](https://www.postgresql.org/docs/18/indexes.html).

**Steps 57–64: Imports, security, operation, and final acceptance**

- [ ] **57. Import data with explicit failure policy**

  Learn: Compare batch ORM work, Core bulk INSERT, COPY/staging, ON CONFLICT, and savepoints.

  Apply: Import an asset file with duplicates and invalid records; document all-or-nothing versus per-row rejection.

  Prove: Rejected rows and accepted rows match policy; demonstrate begin_nested flushing behavior rather than assuming isolation from earlier pending changes.

- [ ] **58. Separate database ownership and runtime privileges**

  Learn: Study database roles, ownership, GRANT/REVOKE, schema access, and trusted connection configuration.

  Apply: Use a limited application role and a separate migration owner; protect credentials and exclude them from logs.

  Prove: The runtime can perform required operations but cannot make unauthorized schema changes.

- [ ] **59. Build PostgreSQL integration tests**

  Learn: Choose fixtures, real commits, separate connections, synchronization barriers, and rollback/savepoint test scope.

  Apply: Automate integrity, authorization, report, migration, and contention cases against PostgreSQL.

  Prove: State which tests require independent committed transactions; do not substitute SQLite for PostgreSQL-specific evidence.

- [ ] **60. Diagnose database maintenance and blocking**

  Learn: Distinguish VACUUM, ANALYZE, dead tuples, idle transactions, activity views, locks, and query workload statistics.

  Apply: Observe update traffic and a blocked repair; identify the blocking connection and relevant query.

  Prove: Explain the cause from PostgreSQL observations and the effect of long-lived transactions.

- [ ] **61. Budget and clean up connections**

  Learn: Use pool_size, max_overflow, checkout timeout, worker counts, connection failure handling, and transaction cleanup.

  Apply: Set a deliberate connection budget and force success/error paths through the API.

  Prove: Connections return to the pool, requests do not leave idle transactions, and exhaustion produces a controlled diagnosis.

- [ ] **62. Make deployment reproducible**

  Learn: Separate database readiness, migrations, application startup, settings, and persistent storage.

  Apply: Provide a Docker Compose setup and commands that create the database and run reviewed migrations before use.

  Prove: Start from fresh local volumes in a disposable environment and complete a repair without manual schema edits.

- [ ] **63. Practice backup and restoration**

  Learn: Understand logical dump formats, restoration targets, schema/data/roles coverage, and verification.

  Apply: Restore a backup into a separate fresh database and run integrity and cost-report checks.

  Prove: Historical costs, inventory reconciliation, and ticket relationships survive restoration.

- [ ] **64. Complete the project acceptance demonstration**

  Learn: Combine the full workflow, concurrency, reporting, migration, and recovery evidence.

  Apply: Demonstrate reporting, approval, assignment, repair, verification, last-unit contention, duplicate completion, audit review, and restored reporting.

  Prove: Rebuild one important use case without copying and explain its SQL, transaction boundary, constraints, loaders, and plan choices.

Checkpoint: Another developer can create, operate, recover, and verify the complete system using the documented process.

Reference reading: [COPY](https://www.postgresql.org/docs/18/sql-copy.html), [PostgreSQL administration](https://www.postgresql.org/docs/18/admin.html), [SQLAlchemy pooling](https://docs.sqlalchemy.org/en/21/core/pooling.html), [Backup/restore](https://www.postgresql.org/docs/18/backup.html).

**Steps 65–80: Specialist extensions: independent laboratories after the relevant core prerequisites**

- [ ] **65. JSONB and mutation tracking**

  Learn: Explore JSONB operators, containment/path queries, expression/GIN indexes, JSON null versus SQL NULL, and ORM mutation tracking. Prerequisites: 32, 54–56.

  Apply: Add varying asset specifications while preserving typed relational columns; compare replacement and nested in-place edits.

  Prove: Reload through a new Session and verify persistence; justify any JSON index with its query.

- [ ] **66. Full-text ticket search**

  Learn: Explore tsvector/tsquery, language configuration, ranking, and GIN. Prerequisites: 54–56.

  Apply: Build ranked ticket search and compare it with substring search on representative text.

  Prove: State language/tokenization behavior and measure the indexed search.

- [ ] **67. Self-reference and recursive traversal**

  Learn: Explore self-FKs, remote_side, recursive CTEs, aliases, and cycle policy. Prerequisites: 23, 50.

  Apply: Add optional equipment containment inside lab/classroom assets in a lab branch.

  Prove: Traverse descendants and define protection against cycles and invalid reparenting.

- [ ] **68. PostgreSQL-specific type and constraint laboratories**

  Learn: Explore ARRAY, native ENUM lifecycle, ranges/multiranges, domains, generated columns, and exclusion constraints in separate sub-exercises. Prerequisites: 27, 55.

  Apply: Model preventive-maintenance time windows and compare an overlap constraint with an application-only check.

  Prove: Show concurrent overlap rejection; document which remaining types are useful or unnecessary for this project's requirements.

- [ ] **69. Derived ORM attributes**

  Learn: Explore hybrid properties, column_property, SQL-expression attributes, and deferred projections. Prerequisites: 32, 49.

  Apply: Express a repair-derived value in Python and in a query, checking the SQL shape.

  Prove: Show equivalent values and reject a formulation that hides N+1 queries or incorrect aggregation.

- [ ] **70. Reusable mapping and relationship conveniences**

  Learn: Explore mixins, declarative dataclass integration, composite value objects, association_proxy, and viewonly relationships as separate experiments. Prerequisites: 24, 25.

  Apply: Try a timestamp mixin, a value object, and convenient read access through WorkOrderPart.

  Prove: Keep one authoritative writable association path and prove conveniences do not create duplicate persistence.

- [ ] **71. Inheritance and polymorphic mapping**

  Learn: Compare single-table, joined-table, and concrete inheritance with category-plus-specifications modeling. Prerequisites: 27, 32, 65.

  Apply: Model computer/projector subtypes in an isolated lab and inspect polymorphic queries.

  Prove: Explain extra joins, constraints, migration cost, and whether inheritance improves the base design.

- [ ] **72. Custom types and attribute validation**

  Learn: Explore TypeDecorator, value conversion, cache_ok decisions, validators, and custom comparators. Prerequisites: 16, 27, 54.

  Apply: Build a small domain conversion type and compare validation via Python, Core, and direct SQL.

  Prove: Round-trip values and prove that Python validators alone do not establish database integrity.

- [ ] **73. Events, triggers, and database functions**

  Learn: Explore Session/mapper/connection events, SQL/PLpgSQL functions, and row triggers in separate experiments. Prerequisites: 36, 59.

  Apply: Compare explicit audit writes with a trigger for a selected table and test ORM versus direct SQL paths.

  Prove: Explain actor propagation, transaction rollback, bulk-write coverage, and how duplicate audit entries are avoided.

- [ ] **74. Row-level security**

  Learn: Explore RLS USING/WITH CHECK, policy combinations, ownership/BYPASSRLS, and transaction-local request context. Prerequisites: 34, 58, 61.

  Apply: Add department isolation for a selected resource and test with the real limited runtime role.

  Prove: Prove another department cannot read/write and that pooled connection context does not leak between requests.

- [ ] **75. Async execution and large-result streaming**

  Learn: Explore AsyncEngine/AsyncSession, explicit I/O, one Session per task, stream/yield_per, and loader compatibility. Prerequisites: 32, 48, 61.

  Apply: Port one proven use case and export a large result without materializing everything.

  Prove: Preserve transaction tests, avoid shared concurrent Sessions, and explain driver/cursor and eager-loading limitations.

- [ ] **76. Advanced query and index laboratories**

  Learn: Compare GIN, GiST, SP-GiST, BRIN, hash, planner statistics, prepared statements, compiled SQL caches, and plan changes as separate sub-exercises. Prerequisites: 54–56.

  Apply: Use targeted JSON/search/range/time-ordered workloads rather than installing indexes indiscriminately.

  Prove: Distinguish SQL compilation caching from cached data and demonstrate one justified choice plus rejected alternatives.

- [ ] **77. Partitioning and retention**

  Learn: Explore partition pruning, partition keys, partitioned uniqueness limits, retention, and index management. Prerequisites: 55, 60, 63.

  Apply: Partition a generated audit-history lab by time and compare relevant plans and maintenance operations.

  Prove: Explain why a smaller base deployment might remain unpartitioned and verify retention/recovery behavior.

- [ ] **78. WAL, PITR, and replication**

  Learn: Study WAL durability, base backups, continuous archiving/recovery targets, physical versus logical replication, and lag in separate operations labs. Prerequisite: 63.

  Apply: Demonstrate a verified point-in-time recovery first, then inspect a replica experiment.

  Prove: Explain RPO/RTO and distinguish backups from replicas; do not claim an untested archive is recoverable.

- [ ] **79. Reliable external side effects**

  Learn: Study outbox transactions, retries, duplicate delivery, consumer idempotency, and file/object compensation. Prerequisites: 37, 47, 59.

  Apply: Record a repair-completed outbox event in the repair transaction and deliver it separately.

  Prove: A crash between database commit and delivery does not lose the event; duplicate delivery has a defined outcome.

- [ ] **80. Independent feature and reference audit**

  Learn: Practice choosing a design, finding exact API options, identifying unsupported assumptions, and updating dependencies. Prerequisite: 64 and relevant extension gates.

  Apply: Design a stock-reservation or preventive-maintenance feature from a blank page; maintain a reference coverage ledger.

  Prove: Produce requirements, schema/migration, SQL, ORM, failure tests, concurrency evidence, plans, and recovery considerations without copying the original implementation.

Checkpoint: Keep extensions only when their value and correctness are demonstrated. Use an isolated lab for alternatives that do not improve the base application.

Reference reading: [PostgreSQL reference](https://www.postgresql.org/docs/18/index.html), [SQLAlchemy Core reference](https://docs.sqlalchemy.org/en/21/core/index.html), [SQLAlchemy ORM reference](https://docs.sqlalchemy.org/en/21/orm/index.html).

**How to deepen a completed step**

Compare alternatives one at a time: raw SQL versus Core versus ORM; ordinary update versus guarded update versus row lock; lazy loading versus select-in versus joined loading; sequential scan versus indexed access; service audit versus trigger audit. Preserve correctness fixtures while changing the implementation. Record the tradeoff, not just which API was used.

When learning an API property, record its name, default, layer, purpose, observable effect, and failure case. A useful property card is:

| Field | What to record |
|---|---|
| Name | Example: relationship.passive_deletes or Session.expire_on_commit |
| Layer | PostgreSQL server / schema / SQL / Core / ORM / driver |
| Default | Read it from documentation matching the installed version |
| Question | Which project behavior might require changing it? |
| Experiment | Small isolated change with SQL/object-state observation |
| Evidence | Test, emitted SQL, query count, plan, or database inspection |
| Decision | Keep the default, configure it, or mark it irrelevant for this project |

For database constraints and concurrency, always test from a path that bypasses the ORM as well. For ORM lifecycle/loader properties, test both object state and the SQL actually sent. Do not assume a Python-side convenience protects other database writers.

**Maintain a reference coverage ledger**

Use four states: demonstrated in the project, demonstrated in an isolated lab, read but not demonstrated, and outside current scope. Classify unfamiliar reference entries as one of the last two rather than silently claiming mastery.

| Reference area | Main steps and extensions |
|---|---|
| PostgreSQL data definition, constraints, keys | 3–7, 15, 26–27, 55, 68 |
| PostgreSQL DML, SQL expressions, joins, grouping, subqueries | 8–12, 16, 29–30, 49–52, 57 |
| PostgreSQL types, operators, functions, time/localization | 4–6, 9, 52, 65, 68, 73 |
| Transactions, MVCC, locks, isolation, retries | 8, 14, 28, 40–48, 59 |
| Indexes, planner, statistics, parallel/large-data experiments | 54–56, 60, 66, 76–77 |
| Roles, privileges, authentication, schemas, RLS | 2, 7, 15, 34, 58, 74 |
| Administration, configuration, monitoring, vacuum | 2, 54, 58, 60–62, 76 |
| Backup, WAL, recovery, physical/logical replication | 63, 77–78 |
| Functions, triggers, procedural/server programming | 73; optional language/extension development remains specialist study |
| SQLAlchemy engines, connections, dialects, pooling, errors | 13–16, 28, 41, 61 |
| SQLAlchemy metadata, DDL, reflection, types | 15, 17, 26–27, 65, 68, 72 |
| SQLAlchemy expressions, operators, functions, result handling | 9–16, 29–30, 49–57, 76 |
| ORM mapping, relationships, loading, inheritance | 17–25, 29–32, 67, 69–71 |
| ORM Session, identity/state, persistence, transactions | 18–21, 28, 40–48 |
| ORM versioning, events, extensions, async | 48, 65, 69–75 |
| Migration management | 26–27, 59, 62; revisit for every schema-changing extension |

PostgreSQL C client interfaces, extension implementation in C, custom access methods, foreign-data wrapper development, server source internals, multi-database ORM sharding, and unusual two-phase transaction setups are separate specialist projects. Include them in the ledger if you choose to study them; do not complicate the college system solely to mention them.

For API flags, use the full [SQLAlchemy Core reference](https://docs.sqlalchemy.org/en/21/core/index.html) and [ORM reference](https://docs.sqlalchemy.org/en/21/orm/index.html). For PostgreSQL commands, administration, programming, and internals, use the [PostgreSQL manual](https://www.postgresql.org/docs/18/index.html). For schema history use the [Alembic tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html).

**The first concrete assignment**

Complete Step 1 before implementation:
- Write what each role can read and change, scoped to the target resource.
- Define ticket transitions, including rejection and repair rework.
- Define when inventory is consumed and whether drafts reserve stock.
- State that completed part/labor costs are immutable historical facts.
- Define what a duplicate completion request returns.
- State the expected result of two repairs competing for one part.
- Decide which records can be deleted versus retired/deactivated.

Save those decisions as the project contract, then proceed to Step 2. Marking a checklist item complete records evidence; it does not replace the experiment.

Step 1 deliverables are now available in the [project contract](PROJECT_CONTRACT.md) and [Step 1 lab](../labs/step-01/notes.md).
