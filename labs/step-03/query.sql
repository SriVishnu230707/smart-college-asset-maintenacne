\set ON_ERROR_STOP on
\pset pager off
\echo === Step 3: five-entity relational model ===
\conninfo
SELECT current_database() = 'college_learning'
       AND current_user = 'college_learner' AS identity_ok \gset
\if :identity_ok
\else
  \echo FAIL: Use the college_learning database and college_learner role.
  \ir ../shared/fail.sql
\endif
SELECT to_regnamespace('college_step03') IS NULL AS namespace_free \gset
\if :namespace_free
\else
  \echo FAIL: college_step03 already exists; inspect it before rerunning.
  \ir ../shared/fail.sql
\endif

-- These fixed synthetic IDs make relationships easy to trace. UUID generation,
-- complete column definitions, and constraint policies are later lessons.
\set cse '10000000-0000-4000-8000-000000000001'
\set ece '10000000-0000-4000-8000-000000000002'
\set projector_category '20000000-0000-4000-8000-000000000001'
\set computer_category '20000000-0000-4000-8000-000000000002'
\set student_cse '30000000-0000-4000-8000-000000000001'
\set student_ece '30000000-0000-4000-8000-000000000002'
\set technician_cse '30000000-0000-4000-8000-000000000003'
\set super_admin '30000000-0000-4000-8000-000000000004'
\set projector '40000000-0000-4000-8000-000000000001'
\set computer_one '40000000-0000-4000-8000-000000000002'
\set computer_two '40000000-0000-4000-8000-000000000003'
\set computer_ece '40000000-0000-4000-8000-000000000004'
\set old_ticket '50000000-0000-4000-8000-000000000001'
\set assigned_ticket '50000000-0000-4000-8000-000000000002'
\set new_ticket '50000000-0000-4000-8000-000000000003'

BEGIN;
CREATE SCHEMA college_step03;
SET LOCAL search_path TO college_step03, public;

CREATE TABLE departments (
    id uuid PRIMARY KEY,
    code text NOT NULL UNIQUE,
    name text NOT NULL
);
CREATE TABLE asset_categories (
    id uuid PRIMARY KEY,
    code text NOT NULL UNIQUE,
    name text NOT NULL
);
CREATE TABLE users (
    id uuid PRIMARY KEY,
    email text NOT NULL UNIQUE,
    display_name text NOT NULL,
    role text NOT NULL,
    department_id uuid REFERENCES departments(id)
);
CREATE TABLE assets (
    id uuid PRIMARY KEY,
    asset_code text NOT NULL UNIQUE,
    name text NOT NULL,
    category_id uuid NOT NULL REFERENCES asset_categories(id),
    department_id uuid NOT NULL REFERENCES departments(id)
);
CREATE TABLE maintenance_tickets (
    id uuid PRIMARY KEY,
    asset_id uuid NOT NULL REFERENCES assets(id),
    reported_by_id uuid NOT NULL REFERENCES users(id),
    assigned_to_id uuid REFERENCES users(id),
    department_id uuid NOT NULL REFERENCES departments(id),
    title text NOT NULL,
    description text NOT NULL,
    status text NOT NULL,
    rejection_reason text
);

INSERT INTO departments VALUES
    (:'cse', 'CSE', 'Computer Science'),
    (:'ece', 'ECE', 'Electronics');
INSERT INTO asset_categories VALUES
    (:'projector_category', 'PROJECTOR', 'Projector'),
    (:'computer_category', 'COMPUTER', 'Computer');
INSERT INTO users VALUES
    (:'student_cse', 'student.cse@example.invalid', 'CSE Student', 'student', :'cse'),
    (:'student_ece', 'student.ece@example.invalid', 'ECE Student', 'student', :'ece'),
    (:'technician_cse', 'technician.cse@example.invalid', 'CSE Technician', 'technician', :'cse'),
    (:'super_admin', 'admin@example.invalid', 'College Admin', 'super_admin', NULL);
INSERT INTO assets VALUES
    (:'projector', 'PRJ-001', 'Classroom Projector', :'projector_category', :'cse'),
    (:'computer_one', 'PC-001', 'Lab Computer', :'computer_category', :'cse'),
    (:'computer_two', 'PC-002', 'Lab Computer', :'computer_category', :'cse'),
    (:'computer_ece', 'ECE-PC-001', 'Lab Computer', :'computer_category', :'ece');
INSERT INTO maintenance_tickets VALUES
    (:'old_ticket', :'projector', :'student_cse', NULL, :'cse',
     'Projector flicker', 'Flicker reported during a demonstration.',
     'rejected', 'Review found the demonstration cable was disconnected; no asset fault.'),
    (:'assigned_ticket', :'computer_one', :'student_cse', :'technician_cse', :'cse',
     'Computer will not start', 'The lab computer does not power on.',
     'assigned', NULL);

\dt college_step03.*
\d college_step03.maintenance_tickets
\echo === Shared department/category facts; repeated asset names are valid ===
SELECT a.asset_code, a.name, c.code AS category, d.code AS current_department
FROM assets AS a
JOIN asset_categories AS c ON c.id = a.category_id
JOIN departments AS d ON d.id = a.department_id
ORDER BY a.asset_code;
SELECT count(*) = 3 AND count(DISTINCT c.id) = 1 AS shared_category_ok
FROM assets AS a JOIN asset_categories AS c ON c.id = a.category_id
WHERE c.code = 'COMPUTER'
\gset
\if :shared_category_ok
  \echo PASS: Three distinct computers share one category record; names need not be unique.
\else
  \echo FAIL: Shared category relationships are incorrect.
  \ir ../shared/fail.sql
\endif
SELECT department_id IS NULL AND role = 'super_admin' AS optional_department_ok
FROM users WHERE id = :'super_admin'
\gset
\if :optional_department_ok
  \echo PASS: A Super Admin can have no department while assets still have a required parent.
\else
  \echo FAIL: Optional user department fixture is incorrect.
  \ir ../shared/fail.sql
\endif

\echo === Reporter and assignee are different user relationships ===
SELECT t.title, reporter.display_name AS reporter,
       assignee.display_name AS assignee
FROM maintenance_tickets AS t
JOIN users AS reporter ON reporter.id = t.reported_by_id
LEFT JOIN users AS assignee ON assignee.id = t.assigned_to_id
ORDER BY t.id;
SELECT t.reported_by_id <> t.assigned_to_id
       AND reporter.role = 'student' AND assignee.role = 'technician'
       AND assignee.department_id = t.department_id AS role_links_ok
FROM maintenance_tickets AS t
JOIN users AS reporter ON reporter.id = t.reported_by_id
JOIN users AS assignee ON assignee.id = t.assigned_to_id
WHERE t.id = :'assigned_ticket'
\gset
\if :role_links_ok
  \echo PASS: Reporter and assignee resolve to separate user identities.
\else
  \echo FAIL: Reporter/assignee links are incorrect.
  \ir ../shared/fail.sql
\endif

\echo === A terminal ticket keeps its department after asset transfer ===
SELECT NOT EXISTS (
    SELECT 1 FROM maintenance_tickets
    WHERE asset_id = :'projector' AND status NOT IN ('closed', 'rejected')
) AS transfer_allowed
\gset
\if :transfer_allowed
  \echo PASS: The transfer fixture has no nonterminal tickets for this asset.
\else
  \echo FAIL: This fixture cannot transfer its asset yet.
  \ir ../shared/fail.sql
\endif
UPDATE assets SET department_id = :'ece' WHERE id = :'projector';
INSERT INTO maintenance_tickets
    (id, asset_id, reported_by_id, assigned_to_id, department_id,
     title, description, status, rejection_reason)
SELECT :'new_ticket', id, :'student_ece', NULL, department_id,
       'Projector input not detected', 'No input is detected after transfer.', 'open', NULL
FROM assets WHERE id = :'projector';
SELECT t.title, t.status, recorded.code AS department_at_report,
       current_owner.code AS current_asset_department
FROM maintenance_tickets AS t
JOIN assets AS a ON a.id = t.asset_id
JOIN departments AS recorded ON recorded.id = t.department_id
JOIN departments AS current_owner ON current_owner.id = a.department_id
WHERE a.id = :'projector'
ORDER BY t.id;
SELECT (SELECT department_id = :'cse' FROM maintenance_tickets WHERE id = :'old_ticket')
       AND (SELECT department_id = :'ece' FROM maintenance_tickets WHERE id = :'new_ticket')
       AND (SELECT department_id = :'ece' FROM assets WHERE id = :'projector')
       AS history_ok
\gset
\if :history_ok
  \echo PASS: The old ticket stays CSE; the transferred asset and new ticket belong to ECE.
\else
  \echo FAIL: Current ownership and recorded history were confused.
  \ir ../shared/fail.sql
\endif

\echo === Counterexample: repeated current supplier details can disagree ===
WITH bad_ticket_copies(ticket_ref, supplier_ref, current_contact) AS (
    VALUES ('T-1', 'SUP-1', 'CONTACT-OLD'), ('T-2', 'SUP-1', 'CONTACT-NEW')
)
SELECT supplier_ref, count(DISTINCT current_contact) AS conflicting_current_contacts
FROM bad_ticket_copies GROUP BY supplier_ref;
WITH bad_ticket_copies(ticket_ref, supplier_ref, current_contact) AS (
    VALUES ('T-1', 'SUP-1', 'CONTACT-OLD'), ('T-2', 'SUP-1', 'CONTACT-NEW')
)
SELECT count(DISTINCT current_contact) > 1 AS anomaly_detected
FROM bad_ticket_copies WHERE supplier_ref = 'SUP-1'
\gset
\if :anomaly_detected
  \echo PASS: The bad design permits contradictory copies of one supplier contact.
\else
  \echo FAIL: The supplier counterexample was not demonstrated.
  \ir ../shared/fail.sql
\endif
WITH suppliers(supplier_ref, current_contact) AS (
    VALUES ('SUP-1', 'CONTACT-NEW')
), spare_parts(part_code, preferred_supplier_ref) AS (
    VALUES ('PART-1', 'SUP-1'), ('PART-10', 'SUP-1')
)
SELECT count(*) = 2 AND count(DISTINCT s.current_contact) = 1 AS normalized_supplier_ok
FROM spare_parts AS p
JOIN suppliers AS s ON s.supplier_ref = p.preferred_supplier_ref
\gset
\if :normalized_supplier_ok
  \echo PASS: Two parts reference one authoritative supplier contact record.
\else
  \echo FAIL: Normalized supplier references are incorrect.
  \ir ../shared/fail.sql
\endif

\echo === Counterexample: substring lookup confuses PART-1 and PART-10 ===
WITH bad_ticket_lists(ticket_ref, part_codes) AS (
    VALUES ('T-WRONG', 'PART-10,PART-20'), ('T-EXACT', 'PART-1,PART-30')
)
SELECT ticket_ref, part_codes FROM bad_ticket_lists
WHERE part_codes LIKE '%PART-1%' ORDER BY ticket_ref;
WITH bad_ticket_lists(ticket_ref, part_codes) AS (
    VALUES ('T-WRONG', 'PART-10,PART-20'), ('T-EXACT', 'PART-1,PART-30')
)
SELECT count(*) = 2 AS false_match_detected
FROM bad_ticket_lists WHERE part_codes LIKE '%PART-1%'
\gset
\if :false_match_detected
  \echo PASS: The encoded part list gives a false substring match for PART-10.
\else
  \echo FAIL: The comma-separated-list counterexample was not demonstrated.
  \ir ../shared/fail.sql
\endif
WITH work_order_parts(work_order_ref, part_code, quantity_used) AS (
    VALUES ('WO-WRONG', 'PART-10', 1), ('WO-WRONG', 'PART-20', 1),
           ('WO-EXACT', 'PART-1', 2), ('WO-EXACT', 'PART-30', 1)
)
SELECT count(*) = 1 AND min(work_order_ref) = 'WO-EXACT'
       AND sum(quantity_used) = 2 AS exact_part_ok
FROM work_order_parts WHERE part_code = 'PART-1'
\gset
\if :exact_part_ok
  \echo PASS: Separate part-use rows give one exact relationship with its own quantity.
\else
  \echo FAIL: Normalized part relationships are incorrect.
  \ir ../shared/fail.sql
\endif

ROLLBACK;
SELECT to_regnamespace('college_step03') IS NULL AS cleanup_ok \gset
\if :cleanup_ok
  \echo PASS: All five demonstration tables and fixtures were rolled back.
\else
  \echo FAIL: The demonstration left an unexpected schema behind.
  \ir ../shared/fail.sql
\endif
