# Step 13 lab: understand the Python database layers

Read the [database-layer guide](../../docs/PYTHON_DATABASE_LAYERS.md), then follow the trace in [python_lab.py](python_lab.py). This implements Step 13 of the [learning path](../../docs/LEARNING_PATH.md). It introduces Core connectivity while leaving mapped models and ORM persistence to later lessons.

## Install the pinned dependencies

Use an installed Python 3.10+ interpreter to create an ignored project environment. From the project root in PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
.\labs\step-02\start.ps1
.\labs\step-13\verify.ps1 -WriteEvidence
```

Use the actual interpreter path instead of `python` if that command is a Windows Store alias. The [root requirements](../../requirements.txt) include [this lab's SQLAlchemy/psycopg pins](requirements.txt) and Step 5's timezone dependency, so the same environment can run the full suite. No package is installed by the verifiers themselves.

The recorded environment used Python 3.12.14, SQLAlchemy 2.1.6, psycopg 3.3.6, and psycopg-binary 3.3.6. The binary extra supplies the development client libraries. See [psycopg installation](https://www.psycopg.org/psycopg3/docs/basic/install.html).

The [shared Python resolver](../shared/verify.ps1) prefers a usable project virtual environment, then normal PATH interpreters, then an existing bundled interpreter. It skips Windows Store aliases during automatic selection and checks versions/imports before connecting. An explicit interpreter is respected:

```powershell
.\labs\step-13\verify.ps1 -PythonExecutable C:\path\to\python.exe -WriteEvidence
```

If the published port changes, set COLLEGE_POSTGRES_PORT consistently before starting Compose and running the lab. Credentials are read privately from ignored `.local/`; they are not command arguments or tracked configuration values.

## Predict the observations

| Question | Prediction |
|---|---|
| Does importing the application's Engine open a physical connection? | No; checked-in and checked-out counts are zero |
| Does compiling the Core expression connect? | No; it creates PostgreSQL SQL plus bound parameters |
| Which dialect and DBAPI are selected? | PostgreSQL dialect with psycopg 3 |
| Is the Engine a Session? | No; no Session instance is created |
| What does engine.connect return? | A SQLAlchemy Connection wrapping a borrowed psycopg connection |
| Which cursor executes the probe? | A real psycopg.Cursor |
| What database/role does PostgreSQL return? | college_learning / college_learner |
| Which application name and timezone does PostgreSQL report? | college_step13 / UTC |
| Does the driver PID agree with the SELECT result? | Yes |
| Does closing the first SQLAlchemy Connection close the driver connection? | No; the pool retains it |
| Are sequential Connection wrappers the same Python object? | No |
| Do those wrappers use the same Engine and driver connection? | Yes, in this controlled run |
| Physical connect / checkout / checkin event counts | 1 / 2 / 2 |
| Invalid SELECT 1 / 0 | PostgreSQL 22012 -> psycopg DivisionByZero -> SQLAlchemy DataError |
| Can the connection be used after explicit rollback? | Yes, the recovery SELECT returns recovered |
| What does final disposal close here? | The returned physical connection |
| What does independent psql find afterward? | Engine PID absent; no Step 13 schema |

The [application module](../../college_maintenance/database.py) defines the one shared Engine. The script's short sys.path setup lets this standalone lab import that module even when launched from another working directory. Production packaging and API startup are not implemented here.

## Read the trace and proof code

The probe selects the lesson marker, server database/role, backend PID, application name, timezone, and server version. It creates no schema or data rows. Event handlers record the actual compiled statement and parameters at the cursor boundary, then capture server column metadata. Those handlers are observation scaffolding; the driver and server still perform execution normally.

SQL echo is enabled only by the lab. Automatic parameter values stay hidden, while the custom trace deliberately prints the fixed public probe strings. Password absence is asserted separately. Initialization SQL, implicit BEGIN, and ROLLBACK are expected log entries; they do not indicate a separate Engine per query.

The invalid SELECT is caught only as the expected SQLAlchemy DataError with the original psycopg SQLSTATE 22012. An accepted invalid query, different exception, mismatched result, or failed cleanup makes the process fail. The Python `check` helper raises explicitly rather than depending on Python assert statements that optimization can disable.

After Python returns, [reconnect.sql](reconnect.sql) receives only the recorded backend PID. It uses a different psql connection and proves that Engine disposal closed the original backend. Guard failures use the [shared SQL exception handler](../shared/fail.sql), so they return nonzero.

## Recorded result and learning gate

The live run on **24 October 2026** passed **23 checks**: 21 Python observations/assertions and two independent psql checks. The [saved evidence](evidence.txt) includes real Engine SQL logs, compiled parameters, cursor type, server-returned PID, balanced pool events, the expected error path, and independent connection cleanup. No application table or mapped ORM model is created.

Explain the Engine, dialect, pool, SQLAlchemy Connection, physical psycopg connection, DBAPI cursor, server, and ORM Session without treating them as interchangeable. Trace the tagged SELECT in both directions and explain why two checkouts can use one physical connection. Identify what happens on wrapper closure, error rollback, and final disposal.

Continue with Step 14 when you can explain the trace and reproduce it without copying its expected observations.
