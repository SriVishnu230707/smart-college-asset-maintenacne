\set ON_ERROR_STOP on
\pset pager off
\echo === Step 3: verify cleanup from a new connection ===
\conninfo
SELECT current_database() AS database_name,
       current_user AS role_name,
       to_regnamespace('college_step03') IS NULL AS model_probe_absent;
SELECT current_database() = 'college_learning'
       AND current_user = 'college_learner'
       AND to_regnamespace('college_step03') IS NULL AS reconnect_ok \gset
\if :reconnect_ok
  \echo PASS: A fresh connection confirms the Step 3 model probe left no schema behind.
\else
  \echo FAIL: The Step 3 cleanup or connection identity is incorrect.
  \quit 1
\endif
