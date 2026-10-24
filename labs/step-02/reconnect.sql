\set ON_ERROR_STOP on
\pset pager off
\echo === A new psql connection ===
\conninfo
SELECT pg_backend_pid() AS connection_backend_pid \gset
\echo connection_backend_pid=:connection_backend_pid
SELECT current_database() AS database_name,
       current_user AS role_name,
       current_schema() AS schema_name,
       current_setting('server_version') AS server_version,
       to_regnamespace('college_step02') IS NULL AS probe_schema_absent;
SHOW search_path;
SELECT current_database() = 'college_learning'
       AND current_user = 'college_learner'
       AND current_schema() = 'public'
       AND to_regnamespace('college_step02') IS NULL AS reconnect_ok \gset
\if :reconnect_ok
  \echo PASS: Reconnected without a GUI; identity is correct and rolled-back objects are absent.
\else
  \echo FAIL: Reconnection observations differ from the expected lab environment.
  \ir ../shared/fail.sql
\endif
