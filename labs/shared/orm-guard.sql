\set ON_ERROR_STOP on
\pset pager off
SELECT current_database()='college_learning' AND current_user='college_learner'
       AND :'lab_schema' ~ '^college_step(2[1-9]|[34][0-9]|50)$' AND :'lab_run_id'::uuid IS NOT NULL AS guard_ok \gset
\if :guard_ok
\else
  \echo FAIL: Invalid learner, study namespace, or run marker.
  \ir fail.sql
\endif
