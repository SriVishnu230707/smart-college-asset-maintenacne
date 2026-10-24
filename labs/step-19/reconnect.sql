\ir guard.sql
\echo === Step 19: independently observe committed lifecycle results ===
\conninfo
BEGIN READ ONLY;
SELECT count(*) = 1 AND bool_and(run_id = :'lab_run_id'::uuid AND survivor_id IS NOT NULL
       AND writer_backend_pid <> pg_backend_pid()
       AND NOT EXISTS (SELECT 1 FROM pg_stat_activity WHERE pid = writer_backend_pid)) AS independent_ok
FROM college_step19.lab_run \gset
\if :independent_ok
  \echo PASS: Independent psql observes the exact lifecycle run after the Python writer disconnects.
\else
  \echo FAIL: Run identity, surviving asset ID, or writer disposal differs.
  \ir ../shared/fail.sql
\endif
SELECT writer_backend_pid, pg_backend_pid() AS observer_backend_pid, survivor_id FROM college_step19.lab_run;
SELECT (SELECT count(*) FROM college_step19.assets) = 1
       AND EXISTS (SELECT 1 FROM college_step19.assets AS a
                   JOIN college_step19.departments AS d ON d.id = a.department_id
                   JOIN college_step19.asset_categories AS c ON c.id = a.category_id
                   CROSS JOIN college_step19.lab_run AS r
                   WHERE a.id = r.survivor_id AND a.asset_code = 'LIFE-KEEP' AND a.name = 'Lifecycle Computer'
                     AND a.location = 'Original Lab' AND a.status = 'active' AND d.code = 'CSE' AND c.code = 'COMPUTER')
       AS survivor_ok \gset
\if :survivor_ok
  \echo PASS: The exact committed survivor remains after detachment and deletion rollback.
\else
  \echo FAIL: The surviving asset or its original values differ.
  \ir ../shared/fail.sql
\endif
SELECT (SELECT count(*) FROM college_step19.departments) = 1
       AND (SELECT count(*) FROM college_step19.asset_categories) = 1
       AND NOT EXISTS (SELECT 1 FROM college_step19.users)
       AND NOT EXISTS (SELECT 1 FROM college_step19.maintenance_tickets)
       AND NOT EXISTS (SELECT 1 FROM college_step19.assets WHERE asset_code IN ('LIFE-TEMP', 'LIFE-CANCEL'))
       AS fixture_ok \gset
\if :fixture_ok
  \echo PASS: Disposable and canceled assets are absent and unrelated study tables remain unchanged.
\else
  \echo FAIL: A lifecycle probe or unexpected fixture row remains.
  \ir ../shared/fail.sql
\endif
SELECT id, asset_code, name, location, status FROM college_step19.assets ORDER BY asset_code;
COMMIT;
