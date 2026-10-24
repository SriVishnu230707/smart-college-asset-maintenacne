\ir guard.sql
\echo === Step 14: independent observer verifies the committed Core transactions ===
\conninfo
BEGIN READ ONLY;
SELECT to_regclass('college_step14.lab_run') IS NOT NULL AS metadata_present \gset
\if :metadata_present
\else
  \echo FAIL: The committed Step 14 metadata is missing.
  \ir ../shared/fail.sql
\endif
SELECT count(*) = 1
       AND bool_and(run_id = :'lab_run_id'::uuid AND writer_backend_pid <> pg_backend_pid()
           AND NOT EXISTS (SELECT 1 FROM pg_stat_activity WHERE pid = writer_backend_pid))
       AS independent_observer_ok FROM college_step14.lab_run \gset
\if :independent_observer_ok
  \echo PASS: An independent backend reads this exact run after the Python writer has disconnected.
\else
  \echo FAIL: The run marker, independent observer, or writer disposal check failed.
  \ir ../shared/fail.sql
\endif
SELECT writer_backend_pid, pg_backend_pid() AS observer_backend_pid FROM college_step14.lab_run;

WITH expected(id, code, name) AS (VALUES
  ('10000000-0000-4000-8000-000000000001'::uuid, 'CSE', 'Computer Science'),
  ('10000000-0000-4000-8000-000000000002'::uuid, 'ECE', 'Department ECE'))
SELECT (SELECT count(*) FROM college_step14.departments) = 2
       AND NOT EXISTS (SELECT * FROM expected EXCEPT SELECT id, code, name FROM college_step14.departments)
       AND (SELECT count(*) FROM college_step14.asset_categories) = 1
       AND EXISTS (SELECT 1 FROM college_step14.asset_categories
                   WHERE id = '20000000-0000-4000-8000-000000000001' AND code = 'COMPUTER')
       AS committed_parents_ok \gset
\if :committed_parents_ok
  \echo PASS: The observer finds the original parent rows and the successfully committed ECE department.
\else
  \echo FAIL: The committed department or category rows differ from the expected fixture.
  \ir ../shared/fail.sql
\endif

WITH expected(id, asset_code, name, department_id, category_id) AS (VALUES
  ('40000000-0000-4000-8000-000000000001'::uuid, 'PC-001', 'Zebra Computer',
   '10000000-0000-4000-8000-000000000001'::uuid, '20000000-0000-4000-8000-000000000001'::uuid),
  ('40000000-0000-4000-8000-000000000002'::uuid, 'PC-002', 'Alpha Computer',
   '10000000-0000-4000-8000-000000000001'::uuid, '20000000-0000-4000-8000-000000000001'::uuid),
  ('40000000-0000-4000-8000-000000000003'::uuid, 'PC-003',
   $payload$O'Brien'); DROP TABLE college_step14.assets; --$payload$,
   '10000000-0000-4000-8000-000000000002'::uuid, '20000000-0000-4000-8000-000000000001'::uuid))
SELECT (SELECT count(*) FROM college_step14.assets) = 3
       AND NOT EXISTS (SELECT * FROM expected EXCEPT
           SELECT id, asset_code, name, department_id, category_id FROM college_step14.assets)
       AS committed_assets_ok \gset
\if :committed_assets_ok
  \echo PASS: Exactly three committed assets retain their IDs, relationships, and literal quoted name.
\else
  \echo FAIL: Committed assets or their bound text differ from the expected rows.
  \ir ../shared/fail.sql
\endif

SELECT NOT EXISTS (SELECT 1 FROM college_step14.departments WHERE id IN (
           '10000000-0000-4000-8000-000000000003', '10000000-0000-4000-8000-000000000004',
           '10000000-0000-4000-8000-000000000005'))
       AND NOT EXISTS (SELECT 1 FROM college_step14.assets WHERE id IN (
           '40000000-0000-4000-8000-000000000004', '40000000-0000-4000-8000-000000000005',
           '40000000-0000-4000-8000-000000000006')) AS rolled_back_pairs_absent \gset
\if :rolled_back_pairs_absent
  \echo PASS: The observer finds no rows from connection-close, application-error, or database-error rollbacks.
\else
  \echo FAIL: A rolled-back department or asset escaped its transaction.
  \ir ../shared/fail.sql
\endif
SELECT a.asset_code, a.name, d.code AS department
FROM college_step14.assets AS a JOIN college_step14.departments AS d ON d.id = a.department_id
ORDER BY a.asset_code COLLATE "C";
COMMIT;
