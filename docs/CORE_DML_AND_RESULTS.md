# Step 16: execute Core DML and understand results

The [Step 16 lab](../labs/step-16/notes.md) performs asset CRUD using select, insert, update, and delete over Core Table objects. It uses a local adaptation of [Step 15's declarations](../labs/step-15/schema.py), with a separate disposable schema, and the existing shared application Engine. Its [executed evidence](../labs/step-16/evidence.txt) contains 38 Python checks and two independent psql checks.

## Request the values the operation must return

The lab inserts two departments, two categories, and three assets. Every fixture INSERT explicitly requests generated IDs through RETURNING. Multi-row results are associated with their business codes, rather than with an assumed return order. Generated UUIDs become the parent IDs used by later asset inserts.

```python
statement = insert(assets).values(
    asset_code="LAB-TEMP", name="Temporary Computer", location="Store Room",
    department_id=department_id, category_id=category_id,
).returning(assets.c.id, assets.c.asset_code)
created = connection.execute(statement).one()
```

This returns a Row containing the generated ID and code. The UUID has no supplied application value; its server default generates it. See [Core INSERT and RETURNING](https://docs.sqlalchemy.org/en/21/tutorial/data_insert.html#insert-returning).

The corresponding update and delete patterns are:

```python
change = (
    update(assets).where(assets.c.id == projector_id)
    .values(location="Room 204", status="under_maintenance")
    .returning(assets.c.id, assets.c.asset_code, assets.c.location, assets.c.status)
)
changed = connection.execute(change).mappings().one()

remove = delete(assets).where(assets.c.id == temporary_id).returning(assets.c.id)
removed_id = connection.execute(remove).scalar_one()
```

The equivalent PostgreSQL shapes use bound values:

```sql
UPDATE college_step16.assets
SET location = :location, status = :status
WHERE id = :asset_id
RETURNING id, asset_code, location, status;

DELETE FROM college_step16.assets WHERE id = :asset_id RETURNING id;
```

Colon placeholders illustrate value binding; the actual PostgreSQL dialect compilation in the evidence uses psycopg's parameter style. RETURNING identifies rows affected inside the current transaction; it does not commit them. The lab's final Core SELECT is also executed as equivalent raw SQL, and their exact rows must agree. See [UPDATE, DELETE, and RETURNING](https://docs.sqlalchemy.org/en/21/tutorial/data_update.html#using-returning-with-update-delete).

## Choose the result contract deliberately

| Method | Intended contract |
|---|---|
| all() | Collect all Rows; zero rows gives an empty sequence |
| first() | First Row or None; additional rows are accepted |
| one() | Exactly one Row; reject zero or multiple rows |
| one_or_none() | Optional single Row; reject multiple rows |
| scalar_one() | Exactly one row, returning its first column |
| scalars().all() | Collect one projected column across all rows |
| mappings().all() | Collect rows as named RowMapping values |

Row supports positions, labeled attributes, and `_mapping`; `dict(mapping)` produces a dictionary. Result filters select representation, while one/one_or_none enforce row cardinality. See the [Result API](https://docs.sqlalchemy.org/en/21/core/connections.html#sqlalchemy.engine.Result).

In the fixture, PC-001 is a unique lookup, MISSING has no row, and CSE has two assets. Five deliberate cardinality errors prove that required/optional single-row methods do not silently choose one of several matches. These client-side errors leave the transaction usable.

PC-002 has a present but NULL location. Selecting that field with scalar_one returns None, while one_or_none returns `(None,)`; an absent asset returns no Row. The fixture explicitly compares these cases so absence is not confused with a nullable field.

## Treat consumption and row counts separately

An exhausted all result does not replay its rows. first closes its result and discards the rest; it adds no SQL LIMIT. Add an explicit ordered limit when the SQL itself should return only the first match. Reusing the closed result raises ResourceClosedError. See [first behavior](https://docs.sqlalchemy.org/en/21/core/connections.html#sqlalchemy.engine.Result.first).

The lab verifies two non-returning UPDATEs: setting an already equal location reports one matched row, and a missing code reports zero. Such results have no rows to fetch. With RETURNING, count and verify the returned identities; do not assume rowcount is available for every driver or execution style. See [affected-row counts](https://docs.sqlalchemy.org/en/21/tutorial/data_update.html#getting-affected-row-count-from-update-delete).

The temporary asset is deleted before the CSE update, which then returns exactly PC-001 and PRJ-001. Deleting PC-002 returns its original UUID; repeating the temporary delete returns no row. These disposable assets have no ticket history. The application's history-preserving retirement policy still governs future real workflows.

One finally block rolls back schema creation, fixture inserts, and every update/delete together. A fresh checkout and independent psql confirm the schema is absent; psql also confirms the disposed Engine backend is gone. This completes the Core portion of the learning path. Typed ORM mappings begin in Step 17.
