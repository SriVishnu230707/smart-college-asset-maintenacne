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
