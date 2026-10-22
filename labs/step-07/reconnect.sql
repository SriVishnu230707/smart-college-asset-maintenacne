\set ON_ERROR_STOP on
\pset pager off
\echo === Step 7: verify cleanup from a new connection ===
\conninfo
SELECT current_database() AS database_name,
       current_user AS role_name,
       to_regnamespace('college_step07') IS NULL AS reference_probe_absent;
SELECT current_database() = 'college_learning'
       AND current_user = 'college_learner'
       AND to_regnamespace('college_step07') IS NULL AS reconnect_ok \gset
\if :reconnect_ok
  \echo PASS: A fresh connection confirms no Step 7 schema remains.
\else
  \echo FAIL: The Step 7 cleanup or connection identity is incorrect.
  \quit 1
\endif
