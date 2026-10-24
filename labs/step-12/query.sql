\set ON_ERROR_STOP on
\pset pager off
\pset null '(NULL)'
\echo === Step 12: scalar and correlated subqueries, existence, and sets ===
\conninfo
SELECT current_database() = 'college_learning' AND current_user = 'college_learner' AS identity_ok \gset
\if :identity_ok
\else
  \echo FAIL: Use the learning database and role.
  \ir ../shared/fail.sql
\endif
SELECT to_regnamespace('college_step12') IS NULL AS namespace_free \gset
\if :namespace_free
\else
  \echo FAIL: college_step12 already exists; inspect it before rerunning.
  \ir ../shared/fail.sql
\endif

BEGIN;
CREATE SCHEMA college_step12;
SET LOCAL search_path TO college_step12, public;
-- Reduced query projections. Reporter/category/completion/audit facts and
-- authorized mutations are omitted; these are not production migrations.
CREATE TABLE departments (id uuid PRIMARY KEY, code text NOT NULL UNIQUE);
CREATE TABLE users (
    id uuid PRIMARY KEY,
    email text NOT NULL UNIQUE,
    department_id uuid REFERENCES departments(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    role text NOT NULL CHECK (role IN ('student', 'technician', 'department_admin', 'super_admin')),
    is_active boolean NOT NULL,
    CHECK (role = 'super_admin' OR department_id IS NOT NULL)
);
CREATE TABLE assets (
    id uuid PRIMARY KEY,
    asset_code text NOT NULL UNIQUE,
    department_id uuid NOT NULL REFERENCES departments(id) ON DELETE RESTRICT ON UPDATE RESTRICT
);
CREATE TABLE maintenance_tickets (
    id uuid PRIMARY KEY,
    asset_id uuid NOT NULL REFERENCES assets(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    department_id uuid NOT NULL REFERENCES departments(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    assigned_to_id uuid REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    status text NOT NULL CHECK (status IN ('open', 'assigned', 'in_progress', 'awaiting_verification', 'closed', 'rejected'))
);
INSERT INTO departments VALUES
    ('10000000-0000-4000-8000-000000000001', 'CSE'),
    ('10000000-0000-4000-8000-000000000002', 'ECE'),
    ('10000000-0000-4000-8000-000000000003', 'MECH');
INSERT INTO users VALUES
    ('30000000-0000-4000-8000-000000000001', 'ravi@example.invalid', '10000000-0000-4000-8000-000000000001', 'technician', true),
    ('30000000-0000-4000-8000-000000000002', 'nila@example.invalid', '10000000-0000-4000-8000-000000000002', 'technician', true),
    ('30000000-0000-4000-8000-000000000003', 'omar@example.invalid', '10000000-0000-4000-8000-000000000001', 'technician', true),
    ('30000000-0000-4000-8000-000000000004', 'mira@example.invalid', '10000000-0000-4000-8000-000000000001', 'technician', false),
    ('30000000-0000-4000-8000-000000000005', 'alex@example.invalid', '10000000-0000-4000-8000-000000000001', 'student', true),
    ('30000000-0000-4000-8000-000000000006', 'admin@example.invalid', NULL, 'super_admin', true),
    ('30000000-0000-4000-8000-000000000007', 'leela@example.invalid', '10000000-0000-4000-8000-000000000002', 'technician', true);
INSERT INTO assets VALUES
    ('40000000-0000-4000-8000-000000000001', 'PRJ-001', '10000000-0000-4000-8000-000000000001'),
    ('40000000-0000-4000-8000-000000000002', 'PC-001', '10000000-0000-4000-8000-000000000001'),
    ('40000000-0000-4000-8000-000000000003', 'PRJ-002', '10000000-0000-4000-8000-000000000002'),
    ('40000000-0000-4000-8000-000000000004', 'PC-002', '10000000-0000-4000-8000-000000000002'),
    ('40000000-0000-4000-8000-000000000005', 'PC-003', '10000000-0000-4000-8000-000000000002');
-- T4 is terminal history before transfer/deactivation; T6 retains Leela's
-- completed assignment. Neither means that technician has current work.
INSERT INTO maintenance_tickets VALUES
    ('50000000-0000-4000-8000-000000000001', '40000000-0000-4000-8000-000000000001', '10000000-0000-4000-8000-000000000001', NULL, 'open'),
    ('50000000-0000-4000-8000-000000000002', '40000000-0000-4000-8000-000000000001', '10000000-0000-4000-8000-000000000001', '30000000-0000-4000-8000-000000000001', 'assigned'),
    ('50000000-0000-4000-8000-000000000003', '40000000-0000-4000-8000-000000000002', '10000000-0000-4000-8000-000000000001', '30000000-0000-4000-8000-000000000001', 'in_progress'),
    ('50000000-0000-4000-8000-000000000004', '40000000-0000-4000-8000-000000000003', '10000000-0000-4000-8000-000000000001', '30000000-0000-4000-8000-000000000004', 'closed'),
    ('50000000-0000-4000-8000-000000000005', '40000000-0000-4000-8000-000000000004', '10000000-0000-4000-8000-000000000002', '30000000-0000-4000-8000-000000000002', 'assigned'),
    ('50000000-0000-4000-8000-000000000006', '40000000-0000-4000-8000-000000000004', '10000000-0000-4000-8000-000000000002', '30000000-0000-4000-8000-000000000007', 'closed');

-- Literal SELECTs only; JSON preserves complete expected rows and NULLs.
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

\echo === Ask whether each asset has any ticket, including history ===
SELECT a.asset_code FROM assets AS a
WHERE NOT EXISTS (SELECT 1 FROM maintenance_tickets AS t WHERE t.asset_id = a.id)
ORDER BY a.asset_code COLLATE "C";
\pset format unaligned
\pset tuples_only on
SELECT assert_rows('Correlated NOT EXISTS finds exactly the unused asset.',
    $$SELECT a.asset_code FROM assets AS a WHERE NOT EXISTS
      (SELECT 1 FROM maintenance_tickets AS t WHERE t.asset_id = a.id) ORDER BY a.asset_code COLLATE "C"$$,
    '[{"asset_code":"PC-003"}]');
SELECT assert_rows('A left anti-join on the nonnullable child primary key finds the same unused asset.',
    $$SELECT a.asset_code FROM assets AS a LEFT JOIN maintenance_tickets AS t ON t.asset_id = a.id
      WHERE t.id IS NULL ORDER BY a.asset_code COLLATE "C"$$, '[{"asset_code":"PC-003"}]');
SELECT assert_rows('EXCEPT subtracts ticketed asset identities from the full asset set.',
    $$SELECT asset_code FROM (SELECT asset_code FROM assets EXCEPT
      SELECT a.asset_code FROM assets AS a JOIN maintenance_tickets AS t ON t.asset_id = a.id) AS unused
      ORDER BY asset_code COLLATE "C"$$, '[{"asset_code":"PC-003"}]');
SELECT assert_rows('EXISTS returns each ticketed asset once despite repeated tickets.',
    $$SELECT a.asset_code FROM assets AS a WHERE EXISTS
      (SELECT 1 FROM maintenance_tickets AS t WHERE t.asset_id = a.id) ORDER BY a.asset_code COLLATE "C"$$,
    '[{"asset_code":"PC-001"},{"asset_code":"PC-002"},{"asset_code":"PRJ-001"},{"asset_code":"PRJ-002"}]');
SELECT assert_rows('Removing the correlation asks one global question and wrongly excludes every asset.',
    $$SELECT a.asset_code FROM assets AS a WHERE NOT EXISTS
      (SELECT 1 FROM maintenance_tickets AS t) ORDER BY a.asset_code COLLATE "C"$$, '[]');

\echo === Scalar subqueries: one value, NULL when empty, error when multiple rows ===
SELECT assert_rows('A unique scalar lookup returns one value; a zero-row scalar lookup returns NULL.',
    $$SELECT (SELECT code FROM departments WHERE code = 'CSE') AS known_department,
             (SELECT code FROM departments WHERE code = 'UNKNOWN') AS missing_department$$,
    '[{"known_department":"CSE","missing_department":null}]');
SELECT assert_rows('A correlated aggregate scalar reports the complete hand-counted ticket totals per asset.',
    $$SELECT a.asset_code, (SELECT count(*) FROM maintenance_tickets AS t WHERE t.asset_id = a.id) AS tickets
      FROM assets AS a ORDER BY a.asset_code COLLATE "C"$$,
    '[{"asset_code":"PC-001","tickets":1},{"asset_code":"PC-002","tickets":2},{"asset_code":"PC-003","tickets":0},{"asset_code":"PRJ-001","tickets":2},{"asset_code":"PRJ-002","tickets":1}]');
SELECT assert_rows('Filtering the correlated scalar count to zero agrees with NOT EXISTS.',
    $$SELECT a.asset_code FROM assets AS a WHERE
      (SELECT count(*) FROM maintenance_tickets AS t WHERE t.asset_id = a.id) = 0
      ORDER BY a.asset_code COLLATE "C"$$, '[{"asset_code":"PC-003"}]');
SELECT assert_rows('EXISTS tests returned rows: a selected NULL is still a row, while a false predicate returns none.',
    $$SELECT EXISTS (SELECT NULL::uuid) AS null_row_exists,
             EXISTS (SELECT NULL::uuid WHERE false) AS empty_exists$$,
    '[{"null_row_exists":true,"empty_exists":false}]');
SELECT assert_rows('An ungrouped COUNT over empty input still returns a row, so wrapping it in EXISTS is a trap.',
    $$SELECT EXISTS (SELECT count(*) FROM maintenance_tickets WHERE false) AS aggregate_row_exists,
             EXISTS (SELECT 1 FROM maintenance_tickets WHERE false) AS matching_row_exists$$,
    '[{"aggregate_row_exists":true,"matching_row_exists":false}]');

\echo === Current assigned tickets differ from retained terminal assignments ===
SELECT assert_rows('Active technicians with nonterminal assigned tickets are Ravi and Nila, each returned once.',
    $$SELECT u.email FROM users AS u WHERE u.role = 'technician' AND u.is_active AND EXISTS
      (SELECT 1 FROM maintenance_tickets AS t WHERE t.assigned_to_id = u.id
       AND t.status IN ('assigned','in_progress','awaiting_verification')) ORDER BY u.id$$,
    '[{"email":"ravi@example.invalid"},{"email":"nila@example.invalid"}]');
SELECT assert_rows('The equivalent raw inner join repeats Ravi because he has two matching tickets.',
    $$SELECT u.email FROM users AS u JOIN maintenance_tickets AS t ON t.assigned_to_id = u.id
      WHERE u.role = 'technician' AND u.is_active AND t.status IN ('assigned','in_progress','awaiting_verification')
      ORDER BY u.id, t.id$$,
    '[{"email":"ravi@example.invalid"},{"email":"ravi@example.invalid"},{"email":"nila@example.invalid"}]');
SELECT assert_rows('DISTINCT on user identity and email restores the same one-row-per-technician result.',
    $$SELECT matched.email FROM (SELECT DISTINCT u.id, u.email FROM users AS u
      JOIN maintenance_tickets AS t ON t.assigned_to_id = u.id WHERE u.role = 'technician' AND u.is_active
      AND t.status IN ('assigned','in_progress','awaiting_verification')) AS matched ORDER BY matched.id$$,
    '[{"email":"ravi@example.invalid"},{"email":"nila@example.invalid"}]');
SELECT assert_rows('Any-assignment history also includes inactive Mira and active Leela, whose only tickets are terminal.',
    $$SELECT u.email FROM users AS u WHERE u.role = 'technician' AND EXISTS
      (SELECT 1 FROM maintenance_tickets AS t WHERE t.assigned_to_id = u.id) ORDER BY u.id$$,
    '[{"email":"ravi@example.invalid"},{"email":"nila@example.invalid"},{"email":"mira@example.invalid"},{"email":"leela@example.invalid"}]');
SELECT assert_rows('Active technicians without current assigned tickets include both never-assigned Omar and historical-only Leela.',
    $$SELECT u.email FROM users AS u WHERE u.role = 'technician' AND u.is_active AND NOT EXISTS
      (SELECT 1 FROM maintenance_tickets AS t WHERE t.assigned_to_id = u.id
       AND t.status IN ('assigned','in_progress','awaiting_verification')) ORDER BY u.id$$,
    '[{"email":"omar@example.invalid"},{"email":"leela@example.invalid"}]');

\echo === NOT IN over the nullable assignee column can return UNKNOWN ===
SELECT assert_rows('For the different question of no assignment ever, correlated NOT EXISTS returns only Omar.',
    $$SELECT u.email FROM users AS u WHERE u.role = 'technician' AND u.is_active AND NOT EXISTS
      (SELECT 1 FROM maintenance_tickets AS t WHERE t.assigned_to_id = u.id) ORDER BY u.id$$,
    '[{"email":"omar@example.invalid"}]');
SELECT assert_rows('Raw NOT IN incorrectly loses Omar because the assignee subquery contains NULL.',
    $$SELECT u.email FROM users AS u WHERE u.role = 'technician' AND u.is_active
      AND u.id NOT IN (SELECT t.assigned_to_id FROM maintenance_tickets AS t) ORDER BY u.id$$, '[]');
SELECT assert_rows('The raw NOT IN predicate is false for a real match and NULL for the unmatched Omar.',
    $$SELECT u.email, u.id NOT IN (SELECT t.assigned_to_id FROM maintenance_tickets AS t) AS never_assigned
      FROM users AS u WHERE u.email IN ('ravi@example.invalid','omar@example.invalid') ORDER BY u.id$$,
    '[{"email":"ravi@example.invalid","never_assigned":false},{"email":"omar@example.invalid","never_assigned":null}]');
SELECT assert_rows('Removing NULL right-side values makes NOT IN agree for the nonnullable outer user key.',
    $$SELECT u.email FROM users AS u WHERE u.role = 'technician' AND u.is_active AND u.id NOT IN
      (SELECT t.assigned_to_id FROM maintenance_tickets AS t WHERE t.assigned_to_id IS NOT NULL) ORDER BY u.id$$,
    '[{"email":"omar@example.invalid"}]');
SELECT assert_rows('NOT IN against an empty assignment result includes all four active technicians.',
    $$SELECT u.email FROM users AS u WHERE u.role = 'technician' AND u.is_active
      AND u.id NOT IN (SELECT t.assigned_to_id FROM maintenance_tickets AS t WHERE false) ORDER BY u.id$$,
    '[{"email":"ravi@example.invalid"},{"email":"nila@example.invalid"},{"email":"omar@example.invalid"},{"email":"leela@example.invalid"}]');
SELECT assert_rows('An isolated nullable outer value remains UNKNOWN against nonempty values but passes an empty NOT IN set.',
    $$SELECT NULL::uuid NOT IN (SELECT id FROM users) AS null_against_values,
             NULL::uuid NOT IN (SELECT id FROM users WHERE false) AS null_against_empty$$,
    '[{"null_against_values":null,"null_against_empty":true}]');

\echo === Set operations compare projected rows, with explicit final ordering ===
SELECT assert_rows('UNION merges the open-ticket and current-assigned-asset sets without duplicate asset codes.',
    $$SELECT asset_code FROM (
        SELECT a.asset_code FROM assets AS a WHERE EXISTS
          (SELECT 1 FROM maintenance_tickets AS t WHERE t.asset_id = a.id AND t.status = 'open')
        UNION
        SELECT a.asset_code FROM assets AS a WHERE EXISTS
          (SELECT 1 FROM maintenance_tickets AS t WHERE t.asset_id = a.id AND t.status IN ('assigned','in_progress','awaiting_verification'))
      ) AS combined ORDER BY asset_code COLLATE "C"$$,
    '[{"asset_code":"PC-001"},{"asset_code":"PC-002"},{"asset_code":"PRJ-001"}]');
SELECT assert_rows('UNION ALL keeps PRJ-001 twice because it belongs to both input sets.',
    $$SELECT asset_code FROM (
        SELECT a.asset_code FROM assets AS a WHERE EXISTS
          (SELECT 1 FROM maintenance_tickets AS t WHERE t.asset_id = a.id AND t.status = 'open')
        UNION ALL
        SELECT a.asset_code FROM assets AS a WHERE EXISTS
          (SELECT 1 FROM maintenance_tickets AS t WHERE t.asset_id = a.id AND t.status IN ('assigned','in_progress','awaiting_verification'))
      ) AS combined ORDER BY asset_code COLLATE "C"$$,
    '[{"asset_code":"PC-001"},{"asset_code":"PC-002"},{"asset_code":"PRJ-001"},{"asset_code":"PRJ-001"}]');
SELECT assert_rows('INTERSECT retains only PRJ-001, the asset in both input sets.',
    $$SELECT asset_code FROM (
        SELECT a.asset_code FROM assets AS a WHERE EXISTS
          (SELECT 1 FROM maintenance_tickets AS t WHERE t.asset_id = a.id AND t.status = 'open')
        INTERSECT
        SELECT a.asset_code FROM assets AS a WHERE EXISTS
          (SELECT 1 FROM maintenance_tickets AS t WHERE t.asset_id = a.id AND t.status IN ('assigned','in_progress','awaiting_verification'))
      ) AS common_assets ORDER BY asset_code COLLATE "C"$$, '[{"asset_code":"PRJ-001"}]');
SELECT assert_rows('Ticketed assets EXCEPT current-assigned assets finds historical-only PRJ-002, not unused PC-003.',
    $$SELECT asset_code FROM (
        SELECT a.asset_code FROM assets AS a WHERE EXISTS (SELECT 1 FROM maintenance_tickets AS t WHERE t.asset_id = a.id)
        EXCEPT
        SELECT a.asset_code FROM assets AS a WHERE EXISTS
          (SELECT 1 FROM maintenance_tickets AS t WHERE t.asset_id = a.id AND t.status IN ('assigned','in_progress','awaiting_verification'))
      ) AS historical_only ORDER BY asset_code COLLATE "C"$$, '[{"asset_code":"PRJ-002"}]');

\echo === Invalid scalar and set shapes fail with exact SQLSTATE ===
SELECT expect_error('A multirow scalar lookup fails instead of choosing an arbitrary user.',
    $$SELECT (SELECT email FROM users WHERE department_id = '10000000-0000-4000-8000-000000000001')$$, '21000');
SELECT expect_error('Set inputs must project the same number of columns.',
    $$SELECT asset_code FROM assets UNION SELECT id, status FROM maintenance_tickets$$, '42601');
SELECT expect_error('Corresponding set columns must have compatible types.',
    $$SELECT asset_code FROM assets UNION SELECT id FROM maintenance_tickets$$, '42804');
SELECT assert_true('The three departments, seven users, five assets, and six tickets remain unchanged.',
    (SELECT count(*) = 3 FROM departments) AND (SELECT count(*) = 7 FROM users)
    AND (SELECT count(*) = 5 FROM assets) AND (SELECT count(*) = 6 FROM maintenance_tickets));
ROLLBACK;
SELECT to_regnamespace('college_step12') IS NULL AS cleanup_ok \gset
\if :cleanup_ok
  \echo PASS: ROLLBACK removed the Step 12 schema, fixture, and helpers.
\else
  \echo FAIL: Step 12 objects remain after rollback.
  \ir ../shared/fail.sql
\endif
