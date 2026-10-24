\ir guard.sql
\echo === Step 20: verify committed cleanup from another connection ===
\conninfo
SELECT current_database() AS database_name, current_user AS role_name,
       to_regnamespace('college_step20') IS NULL AS session_lab_absent;
SELECT to_regnamespace('college_step20') IS NULL AS cleanup_persisted \gset
\if :cleanup_persisted
  \echo PASS: A fresh connection confirms the Step 20 schema cleanup was committed.
\else
  \echo FAIL: The Step 20 schema still exists after cleanup.
  \ir ../shared/fail.sql
\endif
