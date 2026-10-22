\ir guard.sql
\echo === Step 8: remove only the current lab run tables ===
SELECT to_regnamespace('college_step08') IS NULL AS already_absent \gset
\if :already_absent
  \echo INFO: No Step 8 schema remains to clean up.
\else
  BEGIN;
  SELECT to_regclass('college_step08.lab_run') IS NOT NULL
         AND nspowner = (SELECT oid FROM pg_roles WHERE rolname = current_user) AS owned_metadata_present
  FROM pg_namespace WHERE nspname = 'college_step08' \gset
  \if :owned_metadata_present
  \else
    \echo FAIL: Refusing cleanup without matching schema ownership and metadata.
    \ir fail.sql
  \endif
  SELECT count(*) = 1 AND bool_and(run_id = :'lab_run_id'::uuid) AS run_matches
  FROM college_step08.lab_run \gset
  \if :run_matches
  \else
    \echo REFUSED: STEP08_RUN_ID_MISMATCH; no object was removed.
    \set VERBOSITY sqlstate
    DO $$ BEGIN RAISE EXCEPTION USING ERRCODE = '22023', MESSAGE = 'STEP08_RUN_ID_MISMATCH'; END $$;
  \endif
  -- Known objects only, child first. No CASCADE; unexpected dependencies make
  -- the cleanup transaction fail rather than deleting unrelated objects.
  DROP TABLE college_step08.assets;
  DROP TABLE college_step08.asset_categories;
  DROP TABLE college_step08.departments;
  DROP TABLE college_step08.lab_run;
  DROP SCHEMA college_step08;
  COMMIT;
  SELECT to_regnamespace('college_step08') IS NULL AS cleanup_ok \gset
  \if :cleanup_ok
    \echo PASS: Guarded cleanup committed removal of the current run schema and known objects.
  \else
    \echo FAIL: Step 8 cleanup left the schema behind.
    \ir fail.sql
  \endif
\endif
