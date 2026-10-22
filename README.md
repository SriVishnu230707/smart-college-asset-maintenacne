# Smart College Asset & Maintenance Management System

Learn PostgreSQL and SQLAlchemy by building a college maintenance system one step at a time.

Steps 1 and 2 are available. The [project contract](docs/PROJECT_CONTRACT.md) defines the business rules; the [Step 1 lab](labs/step-01/notes.md) contains worked acceptance examples. The [Step 2 lab](labs/step-02/notes.md) starts a PostgreSQL learning database and records real connection, inspection, rollback, and reconnection evidence.

Start here:

1. Read the [project contract](docs/PROJECT_CONTRACT.md).
2. Work through the [Step 1 proofs](labs/step-01/notes.md).
3. Run the [Step 2 database lab](labs/step-02/notes.md), then continue with Step 3 in the [learning path](docs/LEARNING_PATH.md).

With Docker Desktop running, use PowerShell in this project directory:

```powershell
.\labs\step-02\start.ps1
.\labs\step-02\verify.ps1 -WriteEvidence
docker compose exec postgres sh /labs/step-02/psql.sh
```

The database is `college_learning`, with the non-superuser login `college_learner`. PostgreSQL is published on `127.0.0.1:55432`. Credentials are generated locally under the Git-ignored `.local/` directory. See the [captured verification output](labs/step-02/evidence.txt).

The [mastery guide](docs/POSTGRESQL_SQLALCHEMY_MASTERY.md) explains how later SQL, ORM, transaction, and reporting lessons connect to the project.

Current deliverable: the business contract and a running, verified PostgreSQL learning environment. Application tables, SQLAlchemy models, API routes, and business-rule enforcement follow in later learning steps.
