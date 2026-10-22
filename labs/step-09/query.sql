\set ON_ERROR_STOP on
\pset pager off
\pset null '(NULL)'
\echo === Step 9: deliberate predicates, search, casts, ordering, and LIMIT ===
\conninfo
SELECT current_database() = 'college_learning' AND current_user = 'college_learner' AS identity_ok \gset
\if :identity_ok
\else
  \echo FAIL: Use the learning database and role.
  \ir fail.sql
\endif
SELECT to_regnamespace('college_step09') IS NULL AS namespace_free \gset
\if :namespace_free
\else
  \echo FAIL: college_step09 already exists; inspect it before rerunning.
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
CREATE SCHEMA college_step09;
SET LOCAL search_path TO college_step09, public;
SET LOCAL timezone TO 'UTC';
-- Reduced read-model fixtures. Department UUIDs are synthetic labels here;
-- complete entity columns/reference graphs remain in the earlier design labs.
CREATE TABLE users (
    id uuid PRIMARY KEY,
    department_id uuid NOT NULL,
    role text NOT NULL CHECK (role = 'technician'),
    is_active boolean NOT NULL DEFAULT true
);
CREATE TABLE assets (
    id uuid PRIMARY KEY,
    asset_code varchar(50) NOT NULL CONSTRAINT uq_assets_code UNIQUE,
    name varchar(150) NOT NULL CHECK (name !~ '^[[:space:]]*$'),
    department_id uuid NOT NULL,
    status text NOT NULL CHECK (status IN ('active', 'under_maintenance', 'retired')),
    CONSTRAINT ck_assets_code CHECK (asset_code = upper(btrim(asset_code)) AND asset_code !~ '^[[:space:]]*$')
);
CREATE TABLE maintenance_tickets (
    id uuid PRIMARY KEY,
    asset_id uuid NOT NULL REFERENCES assets(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    department_id uuid NOT NULL,
    title varchar(200) NOT NULL CHECK (title !~ '^[[:space:]]*$'),
    assigned_to_id uuid REFERENCES users(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    status text NOT NULL CHECK (status IN ('open', 'assigned', 'in_progress', 'awaiting_verification', 'closed', 'rejected')),
    priority text NOT NULL CHECK (priority IN ('low', 'medium', 'high', 'critical')),
    created_at timestamptz NOT NULL
);
-- Nullable/blank text belongs only in this deliberate comparison table.
CREATE TABLE text_filter_probe (label text PRIMARY KEY, value text);
INSERT INTO users (id, department_id, role) VALUES
    ('30000000-0000-4000-8000-000000000001', :'cse', 'technician'),
    ('30000000-0000-4000-8000-000000000002', :'ece', 'technician');
INSERT INTO assets VALUES
    ('40000000-0000-4000-8000-000000000001', 'PRJ-001', 'Lab Projector', :'cse', 'active'),
    ('40000000-0000-4000-8000-000000000002', 'PC-001', 'lab computer', :'cse', 'active'),
    ('40000000-0000-4000-8000-000000000003', 'PC-002', 'LAB Computer', :'cse', 'under_maintenance'),
    ('40000000-0000-4000-8000-000000000004', 'PC-003', 'Library Computer', :'ece', 'retired'),
    ('40000000-0000-4000-8000-000000000005', 'PRJ-002', 'Projector 100%', :'ece', 'active'),
    ('40000000-0000-4000-8000-000000000006', 'PC-004', 'Computer_Stand', :'ece', 'active');
INSERT INTO maintenance_tickets VALUES
    (:'t1', '40000000-0000-4000-8000-000000000001', :'cse', 'Projector flickers', NULL, 'open', 'high', '2026-10-22 09:00:00+00'),
    (:'t2', '40000000-0000-4000-8000-000000000002', :'cse', 'Computer slow', NULL, 'open', 'low', '2026-10-22 09:00:00+00'),
    (:'t3', '40000000-0000-4000-8000-000000000003', :'cse', 'Computer needs repair', '30000000-0000-4000-8000-000000000001', 'assigned', 'high', '2026-10-22 09:00:00+00'),
    (:'t4', '40000000-0000-4000-8000-000000000005', :'ece', 'Projector lamp failed', NULL, 'open', 'critical', '2026-10-22 09:00:00+00'),
    (:'t5', '40000000-0000-4000-8000-000000000004', :'ece', 'Historical rejected report', NULL, 'rejected', 'low', '2026-10-21 08:00:00+00'),
    (:'t6', '40000000-0000-4000-8000-000000000006', :'ece', 'Stand needs adjustment', '30000000-0000-4000-8000-000000000002', 'in_progress', 'medium', '2026-10-22 08:30:00+00');
INSERT INTO text_filter_probe VALUES
    ('null', NULL), ('empty', ''), ('spaces', '   '), ('mixed', '  Lab  '),
    ('lower', 'lab'), ('upper', 'LAB'), ('percent', '100%'),
    ('underscore', 'Lab_01'), ('one-character', 'LabX01'),
    ('numeric-two', '2'), ('numeric-ten', '10'), ('bad-number', 'two');

-- Verification plumbing only: execute literal one-column queries, collect
-- their ordered keys, and compare against independently written predictions.
-- Arrays/counts/subqueries here are test machinery, not aggregation lessons.
CREATE FUNCTION assert_keys(label text, statement text, expected text[])
RETURNS text LANGUAGE plpgsql AS $$
DECLARE actual text[];
BEGIN
    EXECUTE 'SELECT ARRAY(' || statement || ')::text[]' INTO actual;
    IF actual IS DISTINCT FROM expected THEN
        RAISE EXCEPTION '%: expected %, observed %', label, expected, actual;
    END IF;
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
    RAISE EXCEPTION 'Invalid input was accepted: %', label;
END $$;

\echo === Predict the active asset list and the unassigned ticket queue ===
SELECT asset_code, name, status FROM assets
WHERE status = 'active' ORDER BY asset_code COLLATE "C";
SELECT id, title, priority, created_at FROM maintenance_tickets
WHERE department_id = :'cse' AND assigned_to_id IS NULL AND status = 'open'
ORDER BY created_at DESC, id ASC LIMIT 2;
SELECT label, quote_nullable(value) AS quoted_value, char_length(value) AS characters
FROM text_filter_probe ORDER BY label COLLATE "C";

\pset format unaligned
\pset tuples_only on
SELECT assert_keys('The active-asset predicate excludes maintenance and retired assets.',
    $$SELECT asset_code FROM assets WHERE status = 'active' ORDER BY asset_code COLLATE "C"$$,
    ARRAY['PC-001', 'PC-004', 'PRJ-001', 'PRJ-002']);
SELECT assert_keys('Department scope and active status together select only the two CSE active assets.',
    $$SELECT asset_code FROM assets WHERE department_id = '10000000-0000-4000-8000-000000000001' AND status = 'active' ORDER BY asset_code COLLATE "C"$$,
    ARRAY['PC-001', 'PRJ-001']);
SELECT assert_keys('IN selects the declared active or maintenance statuses.',
    $$SELECT asset_code FROM assets WHERE status IN ('active', 'under_maintenance') ORDER BY asset_code COLLATE "C"$$,
    ARRAY['PC-001', 'PC-002', 'PC-004', 'PRJ-001', 'PRJ-002']);
SELECT assert_keys('IS NULL finds all unassigned tickets, including a terminal rejected report.',
    $$SELECT id::text FROM maintenance_tickets WHERE assigned_to_id IS NULL ORDER BY id$$,
    ARRAY[:'t1', :'t2', :'t4', :'t5']);
SELECT assert_keys('The operational unassigned queue additionally requires open status and department scope.',
    $$SELECT id::text FROM maintenance_tickets WHERE department_id = '10000000-0000-4000-8000-000000000001' AND assigned_to_id IS NULL AND status = 'open' ORDER BY created_at DESC, id ASC LIMIT 2$$,
    ARRAY[:'t1', :'t2']);
SELECT assert_keys('Comparing a nullable assignee with = NULL returns no rows.',
    $$SELECT id::text FROM maintenance_tickets WHERE assigned_to_id = NULL ORDER BY id$$, ARRAY[]::text[]);
SELECT assert_true('A NULL equality predicate is UNKNOWN, not TRUE or FALSE.',
    (NULL::uuid = NULL::uuid) IS UNKNOWN AND (NULL::uuid IS NULL));
SELECT assert_keys('Parenthesized OR preserves department scope for high or critical priorities.',
    $$SELECT id::text FROM maintenance_tickets WHERE department_id = '10000000-0000-4000-8000-000000000001' AND (priority = 'high' OR priority = 'critical') ORDER BY id$$,
    ARRAY[:'t1', :'t3']);
SELECT assert_keys('Without parentheses AND binds first and the critical ECE ticket also matches.',
    $$SELECT id::text FROM maintenance_tickets WHERE department_id = '10000000-0000-4000-8000-000000000001' AND priority = 'high' OR priority = 'critical' ORDER BY id$$,
    ARRAY[:'t1', :'t3', :'t4']);

\echo === Case-aware searches and literal wildcard characters ===
SELECT assert_keys('LIKE with C collation distinguishes the Lab, lab, and LAB prefixes.',
    $$SELECT asset_code FROM assets WHERE name COLLATE "C" LIKE 'Lab%' ORDER BY asset_code COLLATE "C"$$,
    ARRAY['PRJ-001']);
SELECT assert_keys('ILIKE with C collation matches all three ASCII lab case variants.',
    $$SELECT asset_code FROM assets WHERE name COLLATE "C" ILIKE 'lab%' ORDER BY asset_code COLLATE "C"$$,
    ARRAY['PC-001', 'PC-002', 'PRJ-001']);
SELECT assert_keys('An escaped percent searches for a literal percent in an asset name.',
    $$SELECT asset_code FROM assets WHERE name LIKE '%!%%' ESCAPE '!' ORDER BY asset_code COLLATE "C"$$,
    ARRAY['PRJ-002']);
SELECT assert_keys('An escaped underscore searches for a literal underscore in an asset name.',
    $$SELECT asset_code FROM assets WHERE name LIKE '%!_%' ESCAPE '!' ORDER BY asset_code COLLATE "C"$$,
    ARRAY['PC-004']);
SELECT assert_keys('An unescaped underscore matches any single character in the probe.',
    $$SELECT label FROM text_filter_probe WHERE value COLLATE "C" LIKE 'Lab_01' ORDER BY label COLLATE "C"$$,
    ARRAY['one-character', 'underscore']);

\echo === Empty strings, whitespace, functions, and explicit casts ===
SELECT assert_keys('An empty string is distinct from NULL and whitespace-only text.',
    $$SELECT label FROM text_filter_probe WHERE value = '' ORDER BY label COLLATE "C"$$,
    ARRAY['empty']);
SELECT assert_keys('btrim makes ordinary surrounding spaces irrelevant to the blank-text comparison.',
    $$SELECT label FROM text_filter_probe WHERE btrim(value) = '' ORDER BY label COLLATE "C"$$,
    ARRAY['empty', 'spaces']);
SELECT assert_keys('NULLIF and btrim deliberately group NULL, empty, and space-only probe values.',
    $$SELECT label FROM text_filter_probe WHERE nullif(btrim(value), '') IS NULL ORDER BY label COLLATE "C"$$,
    ARRAY['empty', 'null', 'spaces']);
SELECT assert_keys('lower and btrim normalize the three chosen lab search strings.',
    $$SELECT label FROM text_filter_probe WHERE lower(btrim(value) COLLATE "C") = 'lab' ORDER BY label COLLATE "C"$$,
    ARRAY['lower', 'mixed', 'upper']);
SELECT assert_true('Text functions preserve NULL rather than silently replacing it with an empty value.',
    lower(NULL::text) IS NULL AND btrim(NULL::text) IS NULL AND char_length('') = 0);
SELECT assert_keys('Numeric-looking text sorts lexically as 10 before 2.',
    $$SELECT label FROM text_filter_probe WHERE label IN ('numeric-two', 'numeric-ten') ORDER BY value COLLATE "C", label COLLATE "C"$$,
    ARRAY['numeric-ten', 'numeric-two']);
-- Only the two fixed, known numeric fixtures are selected here. This is not
-- a general parser for arbitrary imported text or a promise of AND evaluation order.
SELECT assert_keys('Casting the known numeric fixtures to integer sorts 2 before 10.',
    $$SELECT label FROM text_filter_probe WHERE label IN ('numeric-two', 'numeric-ten') ORDER BY value::integer, label COLLATE "C"$$,
    ARRAY['numeric-two', 'numeric-ten']);
SELECT assert_keys('An explicitly typed UUID predicate selects the CSE technician assignment.',
    $$SELECT id::text FROM maintenance_tickets WHERE assigned_to_id = '30000000-0000-4000-8000-000000000001'::uuid ORDER BY id$$,
    ARRAY[:'t3']);
SELECT assert_keys('An explicit UTC date expression selects the five October 22 ticket instants.',
    $$SELECT id::text FROM maintenance_tickets WHERE (created_at AT TIME ZONE 'UTC')::date = DATE '2026-10-22' ORDER BY id$$,
    ARRAY[:'t1', :'t2', :'t3', :'t4', :'t6']);

\echo === Complete ordering, NULL placement, and LIMIT ===
SELECT assert_true('The newest timestamp is shared by four distinct ticket IDs.',
    (SELECT count(*) = 4 FROM maintenance_tickets WHERE created_at = timestamptz '2026-10-22 09:00:00+00'));
SELECT assert_keys('The unique ID tiebreaker fixes which two tickets LIMIT returns at a shared timestamp.',
    $$SELECT id::text FROM maintenance_tickets ORDER BY created_at DESC, id ASC LIMIT 2$$,
    ARRAY[:'t1', :'t2']);
SELECT assert_keys('Reversing the explicit ID tie policy selects different but timestamp-equal first rows.',
    $$SELECT id::text FROM maintenance_tickets ORDER BY created_at DESC, id DESC LIMIT 2$$,
    ARRAY[:'t4', :'t3']);
SELECT assert_keys('Ascending assignee order defaults to NULLS LAST and uses ID to order ties.',
    $$SELECT id::text FROM maintenance_tickets ORDER BY assigned_to_id ASC, id ASC$$,
    ARRAY[:'t3', :'t6', :'t1', :'t2', :'t4', :'t5']);
SELECT assert_keys('Explicit NULLS FIRST moves unassigned tickets ahead while preserving a unique order.',
    $$SELECT id::text FROM maintenance_tickets ORDER BY assigned_to_id ASC NULLS FIRST, id ASC$$,
    ARRAY[:'t1', :'t2', :'t4', :'t5', :'t3', :'t6']);
SELECT assert_keys('Descending assignee order defaults to NULLS FIRST.',
    $$SELECT id::text FROM maintenance_tickets ORDER BY assigned_to_id DESC, id ASC$$,
    ARRAY[:'t1', :'t2', :'t4', :'t5', :'t6', :'t3']);
SELECT assert_keys('LIMIT zero returns no rows.',
    $$SELECT id::text FROM maintenance_tickets ORDER BY created_at DESC, id ASC LIMIT 0$$, ARRAY[]::text[]);
SELECT assert_keys('A NULL LIMIT is unbounded rather than an empty page.',
    $$SELECT id::text FROM maintenance_tickets ORDER BY created_at DESC, id ASC LIMIT NULL$$,
    ARRAY[:'t1', :'t2', :'t3', :'t4', :'t6', :'t5']);

\echo === Invalid casts and LIMIT input produce their exact SQLSTATE ===
SELECT expect_error('A malformed UUID is rejected rather than matching no assignment.',
    $$SELECT 'not-a-uuid'::uuid$$, '22P02');
SELECT expect_error('Nonnumeric text cannot be converted to an integer by a cast.',
    $$SELECT value::integer FROM text_filter_probe WHERE label = 'bad-number'$$, '22P02');
SELECT expect_error('A negative LIMIT is rejected.',
    $$SELECT id FROM maintenance_tickets ORDER BY id LIMIT -1$$, '2201W');
SELECT assert_true('All filter and invalid-input experiments leave the fixture rows unchanged.',
    (SELECT count(*) = 6 FROM assets) AND (SELECT count(*) = 6 FROM maintenance_tickets)
    AND (SELECT count(*) = 2 FROM users) AND (SELECT count(*) = 12 FROM text_filter_probe));
\pset tuples_only off
\pset format aligned
ROLLBACK;
SELECT to_regnamespace('college_step09') IS NULL AS cleanup_ok \gset
\if :cleanup_ok
  \echo PASS: All Step 9 fixtures, tables, and verification helpers were rolled back.
\else
  \echo FAIL: The Step 9 demonstration left its schema behind.
  \ir fail.sql
\endif
