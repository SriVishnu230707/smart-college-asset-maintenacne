\ir guard.sql
\echo === Step 8: independent connection verifies COMMIT and ROLLBACK ===
\conninfo
BEGIN READ ONLY;
SELECT to_regclass('college_step08.lab_run') IS NOT NULL AS metadata_present \gset
\if :metadata_present
\else
  \echo FAIL: The committed Step 8 metadata is missing.
  \ir fail.sql
\endif
SELECT count(*) = 1 AND bool_and(run_id = :'lab_run_id'::uuid AND writer_backend_pid <> pg_backend_pid())
       AS independent_observer_ok FROM college_step08.lab_run \gset
\if :independent_observer_ok
  \echo PASS: A different backend reads the committed metadata for this exact lab run.
\else
  \echo FAIL: The observer is not independent or the lab run does not match.
  \ir fail.sql
\endif
SELECT writer_backend_pid, pg_backend_pid() AS observer_backend_pid FROM college_step08.lab_run;
SELECT code, name, is_archived FROM college_step08.departments ORDER BY code;
SELECT asset_code, name, location, status FROM college_step08.assets ORDER BY asset_code;

SELECT (SELECT count(*) FROM college_step08.departments) = 2
       AND EXISTS (SELECT 1 FROM college_step08.departments WHERE code = 'CSE' AND name = 'Computer Science' AND NOT is_archived)
       AND EXISTS (SELECT 1 FROM college_step08.departments WHERE code = 'ECE' AND name = 'Electronics' AND NOT is_archived)
       AND (SELECT count(*) FROM college_step08.asset_categories) = 2
       AND EXISTS (SELECT 1 FROM college_step08.asset_categories WHERE code = 'PROJECTOR' AND name = 'Projector' AND NOT is_archived)
       AND EXISTS (SELECT 1 FROM college_step08.asset_categories WHERE code = 'COMPUTER' AND name = 'Computer' AND NOT is_archived)
       AS committed_baseline_ok \gset
\if :committed_baseline_ok
  \echo PASS: The independent connection confirms COMMIT preserved the department/category baseline.
\else
  \echo FAIL: The committed department/category baseline changed or disappeared.
  \ir fail.sql
\endif
SELECT count(*) = 3
       AND NOT EXISTS (SELECT 1 FROM college_step08.assets WHERE asset_code IN ('ROLLBACK-ONLY', 'LAB-TEMP'))
       AND NOT EXISTS (SELECT 1 FROM college_step08.departments WHERE code = 'MECH') AS observer_insert_rollback_ok
FROM college_step08.assets \gset
\if :observer_insert_rollback_ok
  \echo PASS: The independent connection finds none of the rolled-back inserts and exactly three baseline assets.
\else
  \echo FAIL: The observer found a rolled-back insert or wrong asset count.
  \ir fail.sql
\endif
SELECT location = 'Lecture Hall A' AND status = 'active' AND name = 'Classroom Projector'
       AND department_id = (SELECT id FROM college_step08.departments WHERE code = 'CSE')
       AND category_id = (SELECT id FROM college_step08.asset_categories WHERE code = 'PROJECTOR') AS observer_update_rollback_ok
FROM college_step08.assets WHERE asset_code = 'PRJ-001' \gset
\if :observer_update_rollback_ok
  \echo PASS: The independent connection sees the original projector after its UPDATE was rolled back.
\else
  \echo FAIL: The observer saw changed projector values.
  \ir fail.sql
\endif
SELECT location = 'Electronics Lab' AND status = 'active' AND name = 'Electronics Computer'
       AND department_id = (SELECT id FROM college_step08.departments WHERE code = 'ECE')
       AND category_id = (SELECT id FROM college_step08.asset_categories WHERE code = 'COMPUTER') AS observer_delete_rollback_ok
FROM college_step08.assets WHERE asset_code = 'PC-002' \gset
\if :observer_delete_rollback_ok
  \echo PASS: The independent connection sees the committed computer restored after DELETE was rolled back.
\else
  \echo FAIL: The observer could not find the original deleted-then-restored asset.
  \ir fail.sql
\endif
SELECT location = 'Computer Lab 1' AND status = 'active' AND name = 'Lab Computer'
       AND department_id = (SELECT id FROM college_step08.departments WHERE code = 'CSE')
       AND category_id = (SELECT id FROM college_step08.asset_categories WHERE code = 'COMPUTER') AS observer_error_rollback_ok
FROM college_step08.assets WHERE asset_code = 'PC-001' \gset
\if :observer_error_rollback_ok
  \echo PASS: The independent connection confirms the failed transaction committed none of its preceding update.
\else
  \echo FAIL: The failed transaction changed the committed computer.
  \ir fail.sql
\endif
COMMIT;
