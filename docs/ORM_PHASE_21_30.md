# ORM relationships, migrations, and reads: Steps 21-30

Each requested lesson is verified and pushed separately. Historical column-only lessons remain reproducible as the application model evolves.

## Step 21: Identity and freshness

Identity-map reuse, expire/refresh, commit expiration, detached access, and merge are verified against independent committed writes. A deterministic merge race proves it is not atomic upsert.

The experiment distinguishes Python identity from READ COMMITTED database freshness. Expire defers loading; refresh loads immediately. Merge copies available state and may select then insert, so uniqueness still belongs to PostgreSQL. The source remains detached/transient. The deterministic independent insert between merge and flush raises 23505 without overwriting its winner. See [Session state management](https://docs.sqlalchemy.org/en/21/orm/session_state_management.html).

Verification: 22 checks in both PowerShell versions. [Predictions](../labs/step-21/notes.md), [evidence](../labs/step-21/evidence.txt).

## Step 22: Bidirectional department and asset relationships

Department.assets and Asset.department synchronize in Python and persist their foreign key, while direct SQL independently enforces parent existence.

The application uses typed relationship/back_populates declarations. PostgreSQL still owns NOT NULL and foreign-key existence. A transfer here uses only a disposable asset without tickets; full transfer authorization is a later workflow. Historical Steps 17-20 now import a frozen column-only snapshot, preserving their original observations as the application registry evolves. See [relationship patterns](https://docs.sqlalchemy.org/en/21/orm/basic_relationships.html).

Verification: 19 checks in both PowerShell versions. [Predictions](../labs/step-22/notes.md), [evidence](../labs/step-22/evidence.txt).

## Step 23: Separate reporter and assignee paths

Explicit foreign_keys map reporter and optional assignee separately; aliased projections correctly handle different users, the same user, and no assignee.

Reporter and assignee relationships each identify their local FK and inverse collection. The detail projection uses two aliased User entities and an outer join for the nullable assignee. Fixtures use valid assigned/open states; these mappings alone do not authorize assignment. See [multiple join paths](https://docs.sqlalchemy.org/en/21/orm/join_conditions.html#handling-multiple-join-paths).

Verification: 17 checks in both PowerShell versions. [Predictions](../labs/step-23/notes.md), [evidence](../labs/step-23/evidence.txt).

## Step 24: Part usage association objects

WorkOrderPart explicitly maps consolidated quantities and exact historical unit costs between work orders and catalog parts; duplicate lines and invalid values are rejected.

WorkOrder, SparePart, and WorkOrderPart extend application metadata with named RESTRICT references, numeric money, stock bounds, and a partial unique active-work-order index. Association objects carry their own data and relationships; no competing secondary many-to-many collection is mapped. Completion eligibility, inventory movements, and immutable completed work are later workflows, not implied by this mapping. See [association objects](https://docs.sqlalchemy.org/en/21/orm/basic_relationships.html#association-object).

Verification: 20 checks in both PowerShell versions. [Predictions](../labs/step-24/notes.md), [evidence](../labs/step-24/evidence.txt).

## Step 25: Ownership and deletion policies

Application references preserve ticket and work-order history for loaded, unloaded, and direct SQL deletion paths; delete-orphan and CASCADE are demonstrated only on disposable owned children.

History-bearing parent collections use passive_deletes="all" and retain RESTRICT foreign keys; they have no delete/delete-orphan cascade. A separate lab-only Parent/Child model compares all, delete-orphan with passive_deletes=True and ON DELETE CASCADE. These ownership examples never apply destructive cascading to application history. Full immutable-completion workflows remain later work. See [cascade policies](https://docs.sqlalchemy.org/en/21/orm/cascades.html).

Verification: 23 checks in both PowerShell versions. [Predictions](../labs/step-25/notes.md), [evidence](../labs/step-25/evidence.txt).

## Step 26: Alembic application schema ownership

A frozen initial Alembic revision creates a genuinely empty database, installs named constraints, and owns the application schema; the application database is upgraded to the reviewed head.

The initial revision contains explicit DDL, not a call to mutable application metadata. env.py takes target_metadata and an optional caller-owned connection; the ini stores no URL or password. A narrowly named scratch database is provisioned with the ignored admin credential, migrated as college_learner, closed, and dropped without FORCE. Normal application upgrades run as the learner and preserve public data. Use `.venv/Scripts/alembic.exe -c alembic.ini upgrade head`. See [Alembic tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html). Downgrade is destructive and is exercised only in disposable databases in later proofs.

Verification: 25 checks in both PowerShell versions. [Predictions](../labs/step-26/notes.md), [evidence](../labs/step-26/evidence.txt).

## Step 27: Safe evolution of populated data

A reviewed migration backfills a required condition note and truly renames a populated part-name column; original identities and data survive, and downgrade information loss is demonstrated only in a scratch database.

Revision 0002 uses nullable add, deterministic backfill, NOT NULL/default/check, and ALTER COLUMN RENAME. SparePart.name remains the Python attribute while the database column becomes display_name. A five-second lock timeout bounds unexpected blocking; real large deployments still require reviewed lock/backfill scheduling and backups. App migrations only move forward; downgrade is exercised solely on a narrowly named disposable database. See [manual autogenerate review](https://alembic.sqlalchemy.org/en/latest/autogenerate.html).

Verification: 22 checks in both PowerShell versions. [Predictions](../labs/step-27/notes.md), [evidence](../labs/step-27/evidence.txt).

## Step 28: One transaction owner

One use-case owner commits asset, ticket, and audit together; composable helpers only flush, and existing autobegun reads must be resolved explicitly.

Persistence primitives do not authorize callers; the later API/business layer must validate roles and lifecycle eligibility before invoking them. The owner encloses reads and writes, returns primitive IDs before expiration, and propagates errors. An existing read transaction is never secretly committed. Audit storage has its own reviewed revision and RESTRICT references. See [Session transaction framing](https://docs.sqlalchemy.org/en/21/orm/session_transaction.html).

Verification: 20 checks in both PowerShell versions. [Predictions](../labs/step-28/notes.md), [evidence](../labs/step-28/evidence.txt).
