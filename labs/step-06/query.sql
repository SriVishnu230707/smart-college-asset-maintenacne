\set ON_ERROR_STOP on
\pset pager off
\echo === Step 6: row validity, NULL, defaults, and uniqueness ===
\conninfo
SELECT current_database() = 'college_learning'
       AND current_user = 'college_learner' AS identity_ok \gset
\if :identity_ok
\else
  \echo FAIL: Use the learning database and role.
  \quit 1
\endif
SELECT to_regnamespace('college_step06') IS NULL AS namespace_free \gset
\if :namespace_free
\else
  \echo FAIL: college_step06 already exists; inspect it before rerunning.
  \quit 1
\endif

BEGIN;
CREATE SCHEMA college_step06;
SET LOCAL search_path TO college_step06, public;
-- Required links below are UUID values only in this reduced row-validity lab.
-- Foreign keys and deletion policies belong to Step 7.
CREATE TABLE departments (
    id uuid DEFAULT gen_random_uuid() CONSTRAINT pk_departments PRIMARY KEY,
    code varchar(20) CONSTRAINT nn_departments_code NOT NULL,
    name varchar(150) CONSTRAINT nn_departments_name NOT NULL,
    CONSTRAINT ck_departments_code CHECK (code = upper(btrim(code)) AND code !~ '^[[:space:]]*$'),
    CONSTRAINT ck_departments_name CHECK (name !~ '^[[:space:]]*$'),
    CONSTRAINT uq_departments_code UNIQUE (code)
);
CREATE TABLE categories (
    id uuid DEFAULT gen_random_uuid() CONSTRAINT pk_categories PRIMARY KEY,
    code varchar(30) CONSTRAINT nn_categories_code NOT NULL,
    CONSTRAINT ck_categories_code CHECK (code = upper(btrim(code)) AND code !~ '^[[:space:]]*$'),
    CONSTRAINT uq_categories_code UNIQUE (code)
);
CREATE TABLE users (
    id uuid DEFAULT gen_random_uuid() CONSTRAINT pk_users PRIMARY KEY,
    email text CONSTRAINT nn_users_email NOT NULL,
    role text CONSTRAINT nn_users_role NOT NULL,
    department_id uuid,
    is_active boolean CONSTRAINT nn_users_is_active NOT NULL DEFAULT true,
    CONSTRAINT ck_users_email CHECK (email = lower(btrim(email)) AND email <> '' AND email !~ '[[:space:]]'),
    CONSTRAINT uq_users_email UNIQUE (email),
    CONSTRAINT ck_users_role CHECK (role IN ('student', 'technician', 'department_admin', 'super_admin')),
    CONSTRAINT ck_users_department CHECK (role = 'super_admin' OR department_id IS NOT NULL)
);
CREATE TABLE assets (
    id uuid DEFAULT gen_random_uuid() CONSTRAINT pk_assets PRIMARY KEY,
    asset_code varchar(50) CONSTRAINT nn_assets_asset_code NOT NULL,
    status text CONSTRAINT nn_assets_status NOT NULL DEFAULT 'active',
    CONSTRAINT ck_assets_asset_code CHECK (asset_code = upper(btrim(asset_code)) AND asset_code !~ '^[[:space:]]*$'),
    CONSTRAINT uq_assets_asset_code UNIQUE (asset_code),
    CONSTRAINT ck_assets_status CHECK (status IN ('active', 'under_maintenance', 'retired'))
);
CREATE TABLE spare_parts (
    id uuid DEFAULT gen_random_uuid() CONSTRAINT pk_spare_parts PRIMARY KEY,
    sku varchar(50) CONSTRAINT nn_spare_parts_sku NOT NULL,
    stock_quantity integer CONSTRAINT nn_spare_parts_stock NOT NULL DEFAULT 0,
    reorder_level integer CONSTRAINT nn_spare_parts_reorder NOT NULL DEFAULT 0,
    is_archived boolean CONSTRAINT nn_spare_parts_is_archived NOT NULL DEFAULT false,
    CONSTRAINT ck_spare_parts_sku CHECK (sku = upper(btrim(sku)) AND sku !~ '^[[:space:]]*$'),
    CONSTRAINT uq_spare_parts_sku UNIQUE (sku),
    CONSTRAINT ck_spare_parts_stock CHECK (stock_quantity >= 0),
    CONSTRAINT ck_spare_parts_reorder CHECK (reorder_level >= 0)
);
CREATE TABLE tickets (
    id uuid DEFAULT gen_random_uuid() CONSTRAINT pk_tickets PRIMARY KEY,
    title varchar(200) CONSTRAINT nn_tickets_title NOT NULL,
    description text CONSTRAINT nn_tickets_description NOT NULL,
    status text CONSTRAINT nn_tickets_status NOT NULL DEFAULT 'open',
    priority text CONSTRAINT nn_tickets_priority NOT NULL,
    CONSTRAINT ck_tickets_title CHECK (title !~ '^[[:space:]]*$'),
    CONSTRAINT ck_tickets_description CHECK (description !~ '^[[:space:]]*$'),
    CONSTRAINT ck_tickets_status CHECK (status IN ('open', 'assigned', 'in_progress', 'awaiting_verification', 'closed', 'rejected')),
    CONSTRAINT ck_tickets_priority CHECK (priority IN ('low', 'medium', 'high', 'critical'))
);
CREATE TABLE work_order_parts (
    work_order_id uuid CONSTRAINT nn_work_order_parts_order NOT NULL,
    spare_part_id uuid CONSTRAINT nn_work_order_parts_part NOT NULL,
    quantity_used integer CONSTRAINT nn_work_order_parts_quantity NOT NULL,
    CONSTRAINT pk_work_order_parts PRIMARY KEY (work_order_id, spare_part_id),
    CONSTRAINT ck_work_order_parts_quantity CHECK (quantity_used > 0)
);
-- Deliberately weaker comparison tables: these are not project entities.
CREATE TABLE nullable_stock_probe (
    label text PRIMARY KEY,
    stock_quantity integer DEFAULT 0,
    CONSTRAINT ck_nullable_stock_probe CHECK (stock_quantity >= 0)
);
CREATE TABLE nullable_unique_probe (
    id integer PRIMARY KEY,
    optional_code text CONSTRAINT uq_nullable_unique_probe UNIQUE
);
CREATE TABLE nulls_not_distinct_probe (
    id integer PRIMARY KEY,
    optional_code text CONSTRAINT uq_nulls_not_distinct_probe UNIQUE NULLS NOT DISTINCT
);

-- Verification plumbing only. Each statement is a literal from this lab.
-- The nested exception block rolls back a rejected statement. Unexpected
-- SQLSTATE/constraint/column diagnostics or accepted bad data fail the lab.
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
    RAISE EXCEPTION 'Invalid input was accepted: %', label;
END $$;

\echo === Three-valued logic and a nullable CHECK counterexample ===
\pset null '(NULL)'
SELECT NULL::integer >= 0 AS null_comparison,
       true AND NULL::boolean AS true_and_unknown,
       false AND NULL::boolean AS false_and_unknown,
       true OR NULL::boolean AS true_or_unknown,
       NOT NULL::boolean AS not_unknown;
SELECT (NULL::integer >= 0) IS UNKNOWN
       AND (true AND NULL::boolean) IS UNKNOWN
       AND (false AND NULL::boolean) IS FALSE
       AND (true OR NULL::boolean) IS TRUE
       AND (NOT NULL::boolean) IS UNKNOWN AS logic_ok \gset
\if :logic_ok
  \echo PASS: SQL predicates use TRUE, FALSE, and UNKNOWN with the expected AND/OR/NOT results.
\else
  \echo FAIL: Three-valued logic differed from expectations.
  \quit 1
\endif
INSERT INTO nullable_stock_probe (label) VALUES ('omitted');
INSERT INTO nullable_stock_probe VALUES ('explicit-null', NULL), ('positive', 2);
TABLE nullable_stock_probe;
SELECT (SELECT stock_quantity = 0 FROM nullable_stock_probe WHERE label = 'omitted')
       AND (SELECT stock_quantity IS NULL FROM nullable_stock_probe WHERE label = 'explicit-null')
       AND (SELECT stock_quantity = 2 FROM nullable_stock_probe WHERE label = 'positive') AS nullable_check_ok \gset
\if :nullable_check_ok
  \echo PASS: CHECK accepts UNKNOWN; DEFAULT fills omission but preserves an explicit NULL.
\else
  \echo FAIL: Nullable CHECK/default behavior differed from expectations.
  \quit 1
\endif
SELECT (SELECT count(*) FROM nullable_stock_probe WHERE stock_quantity = NULL) = 0
       AND (SELECT count(*) FROM nullable_stock_probe WHERE stock_quantity IS NULL) = 1
       AS null_filter_ok \gset
\if :null_filter_ok
  \echo PASS: WHERE discards UNKNOWN; IS NULL finds the missing value while = NULL does not.
\else
  \echo FAIL: NULL filtering differed from expectations.
  \quit 1
\endif

\echo === Valid project rows and defaults ===
INSERT INTO departments (code, name) VALUES ('CSE', 'Computer Science');
INSERT INTO categories (code) VALUES ('PROJECTOR');
INSERT INTO users (email, role, department_id)
SELECT 'student@example.invalid', 'student', id FROM departments WHERE code = 'CSE';
INSERT INTO users (email, role, is_active) VALUES ('admin@example.invalid', 'super_admin', false);
INSERT INTO assets (asset_code) VALUES ('PRJ-001');
INSERT INTO assets (asset_code, status) VALUES ('PRJ-002', 'under_maintenance'), ('PRJ-003', 'retired');
INSERT INTO spare_parts (id, sku) VALUES ('00000000-0000-4000-8000-000000000001', 'LAMP-001');
INSERT INTO spare_parts (id, sku, stock_quantity, reorder_level, is_archived)
VALUES ('00000000-0000-4000-8000-000000000002', 'FUSE-001', DEFAULT, DEFAULT, true);
INSERT INTO tickets (title, description, priority) VALUES ('Projector flickers', 'Image flickers during use.', 'high');
SELECT (SELECT status = 'active' FROM assets WHERE asset_code = 'PRJ-001')
       AND (SELECT status = 'open' FROM tickets)
       AND (SELECT stock_quantity = 0 AND reorder_level = 0 AND NOT is_archived FROM spare_parts WHERE sku = 'LAMP-001')
       AND (SELECT stock_quantity = 0 AND reorder_level = 0 AND is_archived FROM spare_parts WHERE sku = 'FUSE-001')
       AND (SELECT is_active FROM users WHERE role = 'student')
       AND (SELECT NOT is_active FROM users WHERE role = 'super_admin') AS defaults_ok \gset
\if :defaults_ok
  \echo PASS: Omission and DEFAULT supply valid initial values; explicit boolean choices are preserved.
\else
  \echo FAIL: Project defaults differed from expectations.
  \quit 1
\endif
SELECT EXISTS (SELECT 1 FROM users WHERE role = 'student' AND department_id IS NOT NULL)
       AND EXISTS (SELECT 1 FROM users WHERE role = 'super_admin' AND department_id IS NULL)
       AS conditional_required_ok \gset
\if :conditional_required_ok
  \echo PASS: A student has a department; a Super Admin may have no department.
\else
  \echo FAIL: Conditional department membership differed from expectations.
  \quit 1
\endif

INSERT INTO work_order_parts VALUES
    ('00000000-0000-4000-8000-000000000010', '00000000-0000-4000-8000-000000000001', 1),
    ('00000000-0000-4000-8000-000000000010', '00000000-0000-4000-8000-000000000002', 2),
    ('00000000-0000-4000-8000-000000000011', '00000000-0000-4000-8000-000000000001', 3);
TABLE work_order_parts;
SELECT count(*) = 3 AND count(DISTINCT work_order_id) = 2
       AND count(DISTINCT spare_part_id) = 2 AS composite_ok FROM work_order_parts \gset
\if :composite_ok
  \echo PASS: Composite uniqueness allows different parts per order and the same part in different orders.
\else
  \echo FAIL: Composite-key fixtures differed from expectations.
  \quit 1
\endif
INSERT INTO nullable_unique_probe VALUES (1, NULL), (2, NULL), (3, 'OPTIONAL-1');
INSERT INTO nulls_not_distinct_probe VALUES (1, NULL);
SELECT (SELECT count(*) FROM nullable_unique_probe WHERE optional_code IS NULL) = 2
       AND (SELECT count(*) FROM nulls_not_distinct_probe WHERE optional_code IS NULL) = 1
       AS nullable_unique_ok \gset
\if :nullable_unique_ok
  \echo PASS: Ordinary UNIQUE permits multiple NULLs; NULLS NOT DISTINCT accepts its first NULL.
\else
  \echo FAIL: Nullable uniqueness fixtures differed from expectations.
  \quit 1
\endif

\echo === Invalid direct SQL: expected diagnostics, then one PASS per attempt ===
-- PostgreSQL 18 exposes named NOT NULL constraints in pg_constraint, but its
-- 23502 errors report COLUMN_NAME and leave CONSTRAINT_NAME empty. Assert the
-- column for those errors; assert the named constraint for 23514 and 23505.
\pset format unaligned
\pset tuples_only on
SELECT expect_rejection('A negative stock balance fails ck_spare_parts_stock.',
    $$INSERT INTO spare_parts (sku, stock_quantity) VALUES ('BAD-STOCK', -1)$$, '23514', 'ck_spare_parts_stock');
SELECT expect_rejection('Explicit NULL stock fails NOT NULL despite DEFAULT 0.',
    $$INSERT INTO spare_parts (sku, stock_quantity) VALUES ('NULL-STOCK', NULL)$$, '23502', NULL, 'stock_quantity');
SELECT expect_rejection('A negative reorder level fails ck_spare_parts_reorder.',
    $$INSERT INTO spare_parts (sku, reorder_level) VALUES ('BAD-REORDER', -1)$$, '23514', 'ck_spare_parts_reorder');
SELECT expect_rejection('Explicit NULL reorder level fails NOT NULL.',
    $$INSERT INTO spare_parts (sku, reorder_level) VALUES ('NULL-REORDER', NULL)$$, '23502', NULL, 'reorder_level');
SELECT expect_rejection('Zero consumption quantity fails ck_work_order_parts_quantity.',
    $$INSERT INTO work_order_parts VALUES (gen_random_uuid(), gen_random_uuid(), 0)$$, '23514', 'ck_work_order_parts_quantity');
SELECT expect_rejection('Negative consumption quantity fails ck_work_order_parts_quantity.',
    $$INSERT INTO work_order_parts VALUES (gen_random_uuid(), gen_random_uuid(), -1)$$, '23514', 'ck_work_order_parts_quantity');
SELECT expect_rejection('NULL consumption quantity fails NOT NULL rather than CHECK.',
    $$INSERT INTO work_order_parts VALUES (gen_random_uuid(), gen_random_uuid(), NULL)$$, '23502', NULL, 'quantity_used');
SELECT expect_rejection('An unknown asset status fails ck_assets_status.',
    $$INSERT INTO assets (asset_code, status) VALUES ('BAD-STATUS', 'broken')$$, '23514', 'ck_assets_status');
SELECT expect_rejection('Explicit NULL asset status fails NOT NULL despite its default.',
    $$INSERT INTO assets (asset_code, status) VALUES ('NULL-STATUS', NULL)$$, '23502', NULL, 'status');
SELECT expect_rejection('The undeclared approved ticket status fails ck_tickets_status.',
    $$INSERT INTO tickets (title, description, priority, status) VALUES ('Issue', 'Details', 'low', 'approved')$$, '23514', 'ck_tickets_status');
SELECT expect_rejection('Explicit NULL ticket status fails NOT NULL.',
    $$INSERT INTO tickets (title, description, priority, status) VALUES ('Issue', 'Details', 'low', NULL)$$, '23502', NULL, 'status');
SELECT expect_rejection('An unknown priority fails ck_tickets_priority.',
    $$INSERT INTO tickets (title, description, priority) VALUES ('Issue', 'Details', 'urgent')$$, '23514', 'ck_tickets_priority');
SELECT expect_rejection('Omitting mandatory priority fails NOT NULL; no default invents it.',
    $$INSERT INTO tickets (title, description) VALUES ('Issue', 'Details')$$, '23502', NULL, 'priority');
SELECT expect_rejection('Whitespace-only report text fails ck_tickets_title.',
    $$INSERT INTO tickets (title, description, priority) VALUES (E' \t\n', 'Details', 'low')$$, '23514', 'ck_tickets_title');
SELECT expect_rejection('Empty report details fail ck_tickets_description.',
    $$INSERT INTO tickets (title, description, priority) VALUES ('Issue', '', 'low')$$, '23514', 'ck_tickets_description');
SELECT expect_rejection('A fresh UUID cannot duplicate a department code.',
    $$INSERT INTO departments (code, name) VALUES ('CSE', 'Duplicate')$$, '23505', 'uq_departments_code');
SELECT expect_rejection('A fresh UUID cannot duplicate a category code.',
    $$INSERT INTO categories (code) VALUES ('PROJECTOR')$$, '23505', 'uq_categories_code');
SELECT expect_rejection('A fresh UUID cannot duplicate an asset code.',
    $$INSERT INTO assets (asset_code) VALUES ('PRJ-001')$$, '23505', 'uq_assets_asset_code');
SELECT expect_rejection('A fresh UUID cannot duplicate a part SKU.',
    $$INSERT INTO spare_parts (sku) VALUES ('LAMP-001')$$, '23505', 'uq_spare_parts_sku');
SELECT expect_rejection('A fresh UUID cannot duplicate a normalized user email.',
    $$INSERT INTO users (email, role) VALUES ('admin@example.invalid', 'super_admin')$$, '23505', 'uq_users_email');
SELECT expect_rejection('A lowercase asset code fails canonical-form CHECK before storage.',
    $$INSERT INTO assets (asset_code) VALUES ('prj-004')$$, '23514', 'ck_assets_asset_code');
SELECT expect_rejection('A padded SKU fails canonical-form CHECK before storage.',
    $$INSERT INTO spare_parts (sku) VALUES (' FUSE-002 ')$$, '23514', 'ck_spare_parts_sku');
SELECT expect_rejection('A blank asset code fails CHECK even though it is not NULL.',
    $$INSERT INTO assets (asset_code) VALUES ('')$$, '23514', 'ck_assets_asset_code');
SELECT expect_rejection('A NULL asset code fails NOT NULL.',
    $$INSERT INTO assets (asset_code) VALUES (NULL)$$, '23502', NULL, 'asset_code');
SELECT expect_rejection('A noncanonical email fails ck_users_email.',
    $$INSERT INTO users (email, role) VALUES (' Admin2@example.invalid ', 'super_admin')$$, '23514', 'ck_users_email');
SELECT expect_rejection('A blank email fails ck_users_email.',
    $$INSERT INTO users (email, role) VALUES ('', 'super_admin')$$, '23514', 'ck_users_email');
SELECT expect_rejection('An unknown user role fails ck_users_role.',
    $$INSERT INTO users (email, role, department_id) SELECT 'bad-role@example.invalid', 'manager', id FROM departments$$, '23514', 'ck_users_role');
SELECT expect_rejection('A NULL role fails NOT NULL instead of slipping through CHECK.',
    $$INSERT INTO users (email, role) VALUES ('null-role@example.invalid', NULL)$$, '23502', NULL, 'role');
SELECT expect_rejection('A student without a department fails the same-row membership CHECK.',
    $$INSERT INTO users (email, role) VALUES ('no-department@example.invalid', 'student')$$, '23514', 'ck_users_department');
SELECT expect_rejection('Explicit NULL activation fails NOT NULL despite DEFAULT true.',
    $$INSERT INTO users (email, role, is_active) VALUES ('null-active@example.invalid', 'super_admin', NULL)$$, '23502', NULL, 'is_active');
SELECT expect_rejection('Omitting mandatory department name fails NOT NULL.',
    $$INSERT INTO departments (code) VALUES ('ECE')$$, '23502', NULL, 'name');
SELECT expect_rejection('A duplicate work-order/part pair fails its composite primary key.',
    $$INSERT INTO work_order_parts VALUES ('00000000-0000-4000-8000-000000000010', '00000000-0000-4000-8000-000000000001', 4)$$, '23505', 'pk_work_order_parts');
SELECT expect_rejection('A NULL composite-key component fails NOT NULL.',
    $$INSERT INTO work_order_parts VALUES (NULL, gen_random_uuid(), 1)$$, '23502', NULL, 'work_order_id');
SELECT expect_rejection('Ordinary nullable UNIQUE still rejects repeated non-NULL values.',
    $$INSERT INTO nullable_unique_probe VALUES (4, 'OPTIONAL-1')$$, '23505', 'uq_nullable_unique_probe');
SELECT expect_rejection('NULLS NOT DISTINCT rejects a second NULL.',
    $$INSERT INTO nulls_not_distinct_probe VALUES (2, NULL)$$, '23505', 'uq_nulls_not_distinct_probe');
SELECT expect_rejection('Even the nullable CHECK rejects a known negative value.',
    $$INSERT INTO nullable_stock_probe VALUES ('negative', -1)$$, '23514', 'ck_nullable_stock_probe');
SELECT expect_rejection('CHECK also rejects an invalid UPDATE of an existing stock row.',
    $$UPDATE spare_parts SET stock_quantity = -1 WHERE sku = 'LAMP-001'$$, '23514', 'ck_spare_parts_stock');
\pset tuples_only off
\pset format aligned

\echo === Inspect named constraints and confirm rejected statements changed nothing ===
\d college_step06.spare_parts
SELECT conrelid::regclass AS table_name, conname, contype, pg_get_constraintdef(oid) AS definition
FROM pg_constraint
WHERE connamespace = 'college_step06'::regnamespace
  AND conname IN ('nn_spare_parts_stock', 'ck_spare_parts_stock', 'uq_spare_parts_sku', 'pk_work_order_parts')
ORDER BY conname;
SELECT count(*) = 4 AND count(DISTINCT contype) = 4 AS named_constraints_ok
FROM pg_constraint
WHERE connamespace = 'college_step06'::regnamespace
  AND conname IN ('nn_spare_parts_stock', 'ck_spare_parts_stock', 'uq_spare_parts_sku', 'pk_work_order_parts') \gset
\if :named_constraints_ok
  \echo PASS: Named NOT NULL, CHECK, UNIQUE, and composite PRIMARY KEY constraints are visible in the catalog.
\else
  \echo FAIL: The expected named constraints were not found.
  \quit 1
\endif
SELECT (SELECT count(*) FROM departments) = 1
       AND (SELECT count(*) FROM categories) = 1
       AND (SELECT count(*) FROM users) = 2
       AND (SELECT count(*) FROM assets) = 3
       AND (SELECT count(*) FROM tickets) = 1
       AND (SELECT count(*) FROM spare_parts) = 2
       AND (SELECT bool_and(stock_quantity = 0) FROM spare_parts)
       AND (SELECT count(*) = 3 AND sum(quantity_used) = 6 FROM work_order_parts)
       AND (SELECT count(*) FROM nullable_stock_probe) = 3
       AND (SELECT count(*) FROM nullable_unique_probe) = 3
       AND (SELECT count(*) FROM nulls_not_distinct_probe) = 1 AS invalid_rows_absent \gset
\if :invalid_rows_absent
  \echo PASS: All rejected inserts and the rejected stock update left the valid fixture unchanged.
\else
  \echo FAIL: An invalid attempt changed the valid fixture.
  \quit 1
\endif
ROLLBACK;
SELECT to_regnamespace('college_step06') IS NULL AS cleanup_ok \gset
\if :cleanup_ok
  \echo PASS: All Step 6 tables, constraints, fixtures, and verification helper were rolled back.
\else
  \echo FAIL: The Step 6 demonstration left an unexpected schema behind.
  \quit 1
\endif
