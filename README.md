# Smart College Asset & Maintenance Management System

Learn PostgreSQL and SQLAlchemy by building a college maintenance system one step at a time.

Steps 1-4 are available. The [project contract](docs/PROJECT_CONTRACT.md) and [Step 1 lab](labs/step-01/notes.md) define the business rules. The [Step 2 lab](labs/step-02/notes.md) starts and inspects PostgreSQL. The [relational model](docs/RELATIONAL_MODEL.md) and [Step 3 lab](labs/step-03/notes.md) explain entities and normalization. The [Step 4 decisions](docs/IDENTIFIERS_AND_TYPES.md) and [lab](labs/step-04/notes.md) verify identifiers, business keys, and ordinary types.

Start here:

1. Read the [project contract](docs/PROJECT_CONTRACT.md).
2. Work through the [Step 1 proofs](labs/step-01/notes.md).
3. Run the [Step 2 database lab](labs/step-02/notes.md).
4. Study and run the [Step 3 relational-model lab](labs/step-03/notes.md).
5. Run the [Step 4 identifier/type lab](labs/step-04/notes.md), then continue with Step 5 in the [learning path](docs/LEARNING_PATH.md).

With Docker Desktop running, use PowerShell in this project directory:

```powershell
.\labs\step-02\start.ps1
.\labs\step-02\verify.ps1 -WriteEvidence
.\labs\step-03\verify.ps1 -WriteEvidence
.\labs\step-04\verify.ps1 -WriteEvidence
docker compose exec postgres sh /labs/step-02/psql.sh
```

The database is `college_learning`, with the non-superuser login `college_learner`. PostgreSQL is published on `127.0.0.1:55432`. Credentials are generated locally under the Git-ignored `.local/` directory. See the [captured verification output](labs/step-02/evidence.txt).

Step 3's [captured model-verification output](labs/step-03/evidence.txt) demonstrates its design and normalization examples. The SQL probe leaves no persistent application tables behind.

Step 4's [captured identifier/type output](labs/step-04/evidence.txt) proves a fresh UUID cannot bypass a duplicate asset code, alongside generator, string, and boolean comparisons. Its probe is also rolled back.

The [mastery guide](docs/POSTGRESQL_SQLALCHEMY_MASTERY.md) explains how later SQL, ORM, transaction, and reporting lessons connect to the project.

Current deliverable: the business contract, a running PostgreSQL learning environment, a verified relational model, and identifier/type decisions with executed examples. Permanent application tables, SQLAlchemy models, API routes, and full business-rule enforcement follow in later learning steps.
