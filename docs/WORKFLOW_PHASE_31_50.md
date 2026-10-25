# Loaders, workflow, concurrency, and reporting: Steps 31-50

Each lesson has an isolated PostgreSQL proof, independent observation and cleanup, saved evidence, and a separate commit.

## Step 31: Measure lazy relationship queries

A three-ticket page records its 1+N comment SELECTs and detached serialization failure.

The comment table has a reviewed migration and RESTRICT history references. Loading the ticket list does not load its collections; each first comments access issues SQL, including the empty collection. Count statements with fresh Sessions so the identity map cannot hide round trips. Step 32 optimizes this same fixture. See [relationship loading](https://docs.sqlalchemy.org/en/21/orm/queryguide/relationships.html).

Verification: 18 checks in both PowerShell 7 and Windows PowerShell 5.1. [Notes](../labs/step-31/notes.md), [executed evidence](../labs/step-31/evidence.txt).

## Step 32: Bound relationship loading

The fixed ticket page uses two SELECTs, while joined loading, raiseload, deferred columns, and collection paging have explicit proofs.

Select-in loading avoids joined row multiplication. Joined collection results require unique(); this deduplicates ORM parents rather than reducing SQL rows. Response DTOs are constructed before Session close. Parent limits do not bound child collection size, so large comment histories use the separately scoped comment_page query. See [loader options](https://docs.sqlalchemy.org/en/21/orm/queryguide/relationships.html) and [column loading](https://docs.sqlalchemy.org/en/21/orm/queryguide/columns.html).

Verification: 21 checks in both PowerShell 7 and Windows PowerShell 5.1. [Notes](../labs/step-32/notes.md), [executed evidence](../labs/step-32/evidence.txt).

## Step 33: Expose the thin HTTP boundary

FastAPI reads validate requests, resolve opaque bearer identity, authorize database scope, and serialize values inside one operation transaction.

Request validation returns 422, missing/invalid credentials 401, inactive actors 403, absent scoped rows 404, domain filter errors 400, and integrity conflicts 409. Request Sessions always close and response values need no database work afterward. Opaque token digests and aware expiry live in an ignored file; tokens are provisioned out of band for this local example. No client role or actor ID is trusted. See the API operation guide in docs/API.md and [FastAPI security](https://fastapi.tiangolo.com/tutorial/security/first-steps/).

Verification: 23 checks in both PowerShell 7 and Windows PowerShell 5.1. [Notes](../labs/step-33/notes.md), [executed evidence](../labs/step-33/evidence.txt).

## Step 34: Enforce resource-scoped permissions

Direct API requests prove own-ticket, assigned-technician, department-admin, and Super Admin boundaries for reads and mutations.

Creation derives reporter and department on the server. Original text requires the current-department reporter and open state; triage requires an in-scope administrator. Historical read access after transfer never grants mutation access. Archived departments and retired assets reject new reports. The read policy reuses server-derived scope; unauthorized details conceal resource existence. Database roles are distinct from these application roles.

Verification: 25 checks in both PowerShell 7 and Windows PowerShell 5.1. [Notes](../labs/step-34/notes.md), [executed evidence](../labs/step-34/evidence.txt).

## Step 35: Enforce explicit ticket transitions

Administrative transitions validate eligible assignees, rejection reasons, rework and verification conditions, and terminal-state conflicts.

Ticket-row locks serialize these administrative commands. Approval and assignment are one operation. Reassignment rejects existing orders; only active same-department technicians qualify. Verification/rework require completed work and no active order. Repair start and completion are intentionally work-order commands, implemented in Steps 39-40; this lesson uses explicit synthetic repair-state fixtures to test the administrator edges. A reviewed revision preserves separate verification and rework notes.

Verification: 23 checks in both PowerShell 7 and Windows PowerShell 5.1. [Notes](../labs/step-35/notes.md), [executed evidence](../labs/step-35/evidence.txt).

## Step 36: Commit business audit with changes

Every implemented ticket mutation records actor, target, request, department, time, and change details inside its owning transaction.

A fault injected after the business flush but before audit persistence rolls back both; a fresh independent connection verifies the result. Failed attempts are operational failures, not successful business history. Administrator audit reads enforce ticket/department scope. No history edit/delete endpoint exists; database append-only history protection is added with the completed-work guards in Step 39.

Verification: 18 checks in both PowerShell 7 and Windows PowerShell 5.1. [Notes](../labs/step-36/notes.md), [executed evidence](../labs/step-36/evidence.txt).

## Step 37: Authorize comments and private attachments

Authored append-only comments and separate ticket/work-order attachments follow their parent permissions; upload failures compensate staged bytes.

Bytes are private local objects with random validated keys, size limits and SHA-256 verification; downloads are authenticated and force attachment disposition. The database records ownership, uploader, filename, media type, size and digest. An upload writes bytes first, verifies them, then commits metadata and audit together. A database failure removes its own staged object; a process crash may leave an orphan, handled separately with an age grace period and referenced-key scan. Garbage collection must run in a maintenance window or with uploads paused; it is not a distributed storage transaction. Completed-proof protection is strengthened in Step 39.

Verification: 22 checks in both PowerShell 7 and Windows PowerShell 5.1. [Notes](../labs/step-37/notes.md), [executed evidence](../labs/step-37/evidence.txt).

## Step 38: Reconcile stock with a movement ledger

Opening balances, supplier receipts, and reasoned adjustments update stock and append signed movements in one transaction.

Only Super Admin manages central stock. Zero opening stock creates no movement; positive stock creates one opening entry. Row locks serialize balance changes, negative balances are rejected, and failure after the balance flush rolls back the ledger and balance together. A reviewed migration adopts any pre-existing positive balance as a clearly marked legacy opening, without inventing a human actor; all new commands require a real actor. Partial unique indexes protect opening and consumption identities. Movement immutability is added in Step 39.

Verification: 23 checks in both PowerShell 7 and Windows PowerShell 5.1. [Notes](../labs/step-38/notes.md), [executed evidence](../labs/step-38/evidence.txt).

## Step 39: Manage drafts and protect repair history

Assigned technicians manage one active order, consolidated part lines and exact labor estimates; drafts reserve nothing and completed facts reject edits.

Ticket/order locks protect create/start/edit/discard and child changes. Discarding a draft removes its metadata and leaves bytes for age-gated orphan collection. Stored estimates become final snapshots at the successful completion introduced in Step 40. This lesson uses a synthetic completed fixture to isolate price-history and immutability proofs. Reviewed database triggers protect completed parents and both old/new parents of child moves; audit, inventory and comment history reject UPDATE/DELETE. Direct SQL proofs bypass the ORM. The study installs the exact frozen revision guard, while Alembic owns the application installation.

Verification: 23 checks in both PowerShell 7 and Windows PowerShell 5.1. [Notes](../labs/step-39/notes.md), [executed evidence](../labs/step-39/evidence.txt).

## Step 40: Complete repairs in one transaction

Authorized completion verifies proof, locks stock, captures final prices, consumes parts, and commits work order, ticket, ledger and audit as one result.

The initial protocol locks ticket, order and sorted stock rows. Every part must be available, proof bytes must match metadata, and exact per-repair totals must fit numeric(12,2). Child snapshots flush before the parent becomes immutable. Completion accepts no editable fields; costs in the returned stable-shaped result are decimal strings. A labor-only zero-cost repair remains valid. Later steps inject failures, compare stock protocols, prove contention, and add durable retry semantics; no cross-request snapshot or retry claim is inferred from this single-success proof.

Verification: 22 checks in both PowerShell 7 and Windows PowerShell 5.1. [Notes](../labs/step-40/notes.md), [executed evidence](../labs/step-40/evidence.txt).

## Step 41: Prove completion rollback at fault boundaries

Four injected failures and a real unique-constraint failure leave all seven participating tables unchanged, as read independently after rollback.

The private test-only checkpoint seam is unavailable through HTTP. Faults fire after balance/price flush, after ledger insertion, before completion, and after audit insertion. PostgreSQL fingerprints retain exact numeric JSON text rather than float conversions. A multi-part shortage consumes nothing; a new authorized correction permits a fresh successful attempt. The transaction context propagates errors, rolls back, closes the Session, and returns its checkout.

Verification: 23 checks in both PowerShell 7 and Windows PowerShell 5.1. [Notes](../labs/step-41/notes.md), [executed evidence](../labs/step-41/evidence.txt).

## Step 42: Observe READ COMMITTED visibility

Two real backend connections prove committed statement snapshots, own-write visibility, rollback, and the separate behavior of ORM identity-map caching.

An uncommitted write is invisible to the other reader. After its commit, a later statement in an already-open READ COMMITTED transaction sees the new row version. An existing Python entity can remain stale until refresh even though a column projection is fresh. No ORM cache is treated as a PostgreSQL isolation snapshot. Every explicit transaction is ended before independent observation. See [PostgreSQL isolation](https://www.postgresql.org/docs/18/transaction-iso.html).

Verification: 21 checks in both PowerShell 7 and Windows PowerShell 5.1. [Notes](../labs/step-42/notes.md), [executed evidence](../labs/step-42/evidence.txt).

## Step 43: Use guarded arithmetic stock updates

Completion uses stock=stock-quantity with stock>=quantity and RETURNING; two technicians on independent backends compete for one unit and only one commits.

A positive-quantity guard is enforced before SQL. RETURNING captures the price while the arithmetic update owns the stock-row lock. PostgreSQL blocking is observed with pg_blocking_pids, then the winner is released; the waiter rechecks the predicate after the commit. The losing complete transaction leaves its order unfinished and creates no consumption or audit. Sorted part IDs, parent locks, exact cost validation and rollback remain part of the overall protocol. The contention harness uses an explicitly separate NullPool test Engine so the one-slot learning pool cannot accidentally serialize the test before PostgreSQL does.

Verification: 18 checks in both PowerShell 7 and Windows PowerShell 5.1. [Notes](../labs/step-43/notes.md), [executed evidence](../labs/step-43/evidence.txt).

## Step 44: Prove the parent and row-lock protocol

Completion can lock sorted stock rows explicitly, while concurrent edited and newly inserted part lines wait for parent protection and reject completed work.

Every service child edit locks/rechecks ticket then order, including proof changes and draft deletion. Completion holds those parents before selecting line membership and sorted parts. PostgreSQL blocking is observed for both an existing-line edit and a new-line insert; neither bypasses the frozen set. A direct SQL completed-child insert is independently rejected by the reviewed trigger. The application default remains guarded arithmetic; the internal stock_strategy option compares equivalent row-lock behavior and is not client-selectable.

Verification: 16 checks in both PowerShell 7 and Windows PowerShell 5.1. [Notes](../labs/step-44/notes.md), [executed evidence](../labs/step-44/evidence.txt).

## Step 45: Order locks and retry whole transactions

A real reversed-order deadlock is observed; consistent ordering succeeds, and only serialization/deadlock errors trigger bounded full-transaction retries.

Retryable SQLSTATEs are 40001 and 40P01. Each attempt reauthorizes and reruns all reads/writes in a fresh Session; rollback/close precede bounded backoff. Business conflicts, integrity failures, arbitrary SQL errors and ambiguous connection failures are not retried indiscriminately. Completion HTTP now delegates transaction ownership to this retry owner rather than opening a second request transaction. Exhausted retryable database errors return a controlled 503 without SQL parameters. See [explicit locking](https://www.postgresql.org/docs/18/explicit-locking.html).

Verification: 18 checks in both PowerShell 7 and Windows PowerShell 5.1. [Notes](../labs/step-45/notes.md), [executed evidence](../labs/step-45/evidence.txt).

## Step 46: Compare stronger transaction isolation

Repeatable Read retains a snapshot and can abort stale row updates, while Serializable rejects a demonstrated two-row write-skew history.

The availability predicate is a clearly isolated teaching fixture encoded in asset location, not a new application requirement. Both disjoint Repeatable Read writes commit; Serializable rejects one with 40001, requiring full transaction retry. SQLAlchemy isolation configuration is set before autobegin and resets on pool return. The project keeps READ COMMITTED with explicit ticket/order/stock protection, guarded arithmetic and bounded deadlock/serialization retries; stronger isolation is not treated as a replacement for state, authorization or idempotency rules. See [PostgreSQL isolation](https://www.postgresql.org/docs/18/transaction-iso.html).

Verification: 19 checks in both PowerShell 7 and Windows PowerShell 5.1. [Notes](../labs/step-46/notes.md), [executed evidence](../labs/step-46/evidence.txt).

## Step 47: Make completion durably idempotent

Duplicate, simultaneous, discarded-response, and rollback-waiting completion requests resolve one durable work-order operation without duplicate stock or audit.

Authorization precedes result disclosure. Ticket and order locks serialize the operation; completed status resolves the frozen outcome before unfinished-state checks, even after closure or rework. Only the owning currently assigned technician or a scoped administrator with completed-work read permission may retrieve it. Administrators still cannot initiate unfinished completion. Unique consumption identities and immutable child snapshots support the durable result; current ticket state, stock, display names and catalog prices are excluded. Two real-backend races prove commit and rollback behavior.

Verification: 24 checks in both PowerShell 7 and Windows PowerShell 5.1. [Notes](../labs/step-47/notes.md), [executed evidence](../labs/step-47/evidence.txt).

## Step 48: Reject stale edits optimistically

Ticket mapper versions and required HTTP expected versions reject stale report/priority edits; explicit Core predicates demonstrate the bulk-write boundary.

Two independently loaded entities prove ORM StaleDataError and preservation of the winner. Core DML without a version predicate bypasses mapper protection, so that counterexample is rolled back; a qualified predicate matches zero stale rows. The API returns current versions, requires positive expected_version on protected edits, and emits no success audit for rejected changes. Earlier permission/audit HTTP fixtures now supply the new transport field while preserving their original assertions. A reviewed migration backfills version 1 for existing rows. See [SQLAlchemy version counters](https://docs.sqlalchemy.org/en/21/orm/versioning.html).

Verification: 20 checks in both PowerShell 7 and Windows PowerShell 5.1. [Notes](../labs/step-48/notes.md), [executed evidence](../labs/step-48/evidence.txt).

## Step 49: Aggregate reports before child joins

Hand-counted cost and failure reports avoid parts/comments fan-out, exclude unfinished estimates, and retain recorded department history.

Parts first aggregate to one row per work order, then completed work to one row per department. Comments and proof never join those money aggregates. The naive fixture totals 137.00 incorrectly; raw SQL and SQLAlchemy correctly return 52.00. SUM(DISTINCT amount) is not a repair for fan-out because legitimate equal amounts may belong to different rows. Zero-cost completed repairs count, empty departments retain zero totals, and failures count tickets at department/asset grain. The transfer fixture closes every ticket before moving its asset and proves historical costs remain with ticket.department_id. Report APIs permit only scoped department administrators or Super Admin.

Verification: 19 checks in both PowerShell 7 and Windows PowerShell 5.1. [Notes](../labs/step-49/notes.md), [executed evidence](../labs/step-49/evidence.txt).
