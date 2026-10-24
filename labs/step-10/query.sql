\set ON_ERROR_STOP on
\pset pager off
\pset null '(NULL)'
\echo === Step 10: inner, left, and self joins with explicit aliases ===
\conninfo
SELECT current_database() = 'college_learning' AND current_user = 'college_learner' AS identity_ok \gset
\if :identity_ok
\else
  \echo FAIL: Use the learning database and role.
  \ir fail.sql
\endif
SELECT to_regnamespace('college_step10') IS NULL AS namespace_free \gset
\if :namespace_free
\else
  \echo FAIL: college_step10 already exists; inspect it before rerunning.
  \ir fail.sql
\endif
\set cse '10000000-0000-4000-8000-000000000001'
\set ece '10000000-0000-4000-8000-000000000002'
\set t1 '50000000-0000-4000-8000-000000000001'
\set t2 '50000000-0000-4000-8000-000000000002'
\set t3 '50000000-0000-4000-8000-000000000003'
\set t4 '50000000-0000-4000-8000-000000000004'
\set t5 '50000000-0000-4000-8000-000000000005'
\set t6 '50000000-0000-4000-8000-000000000006'

BEGIN;
CREATE SCHEMA college_step10;
SET LOCAL search_path TO college_step10, public;
-- Reduced projections of the five project entities, with required/optional
-- reference paths. Omitted workflow/completion/audit facts are later lessons.
CREATE TABLE departments (
    id uuid PRIMARY KEY,
    code varchar(20) NOT NULL UNIQUE,
    name varchar(150) NOT NULL
);
CREATE TABLE asset_categories (
    id uuid PRIMARY KEY,
    code varchar(30) NOT NULL UNIQUE,
    name varchar(100) NOT NULL
);
CREATE TABLE users (
    id uuid PRIMARY KEY,
    email text NOT NULL UNIQUE,
    display_name varchar(150) NOT NULL CHECK (display_name !~ '^[[:space:]]*$'),
    role text NOT NULL CHECK (role IN ('student', 'technician', 'department_admin', 'super_admin')),
    department_id uuid REFERENCES departments(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    is_active boolean NOT NULL DEFAULT true,
    CONSTRAINT ck_users_department CHECK (role = 'super_admin' OR department_id IS NOT NULL)
);
CREATE TABLE assets (
    id uuid PRIMARY KEY,
    asset_code varchar(50) NOT NULL UNIQUE,
    name varchar(150) NOT NULL CHECK (name !~ '^[[:space:]]*$'),
    department_id uuid NOT NULL REFERENCES departments(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    category_id uuid NOT NULL REFERENCES asset_categories(id) ON DELETE RESTRICT ON UPDATE RESTRICT
);
CREATE TABLE maintenance_tickets (
    id uuid PRIMARY KEY,
    asset_id uuid NOT NULL REFERENCES assets(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    reported_by_id uuid NOT NULL REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    assigned_to_id uuid REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    department_id uuid NOT NULL REFERENCES departments(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    title varchar(200) NOT NULL CHECK (title !~ '^[[:space:]]*$'),
    status text NOT NULL CHECK (status IN ('open', 'assigned', 'in_progress', 'awaiting_verification', 'closed', 'rejected'))
);
INSERT INTO departments VALUES
    (:'cse', 'CSE', 'Computer Science'),
    (:'ece', 'ECE', 'Electronics'),
    ('10000000-0000-4000-8000-000000000003', 'MECH', 'Mechanical');
INSERT INTO asset_categories VALUES
    ('20000000-0000-4000-8000-000000000001', 'PROJECTOR', 'Projector'),
    ('20000000-0000-4000-8000-000000000002', 'COMPUTER', 'Computer');
INSERT INTO users VALUES
    ('30000000-0000-4000-8000-000000000001', 'alex.cse@example.invalid', 'Alex', 'student', :'cse', true),
    ('30000000-0000-4000-8000-000000000002', 'ravi@example.invalid', 'Ravi', 'technician', :'cse', true),
    ('30000000-0000-4000-8000-000000000003', 'mira@example.invalid', 'Mira', 'technician', :'cse', false),
    ('30000000-0000-4000-8000-000000000004', 'alex.ece@example.invalid', 'Alex', 'student', :'ece', true),
    ('30000000-0000-4000-8000-000000000005', 'nila@example.invalid', 'Nila', 'technician', :'ece', true),
    ('30000000-0000-4000-8000-000000000006', 'admin@example.invalid', 'Campus Admin', 'super_admin', NULL, true);
INSERT INTO assets VALUES
    ('40000000-0000-4000-8000-000000000001', 'PRJ-001', 'Classroom Projector', :'cse', '20000000-0000-4000-8000-000000000001'),
    ('40000000-0000-4000-8000-000000000002', 'PC-001', 'Lab Computer', :'cse', '20000000-0000-4000-8000-000000000002'),
    ('40000000-0000-4000-8000-000000000003', 'PRJ-002', 'Transferred Projector', :'ece', '20000000-0000-4000-8000-000000000001'),
    ('40000000-0000-4000-8000-000000000004', 'PC-002', 'Lab Computer', :'ece', '20000000-0000-4000-8000-000000000002'),
    ('40000000-0000-4000-8000-000000000005', 'PC-003', 'Spare Computer', :'ece', '20000000-0000-4000-8000-000000000002');
-- T5 represents retained terminal history, after transfer/deactivation. It
-- does not create a new assignment to an inactive technician.
INSERT INTO maintenance_tickets VALUES
    (:'t1', '40000000-0000-4000-8000-000000000001', '30000000-0000-4000-8000-000000000001', NULL, :'cse', 'Projector flickers', 'open'),
    (:'t2', '40000000-0000-4000-8000-000000000002', '30000000-0000-4000-8000-000000000001', '30000000-0000-4000-8000-000000000002', :'cse', 'Computer slow', 'assigned'),
    (:'t3', '40000000-0000-4000-8000-000000000004', '30000000-0000-4000-8000-000000000004', NULL, :'ece', 'Computer display issue', 'open'),
    (:'t4', '40000000-0000-4000-8000-000000000001', '30000000-0000-4000-8000-000000000002', '30000000-0000-4000-8000-000000000002', :'cse', 'Technician self-report', 'in_progress'),
    (:'t5', '40000000-0000-4000-8000-000000000003', '30000000-0000-4000-8000-000000000001', '30000000-0000-4000-8000-000000000003', :'cse', 'Historical projector repair', 'closed'),
    (:'t6', '40000000-0000-4000-8000-000000000004', '30000000-0000-4000-8000-000000000004', '30000000-0000-4000-8000-000000000005', :'ece', 'Computer keyboard issue', 'assigned');

-- Verification helpers execute only the literal SELECTs in this file.
-- Ordered result arrays retain row multiplicity; JSON additionally preserves
-- projected column names/NULLs when checking complete display rows. Their
-- aggregate/subquery internals are scaffolding for later query lessons.
CREATE FUNCTION assert_keys(label text, statement text, expected text[])
RETURNS text LANGUAGE plpgsql AS $$
DECLARE actual text[];
BEGIN
    EXECUTE 'SELECT ARRAY(' || statement || ')::text[]' INTO actual;
    IF actual IS DISTINCT FROM expected THEN RAISE EXCEPTION '%: expected %, observed %', label, expected, actual; END IF;
    RETURN 'PASS: ' || label || ' Observed=' || actual::text;
END $$;
CREATE FUNCTION assert_rows(label text, statement text, expected jsonb)
RETURNS text LANGUAGE plpgsql AS $$
DECLARE actual jsonb;
BEGIN
    -- Each supplied query has a complete ORDER BY. The outer expression
    -- only serializes that ordered subquery, with no additional joins.
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

\echo === Ticket details retain unassigned and historical assignments ===
SELECT t.id, t.title, a.asset_code, a.name AS asset_name,
       reporter.display_name AS reporter_name, assignee.display_name AS assignee_name,
       assignee.is_active AS assignee_active
FROM maintenance_tickets AS t
JOIN assets AS a ON a.id = t.asset_id
JOIN users AS reporter ON reporter.id = t.reported_by_id
LEFT JOIN users AS assignee ON assignee.id = t.assigned_to_id
ORDER BY t.id;
\pset format unaligned
\pset tuples_only on
SELECT assert_rows('The detail query returns all six tickets with the correct asset, reporter, and optional assignee names.',
    $$SELECT t.id, t.title, a.asset_code, a.name AS asset_name,
             reporter.display_name AS reporter_name, assignee.display_name AS assignee_name,
             assignee.is_active AS assignee_active
      FROM maintenance_tickets AS t
      JOIN assets AS a ON a.id = t.asset_id
      JOIN users AS reporter ON reporter.id = t.reported_by_id
      LEFT JOIN users AS assignee ON assignee.id = t.assigned_to_id ORDER BY t.id$$,
    $$[
      {"id":"50000000-0000-4000-8000-000000000001","title":"Projector flickers","asset_code":"PRJ-001","asset_name":"Classroom Projector","reporter_name":"Alex","assignee_name":null,"assignee_active":null},
      {"id":"50000000-0000-4000-8000-000000000002","title":"Computer slow","asset_code":"PC-001","asset_name":"Lab Computer","reporter_name":"Alex","assignee_name":"Ravi","assignee_active":true},
      {"id":"50000000-0000-4000-8000-000000000003","title":"Computer display issue","asset_code":"PC-002","asset_name":"Lab Computer","reporter_name":"Alex","assignee_name":null,"assignee_active":null},
      {"id":"50000000-0000-4000-8000-000000000004","title":"Technician self-report","asset_code":"PRJ-001","asset_name":"Classroom Projector","reporter_name":"Ravi","assignee_name":"Ravi","assignee_active":true},
      {"id":"50000000-0000-4000-8000-000000000005","title":"Historical projector repair","asset_code":"PRJ-002","asset_name":"Transferred Projector","reporter_name":"Alex","assignee_name":"Mira","assignee_active":false},
      {"id":"50000000-0000-4000-8000-000000000006","title":"Computer keyboard issue","asset_code":"PC-002","asset_name":"Lab Computer","reporter_name":"Alex","assignee_name":"Nila","assignee_active":true}
    ]$$::jsonb);
SELECT assert_keys('LEFT JOIN preserves every ticket when the optional assignee is missing.',
    $$SELECT t.id::text FROM maintenance_tickets AS t LEFT JOIN users AS assignee ON assignee.id = t.assigned_to_id ORDER BY t.id$$,
    ARRAY[:'t1', :'t2', :'t3', :'t4', :'t5', :'t6']);
SELECT assert_keys('INNER JOIN to the optional assignee removes the two unassigned tickets.',
    $$SELECT t.id::text FROM maintenance_tickets AS t JOIN users AS assignee ON assignee.id = t.assigned_to_id ORDER BY t.id$$,
    ARRAY[:'t2', :'t4', :'t5', :'t6']);
SELECT assert_rows('Repeated display names still resolve to the correct distinct reporter identities.',
    $$SELECT t.id, reporter.email, reporter.display_name FROM maintenance_tickets AS t
      JOIN users AS reporter ON reporter.id = t.reported_by_id
      WHERE t.id IN ('50000000-0000-4000-8000-000000000001', '50000000-0000-4000-8000-000000000003') ORDER BY t.id$$,
    $$[{"id":"50000000-0000-4000-8000-000000000001","email":"alex.cse@example.invalid","display_name":"Alex"},
       {"id":"50000000-0000-4000-8000-000000000003","email":"alex.ece@example.invalid","display_name":"Alex"}]$$::jsonb);
SELECT assert_true('Separate reporter and assignee aliases allow one technician to occupy both roles.',
    (SELECT reporter.id = assignee.id AND reporter.display_name = 'Ravi'
     FROM maintenance_tickets AS t JOIN users AS reporter ON reporter.id = t.reported_by_id
     JOIN users AS assignee ON assignee.id = t.assigned_to_id WHERE t.id = :'t4'));

\echo === ON controls matches; WHERE filters the resulting joined rows ===
SELECT assert_keys('A right-side active predicate in WHERE removes unassigned and inactive-assignee tickets.',
    $$SELECT t.id::text FROM maintenance_tickets AS t LEFT JOIN users AS assignee ON assignee.id = t.assigned_to_id
      WHERE assignee.is_active ORDER BY t.id$$, ARRAY[:'t2', :'t4', :'t6']);
SELECT assert_keys('Moving the active predicate into ON retains all tickets and restricts only the right-side match.',
    $$SELECT t.id::text FROM maintenance_tickets AS t LEFT JOIN users AS assignee
      ON assignee.id = t.assigned_to_id AND assignee.is_active ORDER BY t.id$$,
    ARRAY[:'t1', :'t2', :'t3', :'t4', :'t5', :'t6']);
SELECT assert_rows('A filtered-out inactive assignee and an absent assignment both have NULL joined columns but different stored IDs.',
    $$SELECT t.id, t.assigned_to_id AS stored_assignee_id, assignee.id AS matched_assignee_id,
             assignee.display_name AS matched_assignee_name
      FROM maintenance_tickets AS t LEFT JOIN users AS assignee
      ON assignee.id = t.assigned_to_id AND assignee.is_active
      WHERE t.id IN ('50000000-0000-4000-8000-000000000001', '50000000-0000-4000-8000-000000000005') ORDER BY t.id$$,
    $$[{"id":"50000000-0000-4000-8000-000000000001","stored_assignee_id":null,"matched_assignee_id":null,"matched_assignee_name":null},
       {"id":"50000000-0000-4000-8000-000000000005","stored_assignee_id":"30000000-0000-4000-8000-000000000003","matched_assignee_id":null,"matched_assignee_name":null}]$$::jsonb);
SELECT assert_keys('Testing the filtered joined ID for NULL also selects the inactive historical assignment.',
    $$SELECT t.id::text FROM maintenance_tickets AS t LEFT JOIN users AS assignee
      ON assignee.id = t.assigned_to_id AND assignee.is_active WHERE assignee.id IS NULL ORDER BY t.id$$,
    ARRAY[:'t1', :'t3', :'t5']);
SELECT assert_keys('Testing the stored foreign key for NULL selects only genuinely unassigned tickets.',
    $$SELECT t.id::text FROM maintenance_tickets AS t LEFT JOIN users AS assignee
      ON assignee.id = t.assigned_to_id AND assignee.is_active WHERE t.assigned_to_id IS NULL ORDER BY t.id$$,
    ARRAY[:'t1', :'t3']);
SELECT assert_keys('Adding OR joined-ID IS NULL to WHERE still excludes a real inactive match.',
    $$SELECT t.id::text FROM maintenance_tickets AS t LEFT JOIN users AS assignee ON assignee.id = t.assigned_to_id
      WHERE assignee.is_active OR assignee.id IS NULL ORDER BY t.id$$,
    ARRAY[:'t1', :'t2', :'t3', :'t4', :'t6']);
SELECT assert_keys('A left-side department filter keeps the scoped unassigned ticket and retained history.',
    $$SELECT t.id::text FROM maintenance_tickets AS t LEFT JOIN users AS assignee ON assignee.id = t.assigned_to_id
      WHERE t.department_id = '10000000-0000-4000-8000-000000000001' ORDER BY t.id$$,
    ARRAY[:'t1', :'t2', :'t4', :'t5']);

\echo === Choose the correct reference path for historical department ===
SELECT assert_rows('Distinct department aliases preserve recorded attribution after an asset transfer.',
    $$SELECT t.id, a.asset_code, recorded_department.code AS recorded_department,
             current_department.code AS current_asset_department
      FROM maintenance_tickets AS t JOIN assets AS a ON a.id = t.asset_id
      JOIN departments AS recorded_department ON recorded_department.id = t.department_id
      JOIN departments AS current_department ON current_department.id = a.department_id
      WHERE t.id = '50000000-0000-4000-8000-000000000005' ORDER BY t.id$$,
    $$[{"id":"50000000-0000-4000-8000-000000000005","asset_code":"PRJ-002","recorded_department":"CSE","current_asset_department":"ECE"}]$$::jsonb);

\echo === One-to-many joins preserve multiplicity and unmatched parents ===
SELECT assert_keys('The asset-to-ticket INNER JOIN repeats assets with multiple tickets and omits the unused asset.',
    $$SELECT a.asset_code || ':' || t.id::text FROM assets AS a JOIN maintenance_tickets AS t ON t.asset_id = a.id
      ORDER BY a.asset_code COLLATE "C", t.id$$,
    ARRAY['PC-001:' || :'t2', 'PC-002:' || :'t3', 'PC-002:' || :'t6', 'PRJ-001:' || :'t1', 'PRJ-001:' || :'t4', 'PRJ-002:' || :'t5']);
SELECT assert_keys('The asset-to-ticket LEFT JOIN additionally retains the unused asset with a NULL ticket.',
    $$SELECT a.asset_code || ':' || coalesce(t.id::text, '<no match>') FROM assets AS a
      LEFT JOIN maintenance_tickets AS t ON t.asset_id = a.id ORDER BY a.asset_code COLLATE "C", t.id$$,
    ARRAY['PC-001:' || :'t2', 'PC-002:' || :'t3', 'PC-002:' || :'t6', 'PC-003:<no match>', 'PRJ-001:' || :'t1', 'PRJ-001:' || :'t4', 'PRJ-002:' || :'t5']);
SELECT assert_keys('Filtering child status in WHERE leaves only assets that have open tickets.',
    $$SELECT a.asset_code || ':' || t.id::text FROM assets AS a LEFT JOIN maintenance_tickets AS t ON t.asset_id = a.id
      WHERE t.status = 'open' ORDER BY a.asset_code COLLATE "C", t.id$$,
    ARRAY['PC-002:' || :'t3', 'PRJ-001:' || :'t1']);
SELECT assert_keys('Filtering child status in ON retains every asset while matching only its open tickets.',
    $$SELECT a.asset_code || ':' || coalesce(t.id::text, '<no match>') FROM assets AS a
      LEFT JOIN maintenance_tickets AS t ON t.asset_id = a.id AND t.status = 'open'
      ORDER BY a.asset_code COLLATE "C", t.id$$,
    ARRAY['PC-001:<no match>', 'PC-002:' || :'t3', 'PC-003:<no match>', 'PRJ-001:' || :'t1', 'PRJ-002:<no match>']);
SELECT assert_true('Joining a reporter by department instead of the recorded user ID incorrectly multiplies six tickets into sixteen rows.',
    (SELECT count(*) = 16 FROM maintenance_tickets AS t JOIN users AS reporter ON reporter.department_id = t.department_id));

\echo === Self join: one unordered same-department pair per two users ===
SELECT assert_keys('A self join with distinct aliases and ordered IDs produces each same-department user pair once.',
    $$SELECT first_user.email || ' -> ' || second_user.email FROM users AS first_user JOIN users AS second_user
      ON first_user.department_id = second_user.department_id AND first_user.id < second_user.id
      ORDER BY first_user.id, second_user.id$$,
    ARRAY['alex.cse@example.invalid -> ravi@example.invalid', 'alex.cse@example.invalid -> mira@example.invalid',
          'ravi@example.invalid -> mira@example.invalid', 'alex.ece@example.invalid -> nila@example.invalid']);
SELECT assert_true('Without the ID ordering restriction the same-department self join includes self-pairs and reversed pairs.',
    (SELECT count(*) = 13 FROM users AS first_user JOIN users AS second_user
     ON first_user.department_id = second_user.department_id));

\echo === Invalid column and alias references fail with exact SQLSTATE ===
SELECT expect_error('An unqualified ID is ambiguous when both joined tables have that column.',
    $$SELECT id FROM maintenance_tickets AS t JOIN assets AS a ON a.id = t.asset_id$$, '42702');
SELECT expect_error('Two references to users require different aliases.',
    $$SELECT t.id FROM maintenance_tickets AS t JOIN users AS person ON person.id = t.reported_by_id
      LEFT JOIN users AS person ON person.id = t.assigned_to_id$$, '42712');
SELECT expect_error('An assigned table alias replaces the original qualifier in the query.',
    $$SELECT users.display_name FROM users AS reporter$$, '42P01');
SELECT assert_true('All join and invalid-query experiments leave the fixture rows unchanged.',
    (SELECT count(*) = 3 FROM departments) AND (SELECT count(*) = 2 FROM asset_categories)
    AND (SELECT count(*) = 6 FROM users) AND (SELECT count(*) = 5 FROM assets)
    AND (SELECT count(*) = 6 FROM maintenance_tickets));
\pset tuples_only off
\pset format aligned
ROLLBACK;
SELECT to_regnamespace('college_step10') IS NULL AS cleanup_ok \gset
\if :cleanup_ok
  \echo PASS: All Step 10 fixtures, tables, and verification helpers were rolled back.
\else
  \echo FAIL: The Step 10 demonstration left its schema behind.
  \ir fail.sql
\endif
