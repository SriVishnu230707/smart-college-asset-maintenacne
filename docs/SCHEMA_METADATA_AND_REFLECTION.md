# Step 15: describe and inspect schema metadata

The [Step 15 lab](../labs/step-15/notes.md) describes departments, asset categories, and assets using SQLAlchemy Core. Its [declarations](../labs/step-15/schema.py) live in the lab, and the [verification program](../labs/step-15/python_lab.py) uses the existing shared application Engine. All database changes are rolled back.

## Keep the descriptions and the database distinct

| Object | What it represents in this exercise |
|---|---|
| MetaData | A Python registry of related Table objects |
| Table / Column | A table's intended columns, types, defaults, and constraints |
| Inspector | Database information returned by methods such as get_columns and get_foreign_keys |
| Reflected MetaData | A separate Python description loaded from the database |
| Proposed MetaData | A copy with a hypothetical additional column |

Defining these Python objects does not create database tables. Compiling CreateTable also needs no physical connection. `metadata.create_all(connection)` emits creation DDL for missing tables; it orders dependent tables after their parents. Independent parent tables can appear in either order. See [Core metadata](https://docs.sqlalchemy.org/en/21/core/metadata.html#creating-and-dropping-database-tables).

The lab uses `MetaData(schema="college_step15", naming_convention=...)`. Table registry keys are schema-qualified, such as `college_step15.assets`, and foreign-key targets include the schema. The database search_path deliberately excludes this schema during inspection. This makes explicit qualification observable. See [schema names in metadata](https://docs.sqlalchemy.org/en/21/core/metadata.html#specifying-the-schema-name).

## Declare the reduced project schema

The declarations reuse earlier choices: UUID primary keys with a server gen_random_uuid() default; bounded codes and names; independent unique business codes; false archival defaults; required department/category references; optional asset location; and a constrained asset status.

```python
metadata = MetaData(schema="college_step15", naming_convention=NAMING)
departments = Table(
    "departments", metadata,
    Column("id", Uuid, primary_key=True,
           server_default=text("gen_random_uuid()")),
    Column("code", String(20), nullable=False, unique=True),
    # The complete lab also declares name, archival state, and checks.
)
```

`assets.c.asset_code` accesses the Column object. The declaration's String(50), nullable flag, and server_default describe different properties. A Python `default` is separate from a database `server_default`.

The naming dictionary produces names including `pk_assets`, `uq_assets_asset_code`, `ck_assets_status_allowed`, and `fk_assets_department_id_departments`. Checks supply a short local name such as `status_allowed`, expanded by the convention. Stable names make inspection and future reviewed alterations clearer. See [constraint naming conventions](https://docs.sqlalchemy.org/en/21/core/constraints.html#configuring-a-naming-convention-for-a-metadata-collection).

## Compare declarations with live PostgreSQL information

The verifier creates the schema inside one explicit transaction, then calls `inspect(connection)` on that same Connection. This lets inspection see the transaction's uncommitted DDL without acquiring another checkout. It compares each table's:

- Column order, PostgreSQL type and string length, nullability, and server defaults.
- Primary-key and unique-constraint names and columns.
- Check names and the fixture's check expressions.
- Foreign-key columns, schema-qualified targets, and RESTRICT update/delete policies.
- Explicit category/department indexes, separately from unique-constraint backing indexes.

The comparison helper normalizes PostgreSQL's added text casts, parentheses, and whitespace for these fixed expressions. It is a fixture comparison, not a general SQL-equivalence or migration-diff tool. It does not establish complete coverage of arbitrary database objects or constraint options.

Reflection uses a new registry:

```python
reflected = MetaData()
reflected.reflect(bind=connection, schema="college_step15")
reflected_assets = reflected.tables["college_step15.assets"]
```

The reflected tables are different Python objects with the same persistent structure. Their foreign keys resolve to parents in their own registry. Reflection recovers the server status default but cannot recover the declaration's Python default or Table.info. It reads database information rather than reconstructing the original source. Inspector caching varies by method and dialect; the lab clears its cache after ALTER statements before comparing again. See [reflection and inspection](https://docs.sqlalchemy.org/en/21/core/reflection.html).

## Demonstrate the migration boundary

The exercise adds an undeclared `audit_note text` column and drops the status check inside the disposable transaction. Refreshed inspection detects exactly those differences. An earlier reflected registry remains a Python snapshot; a fresh reflection sees the altered structure.

A separate proposed registry adds `planned_label varchar(40)` to the intended asset definition. Calling its create_all against the existing tables emits no CREATE or ALTER statements. The planned column remains absent, audit_note remains present, and the dropped check stays absent. Schema changes need explicit, reviewed alterations and migration history; reflecting the altered database does not decide that those changes are intended. See [altering objects through migrations](https://docs.sqlalchemy.org/en/21/core/metadata.html#altering-database-objects-through-migrations).

This lab does not initialize Alembic or create a competing application schema history. Later migration lessons own that work. Both initial creation and deliberate drift roll back together. Independent psql then verifies that the schema and disposed Engine backend are absent. The [saved evidence](../labs/step-15/evidence.txt) records 29 Python checks and two independent psql checks.
