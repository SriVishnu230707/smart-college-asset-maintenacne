# Step 3: design the relational model

The deliverable is the [relational model](../../docs/RELATIONAL_MODEL.md): five core entities, an entity-relationship diagram, cardinalities, functional dependencies, normalization decisions, and the ticket's historical department rule.

## Learn through a concrete asset

Start with a projector:

1. Its department's identity/name belongs in `departments`.
2. Its shared category belongs in `asset_categories`.
3. The particular projector belongs in `assets`, linked to that department and category.
4. A student account and a technician account are separate rows in `users`.
5. Each reported problem is a separate `maintenance_tickets` row linked to the asset, reporter, optional assignee, and department at report time.

This lets a department, user, category, or asset exist before any ticket exists. It also avoids repeating the department name, category name, reporter email, or technician contact details in each issue report.

## Run the SQL demonstration

Use the PostgreSQL environment from [Step 2](../step-02/notes.md). From PowerShell in the project directory:

```powershell
.\labs\step-02\start.ps1
.\labs\step-03\verify.ps1 -WriteEvidence
```

Or inspect the SQL directly in `psql`:

```powershell
docker compose exec postgres sh /labs/step-02/psql.sh
```

```sql
\i /labs/step-03/query.sql
\quit
```

[query.sql](query.sql) creates only a disposable `college_step03` schema, with two departments, two categories, four users, four assets, and three tickets after the transfer example. It uses synthetic `example.invalid` email addresses and no authentication data. Primary keys and ordinary foreign keys make its relationships inspectable; this is a reduced model probe, not the complete application schema or its workflow enforcement.

The five tables, fixtures, and transfer are all inside one transaction and rolled back. The script refuses to touch a pre-existing `college_step03` schema. [reconnect.sql](reconnect.sql) checks the cleanup through a fresh connection, and [verify.ps1](verify.ps1) saves successful credential-free output to `evidence.txt` when requested.

## What the proof demonstrates

| Observation | Why it matters |
|---|---|
| Three computers share one category row and may share the same display name | Category identity is reusable; asset identity is independent of display text |
| A Super Admin has no department; every asset still has one | Optionality belongs to each relationship, not every foreign key indiscriminately |
| Reporter and assignee join to distinct users, with unassigned reports retained | Two foreign keys to the same table express different roles |
| An old rejected projector ticket stays in CSE after the projector transfers to ECE | Recorded department is a historical event fact |
| A new report on the transferred projector records ECE | Capture current ownership for each new report, rather than rewriting old reports |
| Two bad copies of one supplier's current contact disagree | Repeated supplier details permit an update anomaly |
| Two part references resolve through one supplier contact record | Store the supplier fact once and reference its identity |
| Searching a comma-separated string for PART-1 also matches PART-10 | Encoded relationship lists make exact identity lookup fragile |
| Individual part-use rows find only PART-1 and carry its own quantity | A junction/association row gives each relationship an identity and attributes |
| Rollback and reconnection find no model-probe schema | The exercise leaves the learning database ready for the next lesson |

The rejected ticket is a synthetic history fixture with a rejection reason. It is terminal before the transfer, as required by the contract. The assigned computer ticket concerns a different asset and does not block the projector's transfer. SQL inserts stand in for previously authorized workflow actions; this exercise does not claim to implement approvals, audits, or permission enforcement.

The supplier and part examples use query-local `VALUES` datasets, not installed inventory tables. They explain why the later model uses `suppliers`, `spare_parts`, `work_orders`, and `work_order_parts` rather than supplier copies and part-list strings on tickets.

## Recorded outcome

The live exercise passed on 22 October 2026 with 11 successful verification checks. See [evidence.txt](evidence.txt) for the original PostgreSQL output, including the five-table description, separate user relationships, CSE/ECE historical snapshot, normalization counterexamples, and successful rollback/reconnection cleanup. Permanent application tables and workflow enforcement have not been installed by this exercise.

## Explain the normalization proof

**Supplier details:** a supplier's current contact depends on the supplier's identity. Repeating it in every ticket permits contradictory values, prevents onboarding without a ticket, and risks losing the supplier when the last ticket is removed. Keep supplier contacts in their own entity and reference them through the appropriate part/receipt relationships.

**Part lists:** a work order may consume many parts, and a part may occur in many work orders. The relationship itself owns quantity and historical unit cost. Model one `work_order_parts` row per `(work_order_id, spare_part_id)` rather than parsing a ticket string. Normalized rows support exact equality, individual references, and per-use data.

**Historical department:** the ticket's department depends on the report, not on the asset's current department for all time. A snapshot is meaningful when its timing and immutability are explicit. Do not use an always-equal composite foreign key to force historical tickets to follow asset transfers.

## Check your understanding

1. Can a department, category, user, or asset exist with no tickets? Explain the diagram's zero-to-many ends.
2. Which user-department link may be absent, and for which application role?
3. Why are `reported_by_id` and `assigned_to_id` separate even though both reference `users.id`?
4. Does a valid user foreign key prove the assignee is an eligible technician?
5. Which key determines a supplier's current contact? Which composite key determines quantity used?
6. Why does adding an `id` column fail to fix repeated supplier contacts?
7. If an asset transfers to ECE, which department should an old CSE ticket and its future cost report use?
8. Why do parts belong to work orders rather than directly to tickets?

The written design and executed model instances are the Step 3 deliverables. Explaining these decisions yourself remains the learning gate. Continue with Step 4 in the [learning path](../../docs/LEARNING_PATH.md) to study identifier generation, business keys, ordinary types, and duplicate asset codes.
