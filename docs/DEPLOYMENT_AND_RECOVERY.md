# Local deployment and recovery verification

The persistent learning PostgreSQL service uses compose.yaml and the generated .local/ credentials. Run labs/step-02/start.ps1 for readiness. Never delete its volume as a shortcut for a migration or test failure.

The separate compose.deploy.yaml manifest defines PostgreSQL, an owner-migration job and a non-owner runtime API. Secrets are mounted from COLLEGE_DEPLOY_SECRETS rather than committed environment values. The job provisions the owner/runtime logins, applies the preserved Alembic chain as owner, and grants runtime DML. API readiness probes the database after migration completion. The image runs under a non-root Unix account; persistent upload bytes use a dedicated volume.

Run labs/step-62/verify.ps1 -WriteEvidence for the reproducible fresh-deployment acceptance test. It generates an exact run-named Compose project and secret directory under .local/, uses loopback-only dynamic host ports, provisions synthetic actors, exercises real network HTTP reporting/assignment/proof/completion/verification, independently reads committed SQL, then removes only that generated project's volumes. The usual learning database is preserved. This is a verification deployment, not a promise that a server is left running afterward.

For a retained manual deployment, provision and preserve its secret files, synthetic/real actor records and bearer digests out of band; run compose.deploy.yaml with a stable project name and COLLEGE_DEPLOY_SECRETS. Do not reuse another deployment's actor token file with an empty database. Credential rotation and external identity-provider integration require a deliberate operational procedure; bootstrap does not silently rotate existing roles.

Step 63 executes pg_dump/pg_restore against a generated fresh database and verifies stock, ledger, frozen costs, audit and history triggers. It separately copies and verifies proof bytes; database dumps do not contain uploaded files. Roles and server configuration must also be provisioned separately.

Step 77 verifies partition hierarchy restoration. Step 78 creates four scratch clusters under an exact-marker temporary directory inside the PostgreSQL container: source primary, physical standby, logical subscriber and recovered target. All listen only on a private Unix socket directory, with no published recovery port. It performs a real base backup, archives WAL, restores to a named point excluding a later commit, observes both replication modes, and stops/removes all scratch resources. Existing PGDATA is never the recovery target. This lab's private trust authentication is not a production configuration.

Step 80 restores the independent optional scheduling migration and verifies its data and exclusion constraint. The core deployment deliberately does not install that prototype into public; adopting it needs a reviewed production migration, route integration and asset-transfer policy.

A replica receives unwanted writes too; it is not an independently recoverable backup. RPO/RTO, off-site storage, encryption, retention and production failover need a separate operational design and tested procedures.
