\ir guard.sql
\echo === Step 14: verify committed cleanup from another connection ===
\conninfo
SELECT current_database() AS database_name, current_user AS role_name,
       to_regnamespace('college_step14') IS NULL AS core_probe_absent;
SELECT to_regnamespace('college_step14') IS NULL AS cleanup_persisted \gset
\if :cleanup_persisted
  \echo PASS: A fresh connection confirms the Step 14 schema cleanup was committed.
\else
  \echo FAIL: The Step 14 schema still exists after cleanup.
  \ir ../shared/fail.sql
\endif
