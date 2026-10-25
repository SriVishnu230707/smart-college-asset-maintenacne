# Loaders, workflow, concurrency, and reporting: Steps 31-50

Each lesson has an isolated PostgreSQL proof, independent observation and cleanup, saved evidence, and a separate commit.

## Step 31: Measure lazy relationship queries

A three-ticket page records its 1+N comment SELECTs and detached serialization failure.

The comment table has a reviewed migration and RESTRICT history references. Loading the ticket list does not load its collections; each first comments access issues SQL, including the empty collection. Count statements with fresh Sessions so the identity map cannot hide round trips. Step 32 optimizes this same fixture. See [relationship loading](https://docs.sqlalchemy.org/en/21/orm/queryguide/relationships.html).

Verification: 18 checks in both PowerShell 7 and Windows PowerShell 5.1. [Notes](../labs/step-31/notes.md), [executed evidence](../labs/step-31/evidence.txt).
