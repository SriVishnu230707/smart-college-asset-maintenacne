# Step 7: enforce referential integrity

This step turns the relationships in the [relational model](RELATIONAL_MODEL.md) into explicit reference and deletion policies. The [project contract](PROJECT_CONTRACT.md) remains the source for business rules. The [Step 7 lab](../labs/step-07/notes.md) executes the policies directly in PostgreSQL, without Python validation, then rolls everything back.

## Require valid parents without losing optional links

A foreign key connects child values to a parent key. Required links also need NOT NULL. A nullable single-column link can be absent, but any supplied ID must exist. The lab rejects both missing-parent inserts and updates. See [PostgreSQL foreign keys](https://www.postgresql.org/docs/18/ddl-constraints.html#DDL-CONSTRAINTS-FK).

| Child field | Parent key | Optional? | Named constraint |
|---|---|---|---|
| `users.department_id` | `departments.id` | Only a Super Admin may omit it | `fk_users_department` |
| `assets.department_id` | `departments.id` | No | `fk_assets_department` |
| `assets.category_id` | `asset_categories.id` | No | `fk_assets_category` |
| `maintenance_tickets.asset_id` | `assets.id` | No | `fk_tickets_asset` |
| `maintenance_tickets.reported_by_id` | `users.id` | No | `fk_tickets_reporter` |
| `maintenance_tickets.assigned_to_id` | `users.id` | Yes, before assignment or on an unassigned historical report | `fk_tickets_assignee` |
| `maintenance_tickets.department_id` | `departments.id` | No; this is department-at-report | `fk_tickets_department` |

The role/department CHECK from [Step 6](ROW_VALIDITY.md) still decides whether a user may omit membership. The foreign key separately rejects a supplied nonexistent department. Reporter and assignee are distinct references to the same users table; neither replaces the other.

All seven project links choose `ON DELETE RESTRICT ON UPDATE RESTRICT`, with the default `NOT DEFERRABLE` timing. Referenced UUID identities remain stable. An ordinary update to a non-key attribute, such as `is_active`, does not delete or change that identity.

For example:

```sql
assigned_to_id uuid,
CONSTRAINT fk_tickets_assignee FOREIGN KEY (assigned_to_id)
    REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT
```

The nullable assignee retains an existing technician's ID on a closed ticket. Deactivating that user preserves the link; deleting the user is rejected. The application must still guard deactivation while active assignments or work orders exist.

## Choose preservation for project history

| Record with history | Chosen operation | What its reference policy protects |
|---|---|---|
| Asset | Retire | Tickets keep their asset identity |
| Reporter or technician | Deactivate after assignment guards succeed | Tickets retain reporter/assignee identities |
| Department | Archive after active-resource checks succeed | Users/assets and historical ticket attribution remain resolvable |
| Category | Archive after active-resource checks succeed | Assets retain their classification |

The lab isolates parent edges so every failed delete has one expected named constraint. It tests departments referenced by assets, users, and historical tickets separately, plus category, asset, reporter, and technician deletion.

RESTRICT prevents deletion while a child references the row. It does not ban deletion of every unreferenced record, make tickets append-only, or prevent someone from first removing children. Preserving all tickets, authorization, guarded archival, and immutable history still require later application/privilege enforcement. The lab's retirement/deactivation updates demonstrate reference preservation, not a complete authorized workflow.

## Keep recorded department independent of current ownership

The ticket has separate foreign keys to its asset and its recorded department. Do not force `(ticket.asset_id, ticket.department_id)` to match an asset's current `(id, department_id)` pair.

In the executed fixture, both existing tickets are terminal. The asset and its former CSE users move to ECE. The old tickets still refer to CSE, so deleting CSE fails even though no current user or asset belongs there. Retiring the asset, deactivating its historical users, and archiving its old department/category preserve all references.

Creation-time department capture, transfer preconditions, historical-field immutability, and competing-transfer protection remain later use-case responsibilities. A foreign key to the department ensures existence; it does not prove the right department was captured.

## Match a composite reference as a whole

For a future reference to a work-order/part line, both values must identify one existing pair. The comparison parent contains `(1, 10)` and `(2, 20)`. The pair `(1, 20)` is invalid even though both components appear somewhere in the parent table.

```sql
FOREIGN KEY (order_no, part_no)
    REFERENCES part_line_key_probe(order_no, part_no) MATCH FULL
```

| Child pair | MATCH SIMPLE, the default | MATCH FULL |
|---|---|---|
| A complete existing pair | Accept | Accept |
| A complete missing pair | Reject | Reject |
| Both NULL | Accept | Accept |
| Exactly one NULL | Skip the parent match | Reject |

Make both columns NOT NULL when the link is mandatory. Composite targets need an eligible unique parent key; the probe uses a composite primary key. A foreign key to department display names fails DDL because no uniqueness guarantee exists, even though the small fixture happens to contain different names. See [CREATE TABLE reference and MATCH rules](https://www.postgresql.org/docs/18/sql-createtable.html).

These numbered comparison keys are teaching fixtures, not the project's entity-ID policy. Application IDs remain UUIDs. The probes do not install work orders or inventory movements.

## Compare ON DELETE choices

| Action | Executed comparison outcome | Project choice for the seven identity/history links |
|---|---|---|
| RESTRICT | Refuse a referenced-parent delete | Selected |
| NO ACTION, the default | The nondeferrable comparison refuses a referenced-parent delete | Use explicit RESTRICT here |
| CASCADE | Delete the child with the parent | Would erase these historical links/rows |
| SET NULL | Keep the child and clear its nullable link | Would erase the recorded relationship |
| SET DEFAULT | Keep the child and use an existing fallback parent | Would replace historical attribution |

SET NULL still fails against NOT NULL; SET DEFAULT still needs a valid target. Both failures leave the parent and child unchanged. These alternatives run only on isolated comparison tables. See [referential actions](https://www.postgresql.org/docs/18/sql-createtable.html).

NO ACTION can defer its check when declared DEFERRABLE and set deferred; RESTRICT's parent action cannot be deferred. This lab selects immediate project constraints and tests immediate NO ACTION. Deferred transaction experiments remain later work. See [SET CONSTRAINTS](https://www.postgresql.org/docs/18/sql-set-constraints.html).

## Inspect diagnostics and supporting indexes

Observed on the pinned PostgreSQL 18.6 server:

| SQLSTATE | Lab operation |
|---|---|
| `23503` | Missing-parent write, invalid composite match, or failed NO ACTION/SET DEFAULT reference |
| `23001` | Referenced-parent deletion/key update refused by RESTRICT |
| `23502` | NULL required link, including SET NULL on a required child column |
| `42830` | Foreign-key DDL targeting non-unique department names |

The verifier checks these exact codes and named foreign keys; NOT NULL failures identify their columns. Do not assume every reference-related rejection uses `23503`. See [official error codes](https://www.postgresql.org/docs/18/errcodes-appendix.html) and the [executed evidence](../labs/step-07/evidence.txt).

Parent primary keys supply unique indexes. PostgreSQL does not automatically index child foreign-key columns. The project examples explicitly add seven child-reference indexes; later query-plan work will assess the full indexing design. See [foreign-key indexing](https://www.postgresql.org/docs/18/ddl-constraints.html#DDL-CONSTRAINTS-FK).

The lab inspects table descriptions and `pg_constraint` definitions, including delete/update actions and validation/deferral flags. All 43 checks passed, including 28 expected rejections. It does not make active/archived status, eligible technician role, ticket transitions, audit history, or concurrent workflows safe by reference constraints alone.
