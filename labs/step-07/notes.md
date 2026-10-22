# Step 7: enforce referential integrity

Read the [reference and deletion decisions](../../docs/REFERENTIAL_INTEGRITY.md) first. This lab proves required/optional relationships and history-preserving deletion policy directly through psql.

## Run the lab

Use the [Step 2 PostgreSQL environment](../step-02/notes.md). With Docker Desktop running, execute from PowerShell in the project directory:

```powershell
.\labs\step-02\start.ps1
.\labs\step-07\verify.ps1 -WriteEvidence
```

The [verifier](verify.ps1) needs no Python or new package. It runs [query.sql](query.sql), then [reconnect.sql](reconnect.sql) in a fresh authenticated psql connection. It writes [evidence.txt](evidence.txt) only after both succeed. Omit `-WriteEvidence` to print the result without replacing the saved transcript.

For interactive exploration:

```powershell
docker compose exec postgres sh /labs/step-02/psql.sh
```

```sql
\i /labs/step-07/query.sql
\i /labs/step-07/reconnect.sql
\quit
```

The SQL refuses to touch an existing `college_step07` schema. Within one transaction it creates five reduced project tables, three composite-reference probes, and six deletion-action probes. Everything, including indexes and the verification helper, is rolled back. This is a reference-policy lesson, not permanent application-schema installation.

## Trace the valid reference graph

- PRJ-001 belongs to CSE and the PROJECTOR category; PC-001 belongs to ECE and COMPUTER.
- The CSE student reported two retained terminal ticket snapshots: one closed with a technician reference, one rejected without an assignee. Omitted repair, reason, and audit details belong to later lessons.
- A Super Admin has NULL department membership; every supplied non-NULL department must still exist.
- Each of the seven project foreign keys explicitly restricts parent deletion and key updates. Seven explicit child-reference indexes are also inspected.

The foreign key verifies a selected assignee's identity. It does not check technician role, activation, same-department eligibility, or valid state transitions. These remain business-workflow rules from the [contract](../../docs/PROJECT_CONTRACT.md).

## Explain all 28 expected rejections

| Attempt(s) | Expected constraint or column | SQLSTATE on PostgreSQL 18.6 | Count |
|---|---|---|---|
| User with a missing non-NULL department | `fk_users_department` | `23503` | 1 |
| Asset with missing department; missing category | `fk_assets_department`; `fk_assets_category` | `23503` | 2 |
| Ticket with missing asset, reporter, assignee, recorded department | `fk_tickets_asset`, `fk_tickets_reporter`, `fk_tickets_assignee`, `fk_tickets_department` | `23503` | 4 |
| NULL required asset department; NULL required ticket asset | `department_id`; `asset_id` | `23502` | 2 |
| Update asset category; ticket assignee to missing parents | `fk_assets_category`; `fk_tickets_assignee` | `23503` | 2 |
| Update the UUID of a referenced asset | `fk_tickets_asset` | `23001` | 1 |
| Create FK to department names without a unique target key | Invalid FK definition | `42830` | 1 |
| Delete department used only by an asset; only by a user | `fk_assets_department`; `fk_users_department` | `23001` | 2 |
| Delete referenced category, asset, reporter, technician | `fk_assets_category`, `fk_tickets_asset`, `fk_tickets_reporter`, `fk_tickets_assignee` | `23001` | 4 |
| Delete original department after asset/users transfer elsewhere | `fk_tickets_department` | `23001` | 1 |
| Mixed parent pair `(1, 20)` with SIMPLE; FULL | `fk_simple_reference`; `fk_full_reference` | `23503` | 2 |
| One NULL component under MATCH FULL, in either position | `fk_full_reference` | `23503` | 2 |
| Delete a referenced composite parent pair | `fk_full_reference` | `23001` | 1 |
| Delete the referenced fallback parent used by SET DEFAULT | `fk_default_child` | `23503` | 1 |
| SET NULL when the child column is required | `parent_id` | `23502` | 1 |
| Delete a parent under default nondeferrable NO ACTION | `fk_no_action_child` | `23503` | 1 |

The `expect_rejection` helper actually executes each literal SQL operation. Its nested exception block rolls back the rejected statement and checks structured diagnostics. Unexpected codes, wrong named constraints/columns, or accepted invalid operations fail the lab. NOT NULL errors on this server report the column and leave the constraint-name field empty.

RESTRICT specifically reports `23001`; missing-parent writes and the NO ACTION comparison report `23503`. The original output records the difference. See [PostgreSQL error codes](https://www.postgresql.org/docs/18/errcodes-appendix.html). psql diagnostic notices and results can interleave across stdout/stderr.

## Trace history and the comparison tables

Both existing tickets are terminal before the illustrated transfer. PRJ-001 and its historical users move from CSE to ECE. Both tickets still record CSE, so deleting CSE fails through `fk_tickets_department`. The fixture then retires the asset, deactivates the historical users, and archives the old department/category. The joins still resolve every ticket reference.

These raw updates illustrate references. They do not implement authorization, active-assignment/archival guards, creation-time department capture, immutable historical fields, or audit writes. Foreign keys alone also do not forbid inserting a new reference to an archived parent or retired asset.

The composite parent contains `(1, 10)` and `(2, 20)`. Each complete child pair must match one row. SIMPLE also accepts `(999, NULL)` because one component is NULL; FULL rejects either partial-NULL form while accepting both NULLs. Required pairs would need NOT NULL on both components.

The deletion comparison uses independent synthetic rows: CASCADE removes its child; SET NULL preserves a child with no parent link; SET DEFAULT redirects a child to existing parent 0. Attempting to delete parent 0 then fails because the resulting default would dangle. SET NULL on a required link also fails. Assertions confirm failed actions leave their parent/child rows intact.

## Recorded outcome

The live run passed on 22 October 2026: **43 PostgreSQL checks**, including 28 expected rejections and 15 successful assertions for the graph, history, composite references, deletion outcomes, catalog/index policy, unchanged fixtures, and cleanup. See [captured evidence](evidence.txt). All demonstration objects were rolled back, and a fresh connection confirmed the schema was absent.

## Explain before advancing

1. What does a foreign key guarantee, and what does NOT NULL add?
2. Why can an unassigned ticket use NULL but not a nonexistent user ID?
3. Which named constraint rejects each delete above, and why are the department cases isolated?
4. Why retain a deactivated technician's identity on a closed ticket?
5. Why does the recorded department need an independent FK instead of a composite link to current asset ownership?
6. Why is `(1, 20)` invalid even though 1 and 20 appear separately in the composite parent?
7. How do SIMPLE and FULL differ for one or two NULL components?
8. Why do SET NULL and SET DEFAULT still have to satisfy other constraints?
9. How do RESTRICT and immediate NO ACTION differ in the observed SQLSTATE? When could NO ACTION be deferred?
10. Why add child-reference indexes explicitly, and which authorization/history rules remain outside their scope?

Continue with Step 8 in the [learning path](../../docs/LEARNING_PATH.md) when you can explain the proof without copying it.
