\set ON_ERROR_STOP on
\pset pager off
\echo === Step 7: foreign keys, composite references, and deletion policies ===
\conninfo
SELECT current_database() = 'college_learning'
       AND current_user = 'college_learner' AS identity_ok \gset
\if :identity_ok
\else
  \echo FAIL: Use the learning database and role.
  \ir ../shared/fail.sql
\endif
SELECT to_regnamespace('college_step07') IS NULL AS namespace_free \gset
\if :namespace_free
\else
  \echo FAIL: college_step07 already exists; inspect it before rerunning.
  \ir ../shared/fail.sql
\endif

BEGIN;
CREATE SCHEMA college_step07;
SET LOCAL search_path TO college_step07, public;
-- Reduced project tables: this lesson adds reference policy, not the full
-- application schema or workflow. Retained terminal ticket snapshots below
-- omit repair/audit details, which are introduced in later steps.
CREATE TABLE departments (
    id uuid DEFAULT gen_random_uuid() CONSTRAINT pk_departments PRIMARY KEY,
    code varchar(20) NOT NULL CONSTRAINT uq_departments_code UNIQUE,
    name varchar(150) NOT NULL,
    is_archived boolean NOT NULL DEFAULT false
);
CREATE TABLE asset_categories (
    id uuid DEFAULT gen_random_uuid() CONSTRAINT pk_asset_categories PRIMARY KEY,
    code varchar(30) NOT NULL CONSTRAINT uq_asset_categories_code UNIQUE,
    is_archived boolean NOT NULL DEFAULT false
);
CREATE TABLE users (
    id uuid DEFAULT gen_random_uuid() CONSTRAINT pk_users PRIMARY KEY,
    email text NOT NULL CONSTRAINT uq_users_email UNIQUE,
    role text NOT NULL,
    department_id uuid,
    is_active boolean NOT NULL DEFAULT true,
    CONSTRAINT ck_users_role CHECK (role IN ('student', 'technician', 'department_admin', 'super_admin')),
    CONSTRAINT ck_users_department CHECK (role = 'super_admin' OR department_id IS NOT NULL),
    CONSTRAINT fk_users_department FOREIGN KEY (department_id)
        REFERENCES departments(id) ON DELETE RESTRICT ON UPDATE RESTRICT
);
CREATE TABLE assets (
    id uuid DEFAULT gen_random_uuid() CONSTRAINT pk_assets PRIMARY KEY,
    asset_code varchar(50) NOT NULL CONSTRAINT uq_assets_asset_code UNIQUE,
    department_id uuid CONSTRAINT nn_assets_department NOT NULL,
    category_id uuid CONSTRAINT nn_assets_category NOT NULL,
    status text NOT NULL DEFAULT 'active',
    CONSTRAINT ck_assets_status CHECK (status IN ('active', 'under_maintenance', 'retired')),
    CONSTRAINT fk_assets_department FOREIGN KEY (department_id)
        REFERENCES departments(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT fk_assets_category FOREIGN KEY (category_id)
        REFERENCES asset_categories(id) ON DELETE RESTRICT ON UPDATE RESTRICT
);
CREATE TABLE maintenance_tickets (
    id uuid DEFAULT gen_random_uuid() CONSTRAINT pk_maintenance_tickets PRIMARY KEY,
    asset_id uuid CONSTRAINT nn_tickets_asset NOT NULL,
    reported_by_id uuid CONSTRAINT nn_tickets_reporter NOT NULL,
    assigned_to_id uuid,
    department_id uuid CONSTRAINT nn_tickets_department NOT NULL,
    status text NOT NULL DEFAULT 'open',
    CONSTRAINT ck_tickets_status CHECK (status IN ('open', 'assigned', 'in_progress', 'awaiting_verification', 'closed', 'rejected')),
    CONSTRAINT fk_tickets_asset FOREIGN KEY (asset_id)
        REFERENCES assets(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT fk_tickets_reporter FOREIGN KEY (reported_by_id)
        REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT fk_tickets_assignee FOREIGN KEY (assigned_to_id)
        REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    -- This is department-at-report, independent of the asset's current owner.
    CONSTRAINT fk_tickets_department FOREIGN KEY (department_id)
        REFERENCES departments(id) ON DELETE RESTRICT ON UPDATE RESTRICT
);
-- PostgreSQL does not automatically index the referencing columns. These
-- simple indexes support future joins and parent-reference checks; this is
-- not a performance benchmark or a complete application indexing plan.
CREATE INDEX ix_users_department ON users(department_id);
CREATE INDEX ix_assets_department ON assets(department_id);
CREATE INDEX ix_assets_category ON assets(category_id);
CREATE INDEX ix_tickets_asset ON maintenance_tickets(asset_id);
CREATE INDEX ix_tickets_reporter ON maintenance_tickets(reported_by_id);
CREATE INDEX ix_tickets_assignee ON maintenance_tickets(assigned_to_id);
CREATE INDEX ix_tickets_department ON maintenance_tickets(department_id);

-- Comparison probes only: integer pairs make MATCH behavior easy to inspect.
-- They illustrate a future reference to one work-order/part pair, without
-- installing work orders, inventory movements, or their workflow yet.
CREATE TABLE part_line_key_probe (
    order_no integer,
    part_no integer,
    CONSTRAINT pk_part_line_key_probe PRIMARY KEY (order_no, part_no)
);
CREATE TABLE simple_reference_probe (
    label text PRIMARY KEY,
    order_no integer,
    part_no integer,
    CONSTRAINT fk_simple_reference FOREIGN KEY (order_no, part_no)
        REFERENCES part_line_key_probe(order_no, part_no) MATCH SIMPLE ON DELETE RESTRICT
);
CREATE TABLE full_reference_probe (
    label text PRIMARY KEY,
    order_no integer,
    part_no integer,
    CONSTRAINT fk_full_reference FOREIGN KEY (order_no, part_no)
        REFERENCES part_line_key_probe(order_no, part_no) MATCH FULL ON DELETE RESTRICT
);

-- ON DELETE alternatives are isolated from all project records/history.
CREATE TABLE deletion_parent_probe (id integer PRIMARY KEY);
CREATE TABLE cascade_child_probe (
    id integer PRIMARY KEY,
    parent_id integer NOT NULL,
    CONSTRAINT fk_cascade_child FOREIGN KEY (parent_id)
        REFERENCES deletion_parent_probe(id) ON DELETE CASCADE
);
CREATE TABLE nullable_child_probe (
    id integer PRIMARY KEY,
    parent_id integer,
    CONSTRAINT fk_nullable_child FOREIGN KEY (parent_id)
        REFERENCES deletion_parent_probe(id) ON DELETE SET NULL
);
CREATE TABLE default_child_probe (
    id integer PRIMARY KEY,
    parent_id integer NOT NULL DEFAULT 0,
    CONSTRAINT fk_default_child FOREIGN KEY (parent_id)
        REFERENCES deletion_parent_probe(id) ON DELETE SET DEFAULT
);
CREATE TABLE required_null_child_probe (
    id integer PRIMARY KEY,
    parent_id integer CONSTRAINT nn_required_null_child_parent NOT NULL,
    CONSTRAINT fk_required_null_child FOREIGN KEY (parent_id)
        REFERENCES deletion_parent_probe(id) ON DELETE SET NULL
);
CREATE TABLE no_action_child_probe (
    id integer PRIMARY KEY,
    parent_id integer NOT NULL,
    -- Omission means NO ACTION, NOT DEFERRABLE by default.
    CONSTRAINT fk_no_action_child FOREIGN KEY (parent_id) REFERENCES deletion_parent_probe(id)
);

CREATE FUNCTION expect_rejection(label text, statement text, expected_state text,
                                 expected_constraint text, expected_column text DEFAULT NULL)
RETURNS text LANGUAGE plpgsql AS $$
DECLARE got_state text; got_constraint text; got_column text;
BEGIN
    BEGIN
        EXECUTE statement;
    EXCEPTION WHEN OTHERS THEN
        GET STACKED DIAGNOSTICS got_state = RETURNED_SQLSTATE,
            got_constraint = CONSTRAINT_NAME, got_column = COLUMN_NAME;
        IF got_state IS DISTINCT FROM expected_state
           OR (expected_constraint IS NOT NULL AND got_constraint IS DISTINCT FROM expected_constraint)
           OR (expected_column IS NOT NULL AND got_column IS DISTINCT FROM expected_column) THEN
            RAISE NOTICE 'Unexpected rejection for %: state=%, constraint=%, column=%',
                label, got_state, got_constraint, got_column;
            RAISE;
        END IF;
        RAISE NOTICE 'Expected SQLSTATE %, constraint=%, column=%', got_state,
            coalesce(nullif(got_constraint, ''), '<not reported>'),
            coalesce(nullif(got_column, ''), '<not reported>');
        RETURN 'PASS: ' || label;
    END;
    RAISE EXCEPTION 'Invalid operation was accepted: %', label;
END $$;

\echo === A valid reference graph with required and optional links ===
INSERT INTO departments (id, code, name) VALUES
    ('10000000-0000-4000-8000-000000000001', 'CSE', 'Computer Science'),
    ('10000000-0000-4000-8000-000000000002', 'ECE', 'Electronics'),
    ('10000000-0000-4000-8000-000000000003', 'STAFF', 'Staff Services');
INSERT INTO asset_categories (id, code) VALUES
    ('20000000-0000-4000-8000-000000000001', 'PROJECTOR'),
    ('20000000-0000-4000-8000-000000000002', 'COMPUTER');
INSERT INTO users (id, email, role, department_id) VALUES
    ('30000000-0000-4000-8000-000000000001', 'reporter@example.invalid', 'student', '10000000-0000-4000-8000-000000000001'),
    ('30000000-0000-4000-8000-000000000002', 'technician@example.invalid', 'technician', '10000000-0000-4000-8000-000000000001'),
    ('30000000-0000-4000-8000-000000000003', 'admin@example.invalid', 'super_admin', NULL),
    ('30000000-0000-4000-8000-000000000004', 'staff@example.invalid', 'department_admin', '10000000-0000-4000-8000-000000000003');
INSERT INTO assets (id, asset_code, department_id, category_id) VALUES
    ('40000000-0000-4000-8000-000000000001', 'PRJ-001', '10000000-0000-4000-8000-000000000001', '20000000-0000-4000-8000-000000000001'),
    ('40000000-0000-4000-8000-000000000002', 'PC-001', '10000000-0000-4000-8000-000000000002', '20000000-0000-4000-8000-000000000002');
INSERT INTO maintenance_tickets (id, asset_id, reported_by_id, assigned_to_id, department_id, status) VALUES
    ('50000000-0000-4000-8000-000000000001', '40000000-0000-4000-8000-000000000001', '30000000-0000-4000-8000-000000000001', '30000000-0000-4000-8000-000000000002', '10000000-0000-4000-8000-000000000001', 'closed'),
    ('50000000-0000-4000-8000-000000000002', '40000000-0000-4000-8000-000000000001', '30000000-0000-4000-8000-000000000001', NULL, '10000000-0000-4000-8000-000000000001', 'rejected');
SELECT (SELECT count(*) FROM maintenance_tickets t
        JOIN assets a ON a.id = t.asset_id
        JOIN departments d ON d.id = t.department_id
        JOIN users reporter ON reporter.id = t.reported_by_id) = 2
       AND (SELECT count(*) FROM maintenance_tickets WHERE assigned_to_id IS NULL) = 1
       AND EXISTS (SELECT 1 FROM users WHERE role = 'super_admin' AND department_id IS NULL)
       AS graph_ok \gset
\if :graph_ok
  \echo PASS: Required parents exist; a ticket can be unassigned and a Super Admin can lack a department.
\else
  \echo FAIL: The required/optional reference graph is incorrect.
  \ir ../shared/fail.sql
\endif

\echo === Missing, NULL, and changed references are checked directly by PostgreSQL ===
\pset format unaligned
\pset tuples_only on
SELECT expect_rejection('A non-NULL missing user department fails fk_users_department.',
    $$INSERT INTO users (email, role, department_id) VALUES ('missing@example.invalid', 'super_admin', '10000000-0000-4000-8000-000000000099')$$, '23503', 'fk_users_department');
SELECT expect_rejection('A missing asset department fails fk_assets_department.',
    $$INSERT INTO assets (asset_code, department_id, category_id) VALUES ('BAD-DEPT', '10000000-0000-4000-8000-000000000099', '20000000-0000-4000-8000-000000000001')$$, '23503', 'fk_assets_department');
SELECT expect_rejection('A missing asset category fails fk_assets_category.',
    $$INSERT INTO assets (asset_code, department_id, category_id) VALUES ('BAD-CATEGORY', '10000000-0000-4000-8000-000000000001', '20000000-0000-4000-8000-000000000099')$$, '23503', 'fk_assets_category');
SELECT expect_rejection('A missing ticket asset fails fk_tickets_asset.',
    $$INSERT INTO maintenance_tickets (asset_id, reported_by_id, department_id) VALUES ('40000000-0000-4000-8000-000000000099', '30000000-0000-4000-8000-000000000001', '10000000-0000-4000-8000-000000000001')$$, '23503', 'fk_tickets_asset');
SELECT expect_rejection('A missing reporter fails fk_tickets_reporter.',
    $$INSERT INTO maintenance_tickets (asset_id, reported_by_id, department_id) VALUES ('40000000-0000-4000-8000-000000000001', '30000000-0000-4000-8000-000000000099', '10000000-0000-4000-8000-000000000001')$$, '23503', 'fk_tickets_reporter');
SELECT expect_rejection('An optional assignee must exist when non-NULL.',
    $$INSERT INTO maintenance_tickets (asset_id, reported_by_id, assigned_to_id, department_id, status) VALUES ('40000000-0000-4000-8000-000000000001', '30000000-0000-4000-8000-000000000001', '30000000-0000-4000-8000-000000000099', '10000000-0000-4000-8000-000000000001', 'assigned')$$, '23503', 'fk_tickets_assignee');
SELECT expect_rejection('A missing recorded ticket department fails fk_tickets_department.',
    $$INSERT INTO maintenance_tickets (asset_id, reported_by_id, department_id) VALUES ('40000000-0000-4000-8000-000000000001', '30000000-0000-4000-8000-000000000001', '10000000-0000-4000-8000-000000000099')$$, '23503', 'fk_tickets_department');
SELECT expect_rejection('A required asset department cannot bypass its FK using NULL.',
    $$INSERT INTO assets (asset_code, department_id, category_id) VALUES ('NULL-DEPT', NULL, '20000000-0000-4000-8000-000000000001')$$, '23502', NULL, 'department_id');
SELECT expect_rejection('A required ticket asset cannot bypass its FK using NULL.',
    $$INSERT INTO maintenance_tickets (asset_id, reported_by_id, department_id) VALUES (NULL, '30000000-0000-4000-8000-000000000001', '10000000-0000-4000-8000-000000000001')$$, '23502', NULL, 'asset_id');
SELECT expect_rejection('Changing an asset category to a missing parent is rejected.',
    $$UPDATE assets SET category_id = '20000000-0000-4000-8000-000000000099' WHERE asset_code = 'PRJ-001'$$, '23503', 'fk_assets_category');
SELECT expect_rejection('Changing an assignee to a missing user is rejected.',
    $$UPDATE maintenance_tickets SET assigned_to_id = '30000000-0000-4000-8000-000000000099' WHERE id = '50000000-0000-4000-8000-000000000001'$$, '23503', 'fk_tickets_assignee');
SELECT expect_rejection('Changing a referenced asset UUID is blocked by ON UPDATE RESTRICT.',
    $$UPDATE assets SET id = '40000000-0000-4000-8000-000000000099' WHERE asset_code = 'PRJ-001'$$, '23001', 'fk_tickets_asset');
SELECT expect_rejection('A foreign key cannot target non-unique department names.',
    $$CREATE TABLE invalid_target_probe (department_name varchar(150) REFERENCES departments(name))$$, '42830', NULL);

\echo === Referenced records cannot be hard-deleted ===
-- ECE currently has only an asset reference; STAFF only a user reference.
-- Isolating the edge makes the expected rejection unambiguous.
SELECT expect_rejection('A department used by an asset cannot be deleted.',
    $$DELETE FROM departments WHERE code = 'ECE'$$, '23001', 'fk_assets_department');
SELECT expect_rejection('A department used by a user cannot be deleted.',
    $$DELETE FROM departments WHERE code = 'STAFF'$$, '23001', 'fk_users_department');
SELECT expect_rejection('A category used by an asset cannot be deleted.',
    $$DELETE FROM asset_categories WHERE code = 'PROJECTOR'$$, '23001', 'fk_assets_category');
SELECT expect_rejection('An asset with retained tickets cannot be deleted.',
    $$DELETE FROM assets WHERE asset_code = 'PRJ-001'$$, '23001', 'fk_tickets_asset');
SELECT expect_rejection('A referenced ticket reporter cannot be deleted.',
    $$DELETE FROM users WHERE email = 'reporter@example.invalid'$$, '23001', 'fk_tickets_reporter');
SELECT expect_rejection('A referenced technician remains protected even on a closed ticket.',
    $$DELETE FROM users WHERE email = 'technician@example.invalid'$$, '23001', 'fk_tickets_assignee');
\pset tuples_only off
\pset format aligned

\echo === Asset transfer and retirement preserve recorded department and user identities ===
-- Both retained tickets are terminal. These raw fixture updates illustrate
-- reference behavior; authorization, transition guards, and audit are later.
SELECT bool_and(status IN ('closed', 'rejected')) AS transfer_precondition_ok
FROM maintenance_tickets WHERE asset_id = '40000000-0000-4000-8000-000000000001' \gset
\if :transfer_precondition_ok
  \echo PASS: All retained tickets are terminal before the illustrated asset transfer.
\else
  \echo FAIL: The transfer fixture has a nonterminal ticket.
  \ir ../shared/fail.sql
\endif
UPDATE assets SET department_id = '10000000-0000-4000-8000-000000000002' WHERE asset_code = 'PRJ-001';
UPDATE users SET department_id = '10000000-0000-4000-8000-000000000002'
WHERE email IN ('reporter@example.invalid', 'technician@example.invalid');
SELECT a.asset_code, current_department.code AS current_department,
       history_department.code AS department_at_report, t.status
FROM maintenance_tickets t
JOIN assets a ON a.id = t.asset_id
JOIN departments current_department ON current_department.id = a.department_id
JOIN departments history_department ON history_department.id = t.department_id
ORDER BY t.id;
SELECT count(*) = 2 AND bool_and(a.department_id = '10000000-0000-4000-8000-000000000002'
       AND t.department_id = '10000000-0000-4000-8000-000000000001') AS history_ok
FROM maintenance_tickets t JOIN assets a ON a.id = t.asset_id \gset
\if :history_ok
  \echo PASS: Asset and user transfers leave both tickets attributed to the original department.
\else
  \echo FAIL: Current ownership changed the recorded ticket department.
  \ir ../shared/fail.sql
\endif
\pset format unaligned
\pset tuples_only on
SELECT expect_rejection('A department referenced only by historical tickets still cannot be deleted.',
    $$DELETE FROM departments WHERE code = 'CSE'$$, '23001', 'fk_tickets_department');
\pset tuples_only off
\pset format aligned
UPDATE assets SET status = 'retired' WHERE asset_code = 'PRJ-001';
UPDATE users SET is_active = false WHERE email IN ('reporter@example.invalid', 'technician@example.invalid');
UPDATE asset_categories SET is_archived = true WHERE code = 'PROJECTOR';
UPDATE departments SET is_archived = true WHERE code = 'CSE';
SELECT count(*) = 2 AND bool_and(a.status = 'retired' AND NOT reporter.is_active
       AND category.is_archived AND history_department.is_archived)
       AND EXISTS (SELECT 1 FROM maintenance_tickets t JOIN users technician ON technician.id = t.assigned_to_id
                   WHERE t.status = 'closed' AND NOT technician.is_active) AS retained_history_ok
FROM maintenance_tickets t
JOIN assets a ON a.id = t.asset_id
JOIN users reporter ON reporter.id = t.reported_by_id
JOIN asset_categories category ON category.id = a.category_id
JOIN departments history_department ON history_department.id = t.department_id \gset
\if :retained_history_ok
  \echo PASS: Retirement, deactivation, and archival preserve all historical reference identities.
\else
  \echo FAIL: History was lost while updating lifecycle flags.
  \ir ../shared/fail.sql
\endif

\echo === Composite references match one whole parent key ===
INSERT INTO part_line_key_probe VALUES (1, 10), (2, 20);
INSERT INTO simple_reference_probe VALUES ('valid', 1, 10), ('absent', NULL, NULL), ('partial', 999, NULL);
INSERT INTO full_reference_probe VALUES ('valid', 2, 20), ('absent', NULL, NULL);
TABLE simple_reference_probe;
TABLE full_reference_probe;
SELECT (SELECT count(*) FROM simple_reference_probe) = 3
       AND EXISTS (SELECT 1 FROM simple_reference_probe WHERE order_no = 999 AND part_no IS NULL)
       AND (SELECT count(*) FROM full_reference_probe) = 2 AS composite_nulls_ok \gset
\if :composite_nulls_ok
  \echo PASS: MATCH SIMPLE skips partial NULL pairs; MATCH FULL permits a complete pair or all NULLs.
\else
  \echo FAIL: Composite nullable-reference behavior differed from expectations.
  \ir ../shared/fail.sql
\endif
\pset format unaligned
\pset tuples_only on
SELECT expect_rejection('Existing components from different rows do not form a valid SIMPLE pair.',
    $$INSERT INTO simple_reference_probe VALUES ('mixed', 1, 20)$$, '23503', 'fk_simple_reference');
SELECT expect_rejection('Existing components from different rows do not form a valid FULL pair.',
    $$INSERT INTO full_reference_probe VALUES ('mixed', 1, 20)$$, '23503', 'fk_full_reference');
SELECT expect_rejection('MATCH FULL rejects a present order with a NULL part.',
    $$INSERT INTO full_reference_probe VALUES ('partial-order', 1, NULL)$$, '23503', 'fk_full_reference');
SELECT expect_rejection('MATCH FULL rejects a NULL order with a present part.',
    $$INSERT INTO full_reference_probe VALUES ('partial-part', NULL, 10)$$, '23503', 'fk_full_reference');
SELECT expect_rejection('A referenced composite parent pair cannot be deleted.',
    $$DELETE FROM part_line_key_probe WHERE order_no = 2 AND part_no = 20$$, '23001', 'fk_full_reference');
\pset tuples_only off
\pset format aligned

\echo === Compare deletion actions using disposable probes ===
INSERT INTO deletion_parent_probe VALUES (0), (1), (2), (3), (4), (5);
INSERT INTO cascade_child_probe VALUES (1, 1);
INSERT INTO nullable_child_probe VALUES (1, 2);
INSERT INTO default_child_probe VALUES (1, 3);
INSERT INTO required_null_child_probe VALUES (1, 4);
INSERT INTO no_action_child_probe VALUES (1, 5);
DELETE FROM deletion_parent_probe WHERE id = 1;
SELECT NOT EXISTS (SELECT 1 FROM cascade_child_probe)
       AND NOT EXISTS (SELECT 1 FROM deletion_parent_probe WHERE id = 1) AS cascade_ok \gset
\if :cascade_ok
  \echo PASS: ON DELETE CASCADE deletes the comparison child with its parent.
\else
  \echo FAIL: The CASCADE probe did not delete the expected child.
  \ir ../shared/fail.sql
\endif
DELETE FROM deletion_parent_probe WHERE id = 2;
SELECT count(*) = 1 AND bool_and(parent_id IS NULL) AS set_null_ok FROM nullable_child_probe \gset
\if :set_null_ok
  \echo PASS: ON DELETE SET NULL retains the comparison child and clears its optional link.
\else
  \echo FAIL: The SET NULL probe did not preserve the child with a NULL link.
  \ir ../shared/fail.sql
\endif
DELETE FROM deletion_parent_probe WHERE id = 3;
SELECT count(*) = 1 AND bool_and(parent_id = 0) AS set_default_ok FROM default_child_probe \gset
\if :set_default_ok
  \echo PASS: ON DELETE SET DEFAULT changes the child to its existing fallback parent.
\else
  \echo FAIL: The SET DEFAULT probe did not use the valid fallback parent.
  \ir ../shared/fail.sql
\endif
\pset format unaligned
\pset tuples_only on
SELECT expect_rejection('SET DEFAULT cannot remove the fallback parent and leave a dangling default.',
    $$DELETE FROM deletion_parent_probe WHERE id = 0$$, '23503', 'fk_default_child');
SELECT expect_rejection('SET NULL still fails if the child link is NOT NULL.',
    $$DELETE FROM deletion_parent_probe WHERE id = 4$$, '23502', NULL, 'parent_id');
SELECT expect_rejection('The default nondeferrable NO ACTION rejects a referenced-parent delete.',
    $$DELETE FROM deletion_parent_probe WHERE id = 5$$, '23503', 'fk_no_action_child');
\pset tuples_only off
\pset format aligned
SELECT (SELECT count(*) FROM deletion_parent_probe) = 3
       AND EXISTS (SELECT 1 FROM deletion_parent_probe WHERE id = 0)
       AND EXISTS (SELECT 1 FROM required_null_child_probe WHERE parent_id = 4)
       AND EXISTS (SELECT 1 FROM no_action_child_probe WHERE parent_id = 5) AS failed_delete_atomic_ok \gset
\if :failed_delete_atomic_ok
  \echo PASS: Rejected deletion actions retain their parents and leave comparison children unchanged.
\else
  \echo FAIL: A failed referential action partially changed the comparison fixture.
  \ir ../shared/fail.sql
\endif

\echo === Inspect actual foreign-key policy and unchanged project fixtures ===
\d college_step07.maintenance_tickets
SELECT conname, conrelid::regclass AS child_table, confrelid::regclass AS parent_table,
       confdeltype AS delete_action, confupdtype AS update_action, condeferrable,
       pg_get_constraintdef(oid) AS definition
FROM pg_constraint
WHERE connamespace = 'college_step07'::regnamespace AND contype = 'f'
ORDER BY conname;
SELECT count(*) = 7 AND bool_and(confdeltype = 'r' AND confupdtype = 'r'
       AND NOT condeferrable AND convalidated) AS project_policy_ok
FROM pg_constraint
WHERE connamespace = 'college_step07'::regnamespace AND contype = 'f'
  AND conrelid IN ('users'::regclass, 'assets'::regclass, 'maintenance_tickets'::regclass) \gset
\if :project_policy_ok
  \echo PASS: All seven project foreign keys are validated, nondeferrable, and RESTRICT parent deletion/key updates.
\else
  \echo FAIL: The catalog does not match the chosen project reference policy.
  \ir ../shared/fail.sql
\endif
SELECT count(*) = 5 AND count(DISTINCT confdeltype) = 5 AS deletion_choices_ok
FROM pg_constraint
WHERE connamespace = 'college_step07'::regnamespace
  AND conname IN ('fk_tickets_asset', 'fk_cascade_child', 'fk_nullable_child', 'fk_default_child', 'fk_no_action_child') \gset
\if :deletion_choices_ok
  \echo PASS: Catalog definitions distinguish RESTRICT, CASCADE, SET NULL, SET DEFAULT, and NO ACTION.
\else
  \echo FAIL: The comparison actions were not defined as expected.
  \ir ../shared/fail.sql
\endif
SELECT count(*) = 7 AND bool_and(i.indisvalid) AS reference_indexes_ok
FROM pg_index i JOIN pg_class c ON c.oid = i.indexrelid
WHERE c.relnamespace = 'college_step07'::regnamespace
  AND c.relname IN ('ix_users_department', 'ix_assets_department', 'ix_assets_category',
                   'ix_tickets_asset', 'ix_tickets_reporter', 'ix_tickets_assignee', 'ix_tickets_department') \gset
\if :reference_indexes_ok
  \echo PASS: Seven explicit child-reference indexes accompany the project foreign keys.
\else
  \echo FAIL: The explicit child-reference indexes are missing or invalid.
  \ir ../shared/fail.sql
\endif
SELECT (SELECT count(*) FROM departments) = 3
       AND (SELECT count(*) FROM asset_categories) = 2
       AND (SELECT count(*) FROM users) = 4
       AND (SELECT count(*) FROM assets) = 2
       AND (SELECT count(*) FROM maintenance_tickets) = 2
       AND (SELECT count(*) FROM part_line_key_probe) = 2
       AND (SELECT count(*) FROM simple_reference_probe) = 3
       AND (SELECT count(*) FROM full_reference_probe) = 2
       AND to_regclass('invalid_target_probe') IS NULL AS rejected_rows_absent \gset
\if :rejected_rows_absent
  \echo PASS: Rejected reference writes, parent deletes, and invalid DDL left no extra or missing fixture rows.
\else
  \echo FAIL: An invalid attempt changed the expected fixture or created invalid DDL.
  \ir ../shared/fail.sql
\endif
ROLLBACK;
SELECT to_regnamespace('college_step07') IS NULL AS cleanup_ok \gset
\if :cleanup_ok
  \echo PASS: All Step 7 tables, indexes, constraints, fixtures, and the helper were rolled back.
\else
  \echo FAIL: The Step 7 demonstration left an unexpected schema behind.
  \ir ../shared/fail.sql
\endif
