# Smart College Asset & Maintenance Management System

A working FastAPI/PostgreSQL maintenance backend and an **80-step SQLAlchemy/PostgreSQL learning project**. All 80 checklist steps have implementations or written business proofs, verification evidence, and individual completion commits. Progress follows understanding rather than a schedule.

Start with the [numbered learning path](docs/LEARNING_PATH.md), [project contract](docs/PROJECT_CONTRACT.md), and [mastery guide](docs/POSTGRESQL_SQLALCHEMY_MASTERY.md). Each lab contains notes, executable proofs, and captured evidence. [Steps 51–80](docs/CONTINUATION_51_80.md) record the latest continuation. [Reference coverage](docs/REFERENCE_COVERAGE.md) distinguishes application features, isolated specialist labs, and further study.

## Application

- Student, Technician, Department Admin and Super Admin identities with resource-scoped authorization and local opaque bearer credentials.
- Asset/ticket relationships, ticket lifecycle, comments, private attachment metadata and proof bytes.
- Work orders, immutable completed costs, suppliers, stock movements, reconciliation and transactional audit history.
- Atomic completion, real PostgreSQL contention/isolation proofs, durable completion retries and optimistic edits.
- Department cost/failure reports, deterministic latest comments, ranked failures, zero-filled monthly costs and scoped full-text search.
- Reviewed Alembic history, finite connection settings and a fresh local container deployment with separate migration owner/runtime login.

The specialist labs cover JSONB, inheritance, composites/dataclasses, custom types, functions/triggers, RLS, async streaming, index alternatives, partitions, real PITR/replication, simulated outbox delivery and an independent preventive-booking prototype. Optional prototypes remain isolated rather than silently changing the core schema. There is no React frontend or public identity-provider integration in this deliverable.

## Run the project and lessons

Use Docker Desktop, Python 3.11+ (verified with 3.12.14), and PowerShell 7 or Windows PowerShell 5.1. In this directory:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\labs\step-02\start.ps1
.\labs\step-51\verify.ps1 -WriteEvidence
.\tests\run.ps1 -WriteEvidence
```

Substitute any implemented lesson number for 51. The full regression runner starts PostgreSQL, runs all 79 executable labs sequentially, checks exact assertion counts, tests runner failure paths, and confirms study-schema cleanup. Step 1 is a written contract/proof exercise.

The final full suites in PowerShell 7 and Windows PowerShell 5.1 each record **1769 lab checks plus 14 runner checks (1783 checks)**. Every new step was also verified individually in both installed shells. Ten-step debug checkpoints ran in both shells for 51–60, 61–70 and 71–80. See [test instructions](tests/README.md), [PowerShell 7 full-suite evidence](tests/evidence-powershell7.txt), [PowerShell 5.1 full-suite evidence](tests/evidence-powershell5.txt), and [debug review](docs/DEBUG_CHECKPOINTS.md).

```powershell
.\tests\debug-batch.ps1 -FromStep 51
.\tests\debug-batch.ps1 -FromStep 61
.\tests\debug-batch.ps1 -FromStep 71
```

Start the local API after migrations, then provision identities/credentials as described in the [API guide](docs/API.md):

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m uvicorn college_maintenance.api:app --host 127.0.0.1 --port 8000
```

The default learning database is college_learning, login college_learner, at 127.0.0.1:55432. This learner owns its study/application schema. The separate [deployment proof](labs/step-62/notes.md) builds a fresh Compose API/PostgreSQL project with distinct owner/runtime roles and removes only its generated test volumes afterward. See [deployment/recovery notes](docs/DEPLOYMENT_AND_RECOVERY.md).

Credentials, bearer digests, uploads, operational archives, local process logs and the virtual environment stay under ignored .local/ or .venv/. Preserve these if retaining a local deployment. No force-push or history reset is used. Historical phase guides and earlier full-suite snapshots remain as lesson-specific records.
