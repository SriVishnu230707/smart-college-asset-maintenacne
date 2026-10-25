\ir orm-guard.sql
SELECT to_regnamespace(:'lab_schema') IS NULL AS absent \gset
\if :absent
  \echo PASS: A fresh connection confirms committed study-schema removal.
\else
  \echo FAIL: The study schema remains.
  \ir fail.sql
\endif
