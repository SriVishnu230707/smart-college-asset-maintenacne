\set ON_ERROR_STOP on
\pset pager off
\echo === Step 10: verify cleanup from a new connection ===
\conninfo
SELECT current_database() AS database_name, current_user AS role_name,
       to_regnamespace('college_step10') IS NULL AS join_probe_absent;
SELECT current_database() = 'college_learning' AND current_user = 'college_learner'
       AND to_regnamespace('college_step10') IS NULL AS reconnect_ok \gset
\if :reconnect_ok
  \echo PASS: A fresh connection confirms no Step 10 schema remains.
\else
  \echo FAIL: The Step 10 cleanup or connection identity is incorrect.
  \ir fail.sql
\endif
