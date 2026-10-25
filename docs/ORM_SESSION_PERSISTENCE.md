# ORM persistence with short-lived Sessions

Historical scope: Steps 17-20 use the [frozen column-only model snapshot](../labs/shared/column_models.py) so their original mapping and SQL predictions remain reproducible. Current application mappings evolve from Step 22 onward.


Step 18 persists the [typed Asset mapping](../college_maintenance/models.py) through the ORM. The [shared Session factory](../college_maintenance/sessions.py) uses the existing Engine; the [small CRUD helpers](../labs/step-18/asset_crud.py) practice on disposable study data. Run the [lab](../labs/step-18/notes.md) and compare its SQL trace with the [Core CRUD lesson](CORE_DML_AND_RESULTS.md).

## Own the Session at the operation boundary

`SessionFactory = sessionmaker(bind=engine)` stores configuration. Each call creates a new Session; importing the factory or constructing an unused Session does not check out a connection. The Engine and its pool are shared, while each operation owns its Session. Keep the default autoflush and commit expiration behavior for this lesson. [Session basics](https://docs.sqlalchemy.org/en/21/orm/session_basics.html).

Use a read context for a lookup and a transaction context for an operation that must commit. The following example assumes the lesson's tables and parent IDs already exist:

```python
from college_maintenance.sessions import SessionFactory

# create_asset is the lesson-local helper in labs/step-18/asset_crud.py.
with SessionFactory() as session, session.begin():
    asset = create_asset(
        session, asset_code="PC-001", name="Lab Computer",
        department_id=department_id, category_id=category_id,
        location="Computer Lab 1",
    )
    asset_id = asset.id
```

The inner transaction commits on successful exit or rolls back when an exception propagates. The outer context closes the Session. `with SessionFactory() as session:` by itself closes resources but does not commit pending writes. The lab proves both paths using fresh readers. [Transaction contexts](https://docs.sqlalchemy.org/en/21/orm/session_transaction.html).

Copy primitive IDs or response values while the Session is open. The example captures its generated UUID before commit. Commit normally expires ORM attributes; accessing an object after its Session closes can require loading that is no longer possible. The later identity/freshness lesson examines this behavior in detail. [Session API](https://docs.sqlalchemy.org/en/21/orm/session_api.html).

## Keep helpers small and transaction ownership explicit

Every helper borrows the caller's Session. It neither commits nor closes that Session, so the caller can group several writes into one atomic operation.

| Helper | ORM operation | Result contract |
|---|---|---|
| create_asset | Construct Asset, add, flush | Asset with generated UUID and status |
| get_asset | Session.get(Asset, id) | Asset or None |
| list_assets | Session.scalars(select(Asset)) | Ordered list of Asset objects; optional department filter |
| update_asset_location | Get, assign location, flush | Asset or None |
| delete_fixture_asset | Get, Session.delete, flush | True if found; False if absent |

Explicit flushes let this introductory helper return generated values and expose database failures before it returns. The caller still owns commit. Step 20 studies autoflush, flush versus commit visibility, and recovery of a failed Session. This lab lets errors leave the context, then opens a new Session for verification.

The delete helper is deliberately lesson-local and named for disposable fixtures. The [project contract](PROJECT_CONTRACT.md) retains asset history through retirement. These helpers do not implement actor authorization, production retirement, or ticket workflows.

## Compare attempted SQL with committed data

Each measured operation starts with a fresh Session. The cursor event records asset statement kinds; metadata/setup statements are excluded from this comparison. These are the observed sequences in [saved evidence](../labs/step-18/evidence.txt):

| Operation | Asset SQL attempted | Durable outcome |
|---|---|---|
| Create two assets | INSERT, INSERT | PC-001 and LAB-TEMP committed |
| Get one asset | SELECT | Returns a mapped Asset |
| List all, then by department | SELECT, SELECT | Ordered objects, with the requested filter |
| Update location | SELECT, UPDATE | PC-001 moves to Computer Lab 2 |
| Delete temporary fixture | SELECT, DELETE | LAB-TEMP removed |
| Missing get/update/delete | SELECT, SELECT, SELECT | None / None / False; no write |
| Create without commit | INSERT | NO-COMMIT rolled back on close |
| Application error after writes | SELECT, UPDATE, INSERT | Both changes rolled back |
| Duplicate code after update | SELECT, UPDATE, INSERT | Both changes rolled back; 23505 / uq_assets_asset_code |
| Delete referenced asset | SELECT, DELETE | KEEP-001 retained; 23001 / fk_tickets_asset |

The last INSERT and DELETE above are attempted statements that fail. An emitted statement alone does not prove a committed change. PostgreSQL's RESTRICT violation here is `23001`; missing-parent foreign-key failures in earlier labs are `23503`. The code checks structured driver diagnostics, not translated error text. [PostgreSQL error codes](https://www.postgresql.org/docs/18/errcodes-appendix.html).

Local `engine.echo = True` records SQL and BEGIN/COMMIT/ROLLBACK while `hide_parameters=True` suppresses automatic bound-value logging. Assertions check all four CRUD statement types, hidden-parameter markers, and absence of the actual learner password and synthetic fixture hash. This does not redact arbitrary SQL literals, manually printed values, or all possible error output. Logging is restored in finally; credentials stay in ignored `.local/`.

## Verify resource release and independent visibility

The lab checks successful reads/writes, close without commit, a propagated application exception, a duplicate-code error, and reference-protected deletion. It verifies no remaining Session transaction or mapped identity entries, balanced pool checkout/checkin events, and zero checked-out connections. Session.close resets a Session by default and permits later reuse; there is no public Session.closed flag. Each operation here creates a distinct Session and does not reuse it. [Session close semantics](https://docs.sqlalchemy.org/en/21/orm/session_api.html#sqlalchemy.orm.Session.close).

Only the lab's OptionEngine translates unqualified model tables to `college_step18`; it shares the application Engine's pool. The fixture must be committed so the independent psql observer can inspect it after Python exits. No permanent application schema is installed. The final committed assets are exactly KEEP-001 and PC-001, and the original ticket still references KEEP-001. Fresh ORM reads, Core SQL, and psql all agree.

The PowerShell verifier always attempts cleanup in finally. Cleanup requires the learner identity, schema ownership, and the exact run UUID recorded in lab_run. A different UUID demonstrably exits 3 with SQLSTATE 22023 without removing anything. Known tables are dropped child-first in one transaction without CASCADE; a fresh connection confirms schema absence. Python closes every Session and disposes the Engine even if an assertion fails.

Step 18 is complete when you can explain the factory versus the Session, predict each observed SQL sequence, distinguish emitted SQL from committed state, and reproduce successful/error cleanup. Object lifecycle states, detailed flush recovery, identity freshness, relationships, migrations, and full application workflows remain later steps.
