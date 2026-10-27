# Reference coverage and independent feature decisions

The checklist records executed demonstrations, not a claim that a learner has memorized every API option. Review each step's code, notes, and evidence, then reproduce it independently.

| Area | Application | Isolated laboratories |
|---|---|---|
| Data integrity | Departments, roles, assets, tickets, costs, inventory and audit | Domains, arrays, ranges, generated values and alternate types |
| SQL and ORM | Typed mappings, sessions, association objects, queries and migrations | Reflection drift, inheritance, composites, dataclasses and custom types |
| Analytics | Scoped feeds, latest comments, costs, ranked failures, monthly costs and full-text API | Loader/index alternatives, views/materialized views and JSONB mutation |
| Concurrency | Atomic repair completion, guarded stock, immutable facts, idempotency and optimistic edits | Independent-backend isolation/locks, hierarchy protocols and exclusion constraints |
| Security | Opaque local bearer credentials, resource permissions, separated deployment owner/runtime | Actual non-owner RLS and context cleanup |
| Operations | Local Compose API, readiness, migrations and finite pools | Real restore/PITR, physical and logical replication in disposable clusters |
| Extensions | Hybrid part totals and scoped search expressions | Async streaming, partition retention, simulated outbox and independent scheduling |

Step 80 designs a preventive-maintenance slot booking prototype independently of repair completion. It includes a handwritten versioned SQL migration, typed models, authenticated scoped API, stale-version cancellation, durable request keys, actual independent-backend contention, a captured plan, and real backup/restore.

Its invariants are administration-only scheduling, asset department scope, aware increasing half-open intervals, one stable asset key, no overlap among scheduled slots, cancellation freeing a slot, duplicate keys retaining their original resource, rejection of changed key payloads, and no success audit after failed writes. Built-in range GiST operator classes and a generated integer asset span avoid requiring a global btree_gist extension. The small fixture's plan is recorded without a production speed claim.

The optional scheduling API/schema remain under labs/step-80. They are not silently enabled in the core deployment. Adoption needs a reviewed public Alembic revision, an asset-transfer policy for future appointments, route integration and deployment acceptance. The core migration history is preserved.

The outbox consumer is local and simulated; no external message is sent. Recovery and replication demonstrations are real but are not a production HA/SLA installation. PostgreSQL C/extension implementation, server internals, ORM sharding and unusual two-phase configurations remain further reference study.

References: [PostgreSQL](https://www.postgresql.org/docs/18/index.html), [Core](https://docs.sqlalchemy.org/en/21/core/index.html), [ORM](https://docs.sqlalchemy.org/en/21/orm/index.html), [Alembic](https://alembic.sqlalchemy.org/en/latest/).
