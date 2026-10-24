# Step 17: define typed mapped classes

The [application models](../college_maintenance/models.py) now define Department, AssetCategory, Asset, User, and MaintenanceTicket. One DeclarativeBase owns their shared MetaData and mapper registry. The [Step 17 lab](../labs/step-17/notes.md) verifies all five mappings, creates their tables only in a disposable namespace, and tests PostgreSQL enforcement without a Session.

## Separate the three layers

| Layer | What it provides | Observed limit |
|---|---|---|
| Python annotations | Describe intended Python values for typing tools | An annotation alone does not reject an invalid assignment |
| ORM mapping | Connects instrumented class attributes to Table columns and mapper properties | Constructing an object does not install a table or validate every field |
| Installed PostgreSQL schema | Enforces declared NOT NULL, uniqueness, CHECK, and foreign-key rules on writes | Only installed constraints protect SQL writers |

The lab creates a plain annotated class that accepts None, then constructs a mapped Department with a noncanonical code and missing name. Neither action sends SQL. The generated ORM constructor rejects unknown attribute names, but it accepts those invalid values. See [mapped-class construction and inspection](https://docs.sqlalchemy.org/en/21/orm/mapping_styles.html#mapped-class-behavior).

## Read the declaration

The models use this pattern:

```python
class Department(Base):
    __tablename__ = "departments"
    __table_args__ = (
        CheckConstraint("name !~ '^[[:space:]]*$'", name="name"),
        # The application definition also constrains canonical codes.
    )
    id: Mapped[UUID] = mapped_column(
        Uuid, primary_key=True, server_default=text("gen_random_uuid()")
    )
    code: Mapped[str] = mapped_column(String(20), unique=True)
    name: Mapped[str] = mapped_column(String(150))
    is_archived: Mapped[bool] = mapped_column(server_default=text("false"))
```

Mapped describes the Python attribute; mapped_column supplies the database/mapper configuration. `__tablename__` names the table. `__table_args__` supplies table-level constraints, whose names are expanded by Base's naming convention. These class definitions register Tables immediately, without database I/O. See [declarative table configuration](https://docs.sqlalchemy.org/en/21/orm/declarative_tables.html).

The mappings infer required columns from Mapped[str], Mapped[UUID], and Mapped[bool]. Optional annotations such as Mapped[UUID | None] infer nullable columns. Explicit SQL types retain the chosen string lengths and timezone-aware timestamps. Inspection of both mapper and installed database verifies those choices in this lab.

Server defaults run on database inserts. A newly constructed Department has no generated UUID or archival value yet. The lab inserts through the mapped Table with Core and verifies UUID generation and false archival defaults. Session persistence is the next lesson.

## Map the agreed five entities

| Entity | Fields and guards represented now |
|---|---|
| Department | UUID; unique canonical code; required nonblank name; archival flag |
| AssetCategory | UUID; unique canonical code; required nonblank name; archival flag |
| User | UUID; unique normalized email; display name; hash field; allowed role; optional department with role-dependent presence; activation |
| Asset | UUID; unique canonical code; required name/category/department; allowed status; optional location |
| MaintenanceTicket | UUID; asset/reporter/optional assignee; department-at-report; title/description; required priority; status; creation and later lifecycle instants; optional rejection reason |

The five tables contain 36 columns. Every entity has a server-generated UUID primary key. User role and ticket priority deliberately have no default. Tickets default to open, assets to active, and creation uses CURRENT_TIMESTAMP. Later event instants are nullable until those events occur; all four event columns use timestamp with time zone.

All seven identity references retain ON DELETE/UPDATE RESTRICT and supporting indexes. Reporter and assignee remain separate foreign-key columns. Ticket department is an independent historical reference, rather than a composite link forcing equality with the asset's current owner. The [reference-policy guide](REFERENTIAL_INTEGRITY.md) explains those decisions.

These are initial column mappings and row/reference guards. Relationship navigation is introduced in Steps 22–23. Assignment eligibility, lifecycle transitions and conditional event completeness, historical immutability, authentication, and resource permissions still belong to later workflow enforcement. A password_hash column does not implement login or hashing.

## Install a disposable proof, then bypass the mapper

The application metadata has no fixed lab schema and performs no creation at import. The lab translates unqualified Table schema names into college_step17 on one Connection, then runs create_all inside its explicit transaction. Only five lab-qualified CREATE TABLE statements may appear. Inspector calls and raw SQL use that namespace explicitly; schema translation does not rewrite literal SQL. See [schema-name translation](https://docs.sqlalchemy.org/en/21/core/connections.html#translation-of-schema-names).

Inspection compares column order, types, lengths, nullability, defaults, primary/unique keys, named checks, all seven foreign keys, and supporting indexes. Valid Core inserts prove database defaults, nullable Super Admin membership, and ticket creation time. Eleven direct-SQL rejections then prove that real constraints protect writes independently of ORM configuration.

Each expected rejection checks SQLSTATE plus the source table and exact constraint or column diagnostic. Savepoints isolate these verification failures; no Session is created. The entire schema transaction rolls back afterward, and independent psql verifies schema removal and writer disposal. The [evidence](../labs/step-17/evidence.txt) records 46 Python checks and two independent psql checks. Permanent schema installation remains owned by the later migration lessons.
