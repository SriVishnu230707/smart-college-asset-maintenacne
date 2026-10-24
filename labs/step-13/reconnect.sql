\set ON_ERROR_STOP on
\pset pager off
\echo === Step 13: independently inspect the Python connection cleanup ===
\conninfo
\if :{?engine_backend_pid}
\else
  \echo FAIL: Supply the backend PID recorded by the Python probe.
  \ir ../shared/fail.sql
\endif
SELECT current_database() = 'college_learning' AND current_user = 'college_learner'
       AND current_setting('server_version_num')::integer BETWEEN 180000 AND 189999
       AND pg_backend_pid() <> :'engine_backend_pid'::integer AS identity_ok \gset
\if :identity_ok
  \echo PASS: Independent psql connects as the learner to PostgreSQL 18 using a different backend.
\else
  \echo FAIL: The observer identity or independent connection is incorrect.
  \ir ../shared/fail.sql
\endif
SELECT :'engine_backend_pid'::integer AS disposed_engine_backend,
       NOT EXISTS (SELECT 1 FROM pg_stat_activity WHERE pid = :'engine_backend_pid'::integer) AS backend_absent,
       to_regnamespace('college_step13') IS NULL AS schema_absent;
SELECT NOT EXISTS (SELECT 1 FROM pg_stat_activity WHERE pid = :'engine_backend_pid'::integer)
       AND to_regnamespace('college_step13') IS NULL AS cleanup_ok \gset
\if :cleanup_ok
  \echo PASS: The disposed Engine backend is gone and no Step 13 schema exists.
\else
  \echo FAIL: The Python Engine connection or an unexpected study schema remains.
  \ir ../shared/fail.sql
\endif
