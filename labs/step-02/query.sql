\set ON_ERROR_STOP on
\pset pager off
\echo === Connection and server ===
\conninfo
SELECT pg_backend_pid() AS connection_backend_pid \gset
\echo connection_backend_pid=:connection_backend_pid
SELECT version();
SHOW server_version;
SELECT current_database() AS database_name,
       session_user AS login_role,
       current_user AS effective_role,
       current_schema() AS current_schema,
       inet_server_addr() AS server_address,
       inet_server_port() AS server_port;

\echo === Databases, roles, schemas, and tables ===
\list
\du college_learner
\dn
SHOW search_path;
SELECT current_schemas(true) AS effective_search_path;
SHOW timezone;
SHOW transaction_isolation;
SELECT schemaname, tablename
FROM pg_catalog.pg_tables
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY schemaname, tablename;

-- These checks fail the script if we connected to the wrong environment.
SELECT current_database() = 'college_learning'
       AND current_user = 'college_learner'
       AND current_schema() = 'public'
       AND current_setting('server_version_num')::integer >= 180000
       AND current_setting('server_version_num')::integer < 190000
       AND NOT rolsuper AND NOT rolcreatedb AND NOT rolcreaterole
       AND NOT rolreplication AND NOT rolbypassrls AND rolcanlogin
       AS identity_ok
FROM pg_catalog.pg_roles WHERE rolname = current_user
\gset
\if :identity_ok
  \echo PASS: PostgreSQL 18, correct database, and non-superuser learning role.
\else
  \echo FAIL: Unexpected server, database, schema, or role.
  \quit 1
\endif

-- Refuse to touch a schema that someone created outside this exercise.
SELECT to_regnamespace('college_step02') IS NULL AS probe_namespace_free \gset
\if :probe_namespace_free
\else
  \echo FAIL: college_step02 already exists; inspect it before rerunning.
  \quit 1
\endif

\echo === A table that exists only inside this transaction ===
BEGIN;
CREATE SCHEMA college_step02;
CREATE TABLE college_step02.connection_probe (
    probe_id integer PRIMARY KEY,
    note text NOT NULL
);
INSERT INTO college_step02.connection_probe (probe_id, note)
VALUES (1, 'Step 2: inspect a table, then roll everything back');
SET LOCAL search_path TO college_step02, public;
SHOW search_path;
SELECT current_schema();
\dn college_step02
\dt college_step02.*
\d college_step02.connection_probe
SELECT * FROM connection_probe;
SELECT count(*) = 1 AS probe_visible FROM connection_probe \gset
\if :probe_visible
  \echo PASS: The current transaction can inspect its own table and row.
\else
  \echo FAIL: Transaction probe is missing.
  \quit 1
\endif
ROLLBACK;

\echo === After rollback ===
SHOW search_path;
SELECT current_schema();
SELECT to_regnamespace('college_step02') IS NULL
       AND current_schema() = 'public' AS rollback_ok \gset
\if :rollback_ok
  \echo PASS: Schema, table, row, and local search_path change were rolled back.
\else
  \echo FAIL: The exercise left unexpected state behind.
  \quit 1
\endif
