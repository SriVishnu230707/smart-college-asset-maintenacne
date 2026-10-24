\ir guard.sql
\echo === Step 20: independently inspect committed tickets and disposed backends ===
\conninfo
BEGIN READ ONLY;
SELECT count(*) = 1 AND bool_and(run_id = :'lab_run_id'::uuid
       AND committed_ticket_id IS NOT NULL AND noauto_ticket_id IS NOT NULL AND recovered_ticket_id IS NOT NULL
       AND observer_backend_pid <> writer_backend_pid AND pg_backend_pid() NOT IN (writer_backend_pid, observer_backend_pid)
       AND NOT EXISTS (SELECT 1 FROM pg_stat_activity WHERE pid IN (writer_backend_pid, observer_backend_pid)))
       AS independent_ok FROM college_step20.lab_run \gset
\if :independent_ok
  \echo PASS: Independent psql verifies the exact completed run and both disposed Python backends.
\else
  \echo FAIL: Run metadata, ticket IDs, or backend independence/disposal differs.
  \ir ../shared/fail.sql
\endif
SELECT writer_backend_pid, observer_backend_pid, pg_backend_pid() AS final_observer_pid,
       committed_ticket_id, noauto_ticket_id, recovered_ticket_id FROM college_step20.lab_run;
SELECT (SELECT count(*) FROM college_step20.maintenance_tickets) = 3
       AND EXISTS (SELECT 1 FROM college_step20.maintenance_tickets AS t CROSS JOIN college_step20.lab_run AS r
                   WHERE t.id = r.committed_ticket_id AND t.title = 'COMMIT-TICKET' AND t.priority = 'high')
       AND EXISTS (SELECT 1 FROM college_step20.maintenance_tickets AS t CROSS JOIN college_step20.lab_run AS r
                   WHERE t.id = r.noauto_ticket_id AND t.title = 'COMMIT-NOAUTO' AND t.priority = 'high')
       AND EXISTS (SELECT 1 FROM college_step20.maintenance_tickets AS t CROSS JOIN college_step20.lab_run AS r
                   WHERE t.id = r.recovered_ticket_id AND t.title = 'RECOVERED' AND t.priority = 'medium')
       AND NOT EXISTS (SELECT 1 FROM college_step20.maintenance_tickets
                       WHERE title IN ('ROLLBACK-TICKET','AUTO-TICKET','CONTROLLED-TICKET','BEFORE-ERROR','INVALID-PRIORITY'))
       AS tickets_ok \gset
\if :tickets_ok
  \echo PASS: Only the three exact committed tickets remain; every rolled-back or rejected ticket is absent.
\else
  \echo FAIL: Committed ticket IDs/priorities differ or aborted work remains.
  \ir ../shared/fail.sql
\endif
SELECT (SELECT count(*) FROM college_step20.departments) = 1
       AND (SELECT count(*) FROM college_step20.asset_categories) = 1
       AND (SELECT count(*) FROM college_step20.users) = 1
       AND (SELECT count(*) FROM college_step20.assets) = 1
       AND (SELECT count(*) FROM college_step20.maintenance_tickets AS t
            JOIN college_step20.assets AS a ON a.id = t.asset_id
            JOIN college_step20.users AS u ON u.id = t.reported_by_id
            JOIN college_step20.departments AS d ON d.id = t.department_id
            JOIN college_step20.asset_categories AS c ON c.id = a.category_id
            WHERE t.status = 'open' AND t.description = 'Original description' AND t.created_at IS NOT NULL
              AND t.assigned_to_id IS NULL AND t.assigned_at IS NULL AND t.closed_at IS NULL
              AND t.rejected_at IS NULL AND t.rejection_reason IS NULL
              AND a.asset_code = 'FLUSH-PC' AND a.name = 'Flush Computer' AND a.location = 'Original Lab' AND a.status = 'active'
              AND u.email = 'reporter@example.test' AND u.role = 'student' AND u.is_active
              AND d.code = 'CSE' AND u.department_id = d.id AND a.department_id = d.id AND c.code = 'COMPUTER') = 3
       AS fixture_ok \gset
\if :fixture_ok
  \echo PASS: All ticket defaults, original descriptions, references, and parent fixture rows remain exact after recovery.
\else
  \echo FAIL: A ticket default, original value, or fixture reference changed.
  \ir ../shared/fail.sql
\endif
SELECT id, title, priority, status, description FROM college_step20.maintenance_tickets ORDER BY title;
COMMIT;
