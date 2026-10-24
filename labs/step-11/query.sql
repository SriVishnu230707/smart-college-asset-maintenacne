\set ON_ERROR_STOP on
\pset pager off
\pset null '(NULL)'
\echo === Step 11: grouped ticket counts and exact completed-labor aggregates ===
\conninfo
SELECT current_database() = 'college_learning' AND current_user = 'college_learner' AS identity_ok \gset
\if :identity_ok
\else
  \echo FAIL: Use the learning database and role.
  \ir fail.sql
\endif
SELECT to_regnamespace('college_step11') IS NULL AS namespace_free \gset
\if :namespace_free
\else
  \echo FAIL: college_step11 already exists; inspect it before rerunning.
  \ir fail.sql
\endif

BEGIN;
CREATE SCHEMA college_step11;
SET LOCAL search_path TO college_step11, public;
-- Reduced report projections. Asset/reporter/proof/ledger facts and full
-- write authorization are omitted; these are not production migrations.
CREATE TABLE departments (id uuid PRIMARY KEY, code text NOT NULL UNIQUE);
CREATE TABLE users (
    id uuid PRIMARY KEY,
    department_id uuid NOT NULL REFERENCES departments(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    display_name text NOT NULL
);
CREATE TABLE maintenance_tickets (
    id uuid PRIMARY KEY,
    department_id uuid NOT NULL REFERENCES departments(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    assigned_to_id uuid REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    priority text NOT NULL CHECK (priority IN ('low', 'medium', 'high', 'critical')),
    status text NOT NULL CHECK (status IN ('open', 'assigned', 'in_progress', 'awaiting_verification', 'closed', 'rejected'))
);
CREATE TABLE work_orders (
    id uuid PRIMARY KEY,
    ticket_id uuid NOT NULL REFERENCES maintenance_tickets(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    status text NOT NULL CHECK (status IN ('draft', 'in_progress', 'completed')),
    labor_cost numeric(12,2) NOT NULL CHECK (labor_cost >= 0 AND labor_cost <> 'NaN'::numeric)
);
INSERT INTO departments VALUES
    ('10000000-0000-4000-8000-000000000001', 'CSE'),
    ('10000000-0000-4000-8000-000000000002', 'ECE'),
    ('10000000-0000-4000-8000-000000000003', 'MECH');
-- Both rows represent active technicians. Role eligibility is a later workflow.
INSERT INTO users VALUES
    ('30000000-0000-4000-8000-000000000001', '10000000-0000-4000-8000-000000000001', 'Ravi'),
    ('30000000-0000-4000-8000-000000000002', '10000000-0000-4000-8000-000000000002', 'Nila');
-- T1-T6 abbreviate the UUID endings. T4 is undergoing rework after W1;
-- W5 is its new draft. Old completed work remains in the report.
INSERT INTO maintenance_tickets VALUES
    ('50000000-0000-4000-8000-000000000001', '10000000-0000-4000-8000-000000000001', NULL, 'high', 'open'),
    ('50000000-0000-4000-8000-000000000002', '10000000-0000-4000-8000-000000000001', '30000000-0000-4000-8000-000000000001', 'high', 'in_progress'),
    ('50000000-0000-4000-8000-000000000003', '10000000-0000-4000-8000-000000000002', NULL, 'medium', 'open'),
    ('50000000-0000-4000-8000-000000000004', '10000000-0000-4000-8000-000000000001', '30000000-0000-4000-8000-000000000001', 'critical', 'in_progress'),
    ('50000000-0000-4000-8000-000000000005', '10000000-0000-4000-8000-000000000001', '30000000-0000-4000-8000-000000000001', 'low', 'closed'),
    ('50000000-0000-4000-8000-000000000006', '10000000-0000-4000-8000-000000000002', '30000000-0000-4000-8000-000000000002', 'high', 'awaiting_verification');
-- Costs are already validated two-place INR literals. Completed amounts are
-- frozen labor components; parts are outside this report, not assumed free.
INSERT INTO work_orders VALUES
    ('60000000-0000-4000-8000-000000000001', '50000000-0000-4000-8000-000000000004', 'completed', 600.50),
    ('60000000-0000-4000-8000-000000000002', '50000000-0000-4000-8000-000000000005', 'completed', 0.00),
    ('60000000-0000-4000-8000-000000000003', '50000000-0000-4000-8000-000000000006', 'completed', 75.50),
    ('60000000-0000-4000-8000-000000000004', '50000000-0000-4000-8000-000000000002', 'in_progress', 1000.00),
    ('60000000-0000-4000-8000-000000000005', '50000000-0000-4000-8000-000000000004', 'draft', 2000.00);

-- Helpers execute only literal lab SELECTs. JSON is a comparison format,
-- not an application storage decision. Ordered subqueries have no outer join.
CREATE FUNCTION assert_rows(label text, statement text, expected jsonb)
RETURNS text LANGUAGE plpgsql AS $$
DECLARE actual jsonb;
BEGIN
    EXECUTE 'SELECT coalesce(jsonb_agg(to_jsonb(r)), ''[]''::jsonb) FROM (' || statement || ') AS r' INTO actual;
    IF actual IS DISTINCT FROM expected THEN RAISE EXCEPTION '%: expected %, observed %', label, expected, actual; END IF;
    RETURN 'PASS: ' || label || ' Observed=' || actual::text;
END $$;
CREATE FUNCTION assert_true(label text, observed boolean)
RETURNS text LANGUAGE plpgsql AS $$
BEGIN
    IF observed IS DISTINCT FROM true THEN RAISE EXCEPTION 'Assertion failed: %', label; END IF;
    RETURN 'PASS: ' || label;
END $$;
CREATE FUNCTION expect_error(label text, statement text, expected_state text)
RETURNS text LANGUAGE plpgsql AS $$
DECLARE actual_state text;
BEGIN
    BEGIN
        EXECUTE statement;
    EXCEPTION WHEN OTHERS THEN
        GET STACKED DIAGNOSTICS actual_state = RETURNED_SQLSTATE;
        IF actual_state IS DISTINCT FROM expected_state THEN RAISE; END IF;
        RETURN 'PASS: ' || label || ' SQLSTATE=' || actual_state;
    END;
    RAISE EXCEPTION 'Invalid query was accepted: %', label;
END $$;

\echo === COUNT star counts joined rows; COUNT child-ID counts real tickets ===
SELECT d.code, count(*) AS joined_rows, count(t.id) AS tickets,
       count(t.assigned_to_id) AS assignments
FROM departments AS d LEFT JOIN maintenance_tickets AS t ON t.department_id = d.id
GROUP BY d.id, d.code ORDER BY d.code COLLATE "C";
\pset format unaligned
\pset tuples_only on
SELECT assert_rows('Department totals distinguish joined rows, real tickets, and non-NULL assignments.',
    $$SELECT d.code, count(*) AS joined_rows, count(t.id) AS tickets, count(t.assigned_to_id) AS assignments
      FROM departments AS d LEFT JOIN maintenance_tickets AS t ON t.department_id = d.id
      GROUP BY d.id, d.code ORDER BY d.code COLLATE "C"$$,
    '[{"code":"CSE","joined_rows":4,"tickets":4,"assignments":3},{"code":"ECE","joined_rows":2,"tickets":2,"assignments":1},{"code":"MECH","joined_rows":1,"tickets":0,"assignments":0}]');
SELECT assert_rows('Grouping only observed priorities retains MECH as one NULL-priority group, not four zero buckets.',
    $$SELECT d.code, t.priority, count(t.id) AS tickets
      FROM departments AS d LEFT JOIN maintenance_tickets AS t ON t.department_id = d.id
      GROUP BY d.id, d.code, t.priority ORDER BY d.code COLLATE "C", t.priority COLLATE "C" NULLS LAST$$,
    '[{"code":"CSE","priority":"critical","tickets":1},{"code":"CSE","priority":"high","tickets":2},{"code":"CSE","priority":"low","tickets":1},{"code":"ECE","priority":"high","tickets":1},{"code":"ECE","priority":"medium","tickets":1},{"code":"MECH","priority":null,"tickets":0}]');

\echo === Explicit reporting axes produce all twelve department-priority buckets ===
\pset format aligned
\pset tuples_only off
SELECT d.code, p.priority, count(t.id) AS tickets
FROM departments AS d
CROSS JOIN (VALUES ('low', 1), ('medium', 2), ('high', 3), ('critical', 4)) AS p(priority, sort_rank)
LEFT JOIN maintenance_tickets AS t ON t.department_id = d.id AND t.priority = p.priority
GROUP BY d.id, d.code, p.priority, p.sort_rank
ORDER BY d.code COLLATE "C", p.sort_rank;
\pset format unaligned
\pset tuples_only on
SELECT assert_rows('All twelve priority buckets match the hand-counted matrix, including every empty MECH bucket.',
    $$SELECT d.code, p.priority, count(t.id) AS tickets FROM departments AS d
      CROSS JOIN (VALUES ('low', 1), ('medium', 2), ('high', 3), ('critical', 4)) AS p(priority, sort_rank)
      LEFT JOIN maintenance_tickets AS t ON t.department_id = d.id AND t.priority = p.priority
      GROUP BY d.id, d.code, p.priority, p.sort_rank ORDER BY d.code COLLATE "C", p.sort_rank$$,
    '[{"code":"CSE","priority":"low","tickets":1},{"code":"CSE","priority":"medium","tickets":0},{"code":"CSE","priority":"high","tickets":2},{"code":"CSE","priority":"critical","tickets":1},{"code":"ECE","priority":"low","tickets":0},{"code":"ECE","priority":"medium","tickets":1},{"code":"ECE","priority":"high","tickets":1},{"code":"ECE","priority":"critical","tickets":0},{"code":"MECH","priority":"low","tickets":0},{"code":"MECH","priority":"medium","tickets":0},{"code":"MECH","priority":"high","tickets":0},{"code":"MECH","priority":"critical","tickets":0}]');

\echo === FILTER and CASE select inputs for one metric without dropping other rows ===
SELECT assert_rows('FILTER and CASE agree on open counts while total, unassigned, and distinct-assignee metrics retain their meanings.',
    $$SELECT d.code, count(t.id) AS total,
             count(t.id) FILTER (WHERE t.status = 'open') AS open_filter,
             sum(CASE WHEN t.status = 'open' THEN 1 ELSE 0 END) AS open_sum_case,
             count(CASE WHEN t.status = 'open' THEN 1 END) AS open_count_case,
             count(t.id) FILTER (WHERE t.assigned_to_id IS NULL) AS unassigned,
             count(DISTINCT t.assigned_to_id) AS distinct_assignees
      FROM departments AS d LEFT JOIN maintenance_tickets AS t ON t.department_id = d.id
      GROUP BY d.id, d.code ORDER BY d.code COLLATE "C"$$,
    '[{"code":"CSE","total":4,"open_filter":1,"open_sum_case":1,"open_count_case":1,"unassigned":1,"distinct_assignees":1},{"code":"ECE","total":2,"open_filter":1,"open_sum_case":1,"open_count_case":1,"unassigned":1,"distinct_assignees":1},{"code":"MECH","total":0,"open_filter":0,"open_sum_case":0,"open_count_case":0,"unassigned":0,"distinct_assignees":0}]');
SELECT assert_rows('Wrong COUNT expressions count false, zero, or an unmatched placeholder instead of the intended condition.',
    $$SELECT d.code, count(t.status = 'open') AS nonnull_booleans,
             count(CASE WHEN t.status = 'open' THEN 1 ELSE 0 END) AS nonnull_cases,
             count(*) FILTER (WHERE t.assigned_to_id IS NULL) AS null_assignee_rows
      FROM departments AS d LEFT JOIN maintenance_tickets AS t ON t.department_id = d.id
      GROUP BY d.id, d.code ORDER BY d.code COLLATE "C"$$,
    '[{"code":"CSE","nonnull_booleans":4,"nonnull_cases":4,"null_assignee_rows":1},{"code":"ECE","nonnull_booleans":2,"nonnull_cases":2,"null_assignee_rows":1},{"code":"MECH","nonnull_booleans":0,"nonnull_cases":1,"null_assignee_rows":1}]');
SELECT assert_rows('A child-status WHERE predicate drops the empty department before grouping.',
    $$SELECT d.code, count(t.id) AS tickets FROM departments AS d
      LEFT JOIN maintenance_tickets AS t ON t.department_id = d.id WHERE t.status = 'open'
      GROUP BY d.id, d.code ORDER BY d.code COLLATE "C"$$,
    '[{"code":"CSE","tickets":1},{"code":"ECE","tickets":1}]');
SELECT assert_rows('The same status predicate in ON preserves all departments with zero counts where needed.',
    $$SELECT d.code, count(t.id) AS tickets FROM departments AS d
      LEFT JOIN maintenance_tickets AS t ON t.department_id = d.id AND t.status = 'open'
      GROUP BY d.id, d.code ORDER BY d.code COLLATE "C"$$,
    '[{"code":"CSE","tickets":1},{"code":"ECE","tickets":1},{"code":"MECH","tickets":0}]');

\echo === WHERE selects rows; HAVING selects groups ===
SELECT assert_rows('HAVING at least three tickets retains only CSE with all four input tickets.',
    $$SELECT d.code, count(t.id) AS tickets FROM departments AS d
      LEFT JOIN maintenance_tickets AS t ON t.department_id = d.id
      GROUP BY d.id, d.code HAVING count(t.id) >= 3 ORDER BY d.code COLLATE "C"$$,
    '[{"code":"CSE","tickets":4}]');
SELECT assert_rows('HAVING a filtered urgent count retains the complete qualifying group and its total.',
    $$SELECT d.code, count(t.id) AS total, count(t.id) FILTER (WHERE t.priority IN ('high','critical')) AS urgent
      FROM departments AS d LEFT JOIN maintenance_tickets AS t ON t.department_id = d.id
      GROUP BY d.id, d.code HAVING count(t.id) FILTER (WHERE t.priority IN ('high','critical')) >= 2
      ORDER BY d.code COLLATE "C"$$,
    '[{"code":"CSE","total":4,"urgent":3}]');
SELECT assert_rows('Moving the urgent predicate to WHERE changes the inputs and the reported total to three.',
    $$SELECT d.code, count(t.id) AS total FROM departments AS d
      LEFT JOIN maintenance_tickets AS t ON t.department_id = d.id WHERE t.priority IN ('high','critical')
      GROUP BY d.id, d.code HAVING count(t.id) >= 2 ORDER BY d.code COLLATE "C"$$,
    '[{"code":"CSE","total":3}]');
SELECT assert_rows('HAVING a zero child count selects the genuinely empty department.',
    $$SELECT d.code, count(t.id) AS tickets FROM departments AS d
      LEFT JOIN maintenance_tickets AS t ON t.department_id = d.id
      GROUP BY d.id, d.code HAVING count(t.id) = 0 ORDER BY d.code COLLATE "C"$$,
    '[{"code":"MECH","tickets":0}]');

\echo === Completed labor uses frozen NUMERIC inputs and recorded ticket department ===
\pset format aligned
\pset tuples_only off
SELECT d.code, count(w.id) FILTER (WHERE w.status = 'completed') AS completed_orders,
       sum(w.labor_cost) FILTER (WHERE w.status = 'completed') AS raw_labor_sum,
       coalesce(sum(w.labor_cost) FILTER (WHERE w.status = 'completed'), 0.00::numeric) AS labor_total,
       avg(w.labor_cost) FILTER (WHERE w.status = 'completed') AS mean_completed_labor
FROM departments AS d LEFT JOIN maintenance_tickets AS t ON t.department_id = d.id
LEFT JOIN work_orders AS w ON w.ticket_id = t.id
GROUP BY d.id, d.code ORDER BY d.code COLLATE "C";
\pset format unaligned
\pset tuples_only on
SELECT assert_rows('Completed labor excludes both unfinished estimates, includes real zero cost, and preserves an absent mean as NULL.',
    $$SELECT d.code, count(w.id) FILTER (WHERE w.status = 'completed') AS completed_orders,
             sum(w.labor_cost) FILTER (WHERE w.status = 'completed') AS raw_labor_sum,
             coalesce(sum(w.labor_cost) FILTER (WHERE w.status = 'completed'), 0.00::numeric) AS labor_total,
             avg(w.labor_cost) FILTER (WHERE w.status = 'completed') AS mean_completed_labor
      FROM departments AS d LEFT JOIN maintenance_tickets AS t ON t.department_id = d.id
      LEFT JOIN work_orders AS w ON w.ticket_id = t.id GROUP BY d.id, d.code ORDER BY d.code COLLATE "C"$$,
    '[{"code":"CSE","completed_orders":2,"raw_labor_sum":600.50,"labor_total":600.50,"mean_completed_labor":300.25},{"code":"ECE","completed_orders":1,"raw_labor_sum":75.50,"labor_total":75.50,"mean_completed_labor":75.50},{"code":"MECH","completed_orders":0,"raw_labor_sum":null,"labor_total":0.00,"mean_completed_labor":null}]');
SELECT assert_rows('CASE without ELSE matches filtered SUM and AVG; ELSE zero biases the average denominator.',
    $$SELECT d.code, sum(CASE WHEN w.status = 'completed' THEN w.labor_cost END) AS case_sum,
             avg(CASE WHEN w.status = 'completed' THEN w.labor_cost END) AS case_mean,
             avg(CASE WHEN w.status = 'completed' THEN w.labor_cost ELSE 0.00 END) AS zero_filled_mean
      FROM departments AS d LEFT JOIN maintenance_tickets AS t ON t.department_id = d.id
      LEFT JOIN work_orders AS w ON w.ticket_id = t.id GROUP BY d.id, d.code ORDER BY d.code COLLATE "C"$$,
    '[{"code":"CSE","case_sum":600.50,"case_mean":300.25,"zero_filled_mean":120.10},{"code":"ECE","case_sum":75.50,"case_mean":75.50,"zero_filled_mean":37.75},{"code":"MECH","case_sum":null,"case_mean":null,"zero_filled_mean":0.00}]');
SELECT assert_rows('The isolated nullable-value probe distinguishes a missing observation from a real zero.',
    $$SELECT count(*) AS rows, count(v) AS known_values, sum(v) AS total, avg(v) AS known_mean,
             avg(coalesce(v, 0.00)) AS zero_filled_mean
      FROM (VALUES (6.00::numeric), (NULL::numeric), (0.00::numeric)) AS probe(v)$$,
    '[{"rows":3,"known_values":2,"total":6.00,"known_mean":3.00,"zero_filled_mean":2.00}]');
SELECT assert_rows('An ungrouped empty input returns one aggregate row with zero COUNT and NULL SUM and AVG.',
    $$SELECT count(*) AS rows, sum(labor_cost) AS total, avg(labor_cost) AS mean
      FROM work_orders WHERE false$$,
    '[{"rows":0,"total":null,"mean":null}]');
SELECT assert_rows('A grouped empty input has no groups, so COALESCE cannot manufacture a missing group row.',
    $$SELECT status, coalesce(sum(labor_cost), 0.00) AS total FROM work_orders
      WHERE false GROUP BY status ORDER BY status COLLATE "C"$$, '[]');
SELECT assert_rows('Joining work orders changes row grain: T4 repeats, while DISTINCT ticket IDs still count tickets.',
    $$SELECT d.code, count(t.id) AS repeated_ticket_ids, count(DISTINCT t.id) AS tickets
      FROM departments AS d LEFT JOIN maintenance_tickets AS t ON t.department_id = d.id
      LEFT JOIN work_orders AS w ON w.ticket_id = t.id GROUP BY d.id, d.code ORDER BY d.code COLLATE "C"$$,
    '[{"code":"CSE","repeated_ticket_ids":5,"tickets":4},{"code":"ECE","repeated_ticket_ids":2,"tickets":2},{"code":"MECH","repeated_ticket_ids":0,"tickets":0}]');
SELECT assert_rows('COUNT returns bigint and SUM and AVG of numeric inputs remain numeric.',
    $$SELECT pg_typeof(count(*))::text AS count_type, pg_typeof(sum(labor_cost))::text AS sum_type,
             pg_typeof(avg(labor_cost))::text AS mean_type FROM work_orders$$,
    '[{"count_type":"bigint","sum_type":"numeric","mean_type":"numeric"}]');
SELECT assert_rows('A report SUM can exceed the per-record NUMERIC(12,2) range without losing exact cents.',
    $$SELECT sum(v) AS report_total FROM (VALUES (9999999999.99::numeric(12,2)), (9999999999.99::numeric(12,2))) AS probe(v)$$,
    '[{"report_total":19999999999.98}]');

\echo === Invalid aggregate queries fail with exact SQLSTATE ===
SELECT expect_error('An aggregate cannot select its own input rows in WHERE.',
    $$SELECT department_id, count(*) FROM maintenance_tickets WHERE count(*) > 1 GROUP BY department_id$$, '42803');
SELECT expect_error('A varying non-grouped ticket priority cannot be projected beside a department aggregate.',
    $$SELECT department_id, priority, count(*) FROM maintenance_tickets GROUP BY department_id$$, '42803');
SELECT expect_error('Narrowing the valid report SUM back to a per-record money type overflows.',
    $$SELECT sum(v)::numeric(12,2) FROM (VALUES (9999999999.99::numeric(12,2)), (9999999999.99::numeric(12,2))) AS probe(v)$$, '22003');
SELECT assert_true('All fixture rows are unchanged after the read queries and expected errors.',
    (SELECT count(*) = 3 FROM departments) AND (SELECT count(*) = 2 FROM users)
    AND (SELECT count(*) = 6 FROM maintenance_tickets) AND (SELECT count(*) = 5 FROM work_orders));
ROLLBACK;
SELECT to_regnamespace('college_step11') IS NULL AS cleanup_ok \gset
\if :cleanup_ok
  \echo PASS: ROLLBACK removed the Step 11 schema, fixture, and helpers.
\else
  \echo FAIL: Step 11 objects remain after rollback.
  \ir fail.sql
\endif
