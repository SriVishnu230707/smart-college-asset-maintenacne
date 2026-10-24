\ir guard.sql
\echo === Step 18: independent observer verifies ORM commits, rollbacks, and Session disposal ===
\conninfo
BEGIN READ ONLY;
SELECT to_regclass('college_step18.lab_run') IS NOT NULL AS metadata_present \gset
\if :metadata_present
\else
  \echo FAIL: The committed Step 18 metadata is missing.
  \ir ../shared/fail.sql
\endif
SELECT count(*) = 1 AND bool_and(run_id = :'lab_run_id'::uuid
       AND created_asset_id IS NOT NULL AND writer_backend_pid <> pg_backend_pid()
       AND NOT EXISTS (SELECT 1 FROM pg_stat_activity WHERE pid = writer_backend_pid))
       AS independent_ok FROM college_step18.lab_run \gset
\if :independent_ok
  \echo PASS: Independent psql observes the exact completed run after the Python writer has disconnected.
\else
  \echo FAIL: Run metadata, generated ID, observer independence, or writer disposal differs.
  \ir ../shared/fail.sql
\endif
SELECT writer_backend_pid, pg_backend_pid() AS observer_backend_pid, created_asset_id, protected_asset_id
FROM college_step18.lab_run;

SELECT (SELECT count(*) FROM college_step18.departments) = 2
       AND EXISTS (SELECT 1 FROM college_step18.departments WHERE code = 'CSE' AND name = 'Computer Science' AND NOT is_archived)
       AND EXISTS (SELECT 1 FROM college_step18.departments WHERE code = 'ECE' AND name = 'Electronics' AND NOT is_archived)
       AND (SELECT count(*) FROM college_step18.asset_categories) = 1
       AND EXISTS (SELECT 1 FROM college_step18.asset_categories WHERE code = 'COMPUTER' AND name = 'Computer' AND NOT is_archived)
       AND (SELECT count(*) FROM college_step18.users) = 1
       AND EXISTS (SELECT 1 FROM college_step18.users AS u JOIN college_step18.departments AS d ON d.id = u.department_id
                   WHERE u.email = 'reporter@example.test' AND u.role = 'student' AND u.is_active AND d.code = 'ECE')
       AS parents_ok \gset
\if :parents_ok
  \echo PASS: The committed department/category/reporter fixture remains exact after every ORM operation.
\else
  \echo FAIL: Parent fixture values changed or unexpected parent rows exist.
  \ir ../shared/fail.sql
\endif

SELECT (SELECT count(*) FROM college_step18.assets) = 2
       AND EXISTS (SELECT 1 FROM college_step18.assets AS a
                   JOIN college_step18.departments AS d ON d.id = a.department_id
                   JOIN college_step18.asset_categories AS c ON c.id = a.category_id
                   CROSS JOIN college_step18.lab_run AS r
                   WHERE a.id = r.created_asset_id AND a.asset_code = 'PC-001' AND a.name = 'Lab Computer'
                     AND a.location = 'Computer Lab 2' AND a.status = 'active' AND d.code = 'CSE' AND c.code = 'COMPUTER')
       AND EXISTS (SELECT 1 FROM college_step18.assets AS a
                   JOIN college_step18.departments AS d ON d.id = a.department_id
                   JOIN college_step18.asset_categories AS c ON c.id = a.category_id
                   CROSS JOIN college_step18.lab_run AS r
                   WHERE a.id = r.protected_asset_id AND a.asset_code = 'KEEP-001' AND a.name = 'Referenced Computer'
                     AND a.location = 'Electronics Lab' AND a.status = 'active' AND d.code = 'ECE' AND c.code = 'COMPUTER')
       AS committed_assets_ok \gset
\if :committed_assets_ok
  \echo PASS: Independent SQL confirms the generated asset ID, committed update, and preserved referenced asset.
\else
  \echo FAIL: The final ORM asset identities, relationships, or values differ from the expected rows.
  \ir ../shared/fail.sql
\endif

SELECT NOT EXISTS (SELECT 1 FROM college_step18.assets WHERE asset_code IN ('LAB-TEMP', 'NO-COMMIT', 'APP-ROLLBACK'))
       AND (SELECT count(*) FROM college_step18.maintenance_tickets) = 1
       AND EXISTS (SELECT 1 FROM college_step18.maintenance_tickets AS t
                   JOIN college_step18.users AS u ON u.id = t.reported_by_id
                   JOIN college_step18.departments AS d ON d.id = t.department_id
                   CROSS JOIN college_step18.lab_run AS r
                   WHERE t.asset_id = r.protected_asset_id AND t.title = 'Computer issue'
                     AND t.priority = 'high' AND t.status = 'open' AND t.assigned_to_id IS NULL
                     AND t.created_at IS NOT NULL AND u.email = 'reporter@example.test' AND d.code = 'ECE')
       AS rollback_and_reference_ok \gset
\if :rollback_and_reference_ok
  \echo PASS: The deleted/uncommitted/aborted fixtures are absent and failed deletion preserved the original ticket reference.
\else
  \echo FAIL: A rollback-only asset remains or the protected ticket history changed.
  \ir ../shared/fail.sql
\endif
SELECT a.id, a.asset_code, a.name, a.location, a.status, d.code AS department
FROM college_step18.assets AS a JOIN college_step18.departments AS d ON d.id = a.department_id
ORDER BY a.asset_code;
COMMIT;
