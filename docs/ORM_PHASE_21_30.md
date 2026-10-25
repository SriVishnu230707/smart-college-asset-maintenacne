# ORM relationships, migrations, and reads: Steps 21-30

Each requested lesson is verified and pushed separately. Historical column-only lessons remain reproducible as the application model evolves.

## Step 21: Identity and freshness

Identity-map reuse, expire/refresh, commit expiration, detached access, and merge are verified against independent committed writes. A deterministic merge race proves it is not atomic upsert.

The experiment distinguishes Python identity from READ COMMITTED database freshness. Expire defers loading; refresh loads immediately. Merge copies available state and may select then insert, so uniqueness still belongs to PostgreSQL. The source remains detached/transient. The deterministic independent insert between merge and flush raises 23505 without overwriting its winner. See [Session state management](https://docs.sqlalchemy.org/en/21/orm/session_state_management.html).

Verification: 22 checks in both PowerShell versions. [Predictions](../labs/step-21/notes.md), [evidence](../labs/step-21/evidence.txt).
