\set ON_ERROR_STOP on
\pset pager off
\if :{?lab_run_id}
\else
  \echo FAIL: Supply lab_run_id through the Step 19 verifier or --set.
  \ir ../shared/fail.sql
\endif
SELECT current_database() = 'college_learning'
       AND current_user = 'college_learner'
       AND :'lab_run_id'::uuid IS NOT NULL AS identity_ok \gset
\if :identity_ok
\else
  \echo FAIL: Use the learning database, role, and a valid run ID.
  \ir ../shared/fail.sql
\endif
