\ir guard.sql
\set ON_ERROR_ROLLBACK off
\echo === Step 8: INSERT, SELECT, UPDATE, DELETE, RETURNING, and transactions ===
\conninfo
SELECT to_regnamespace('college_step08') IS NULL AS namespace_free \gset
\if :namespace_free
\else
  \echo FAIL: college_step08 already exists; inspect it before rerunning.
  \ir fail.sql
\endif

\echo === Commit a small synthetic baseline for the independent observer ===
BEGIN;
CREATE SCHEMA college_step08;
SET LOCAL search_path TO college_step08, public;
-- This metadata identifies the exact lab run authorized for later cleanup.
CREATE TABLE lab_run (
    run_id uuid PRIMARY KEY,
    writer_backend_pid integer NOT NULL
);
INSERT INTO lab_run VALUES (:'lab_run_id', pg_backend_pid());
CREATE TABLE departments (
    id uuid DEFAULT gen_random_uuid() CONSTRAINT pk_departments PRIMARY KEY,
    code varchar(20) NOT NULL CONSTRAINT uq_departments_code UNIQUE,
    name varchar(150) NOT NULL,
    is_archived boolean NOT NULL DEFAULT false,
    CONSTRAINT ck_departments_code CHECK (code = upper(btrim(code)) AND code !~ '^[[:space:]]*$'),
    CONSTRAINT ck_departments_name CHECK (name !~ '^[[:space:]]*$')
);
CREATE TABLE asset_categories (
    id uuid DEFAULT gen_random_uuid() CONSTRAINT pk_asset_categories PRIMARY KEY,
    code varchar(30) NOT NULL CONSTRAINT uq_asset_categories_code UNIQUE,
    name varchar(100) NOT NULL,
    is_archived boolean NOT NULL DEFAULT false,
    CONSTRAINT ck_categories_code CHECK (code = upper(btrim(code)) AND code !~ '^[[:space:]]*$'),
    CONSTRAINT ck_categories_name CHECK (name !~ '^[[:space:]]*$')
);
CREATE TABLE assets (
    id uuid DEFAULT gen_random_uuid() CONSTRAINT pk_assets PRIMARY KEY,
    asset_code varchar(50) NOT NULL CONSTRAINT uq_assets_asset_code UNIQUE,
    name varchar(150) NOT NULL,
    department_id uuid NOT NULL,
    category_id uuid NOT NULL,
    location varchar(200) NOT NULL,
    status text NOT NULL DEFAULT 'active',
    CONSTRAINT ck_assets_code CHECK (asset_code = upper(btrim(asset_code)) AND asset_code !~ '^[[:space:]]*$'),
    CONSTRAINT ck_assets_name CHECK (name !~ '^[[:space:]]*$'),
    CONSTRAINT ck_assets_location CHECK (location !~ '^[[:space:]]*$'),
    CONSTRAINT ck_assets_status CHECK (status IN ('active', 'under_maintenance', 'retired')),
    CONSTRAINT fk_assets_department FOREIGN KEY (department_id)
        REFERENCES departments(id) ON DELETE RESTRICT ON UPDATE RESTRICT,
    CONSTRAINT fk_assets_category FOREIGN KEY (category_id)
        REFERENCES asset_categories(id) ON DELETE RESTRICT ON UPDATE RESTRICT
);
CREATE INDEX ix_assets_department ON assets(department_id);
CREATE INDEX ix_assets_category ON assets(category_id);

INSERT INTO departments (code, name) VALUES ('CSE', 'Computer Science') RETURNING id \gset cse_
INSERT INTO departments (code, name) VALUES ('ECE', 'Electronics') RETURNING id \gset ece_
INSERT INTO asset_categories (code, name) VALUES ('PROJECTOR', 'Projector') RETURNING id \gset projector_
INSERT INTO asset_categories (code, name) VALUES ('COMPUTER', 'Computer') RETURNING id \gset computer_
INSERT INTO assets (asset_code, name, department_id, category_id, location) VALUES
    ('PRJ-001', 'Classroom Projector', :'cse_id', :'projector_id', 'Lecture Hall A'),
    ('PC-001', 'Lab Computer', :'cse_id', :'computer_id', 'Computer Lab 1'),
    ('PC-002', 'Electronics Computer', :'ece_id', :'computer_id', 'Electronics Lab')
RETURNING id, asset_code, location, status;
\set seeded_rows :ROW_COUNT
SELECT :seeded_rows::integer = 3 AND count(*) = 3 AND bool_and(status = 'active')
       AND (SELECT count(*) FROM departments) = 2
       AND (SELECT count(*) FROM asset_categories) = 2 AS seed_ok FROM assets \gset
\if :seed_ok
  \echo PASS: INSERT seeded two departments, two categories, and three assets with UUID/default values.
\else
  \echo FAIL: The inserted baseline did not match the fixture.
  \ir fail.sql
\endif
COMMIT;
\echo INFO: Baseline COMMIT completed; later connections will verify persistence.

\echo === Read and change rows inside a transaction that will be rolled back ===
BEGIN;
SET LOCAL search_path TO college_step08, public;
SELECT id FROM assets WHERE asset_code = 'PRJ-001' \gset original_projector_
SELECT asset_code, name, location, status FROM assets ORDER BY asset_code;
\set selected_rows :ROW_COUNT
SELECT :selected_rows::integer = 3 AS read_ok \gset
\if :read_ok
  \echo PASS: SELECT reads the three committed asset rows with an explicit projection and order.
\else
  \echo FAIL: The baseline read returned an unexpected row count.
  \ir fail.sql
\endif
INSERT INTO departments (code, name) VALUES ('MECH', 'Mechanical Study Fixture')
RETURNING id, code \gset temporary_department_
INSERT INTO assets (asset_code, name, department_id, category_id, location)
VALUES ('LAB-TEMP', 'Temporary Study Computer', :'temporary_department_id', :'computer_id', 'Temporary Room')
RETURNING id, asset_code, status \gset temporary_asset_
\set inserted_rows :ROW_COUNT
\echo INSERT RETURNING: id=:temporary_asset_id asset_code=:temporary_asset_asset_code status=:temporary_asset_status
SELECT :inserted_rows::integer = 1 AND :'temporary_asset_status' = 'active'
       AND EXISTS (SELECT 1 FROM assets WHERE id = :'temporary_asset_id') AS insert_returning_ok \gset
\if :insert_returning_ok
  \echo PASS: INSERT RETURNING supplies the generated UUID/default and the writer can read its uncommitted row.
\else
  \echo FAIL: INSERT RETURNING did not describe the inserted row.
  \ir fail.sql
\endif

UPDATE assets SET location = 'Room 204', status = 'under_maintenance'
WHERE asset_code = 'PRJ-001'
RETURNING id, old.location AS old_location, new.location AS new_location,
          old.status AS old_status, new.status AS new_status \gset updated_
\set updated_rows :ROW_COUNT
\echo UPDATE RETURNING: location=:updated_old_location -> :updated_new_location status=:updated_old_status -> :updated_new_status
SELECT :updated_rows::integer = 1 AND :'updated_id'::uuid = :'original_projector_id'::uuid
       AND :'updated_old_location' = 'Lecture Hall A' AND :'updated_new_location' = 'Room 204'
       AND :'updated_old_status' = 'active' AND :'updated_new_status' = 'under_maintenance'
       AS update_returning_ok \gset
\if :update_returning_ok
  \echo PASS: UPDATE targets one asset and RETURNING reports its old/new values without changing its identity.
\else
  \echo FAIL: UPDATE RETURNING differed from the intended one-row change.
  \ir fail.sql
\endif
SELECT location = 'Room 204' AND status = 'under_maintenance' AS own_update_ok
FROM assets WHERE asset_code = 'PRJ-001' \gset
\if :own_update_ok
  \echo PASS: A subsequent SELECT in the writer transaction sees its updated asset values.
\else
  \echo FAIL: The writer did not see its own update.
  \ir fail.sql
\endif

DELETE FROM assets WHERE id = :'temporary_asset_id' RETURNING id, asset_code \gset removed_temporary_
\set removed_temporary_rows :ROW_COUNT
DELETE FROM departments WHERE id = :'temporary_department_id' RETURNING code \gset removed_department_
\set removed_department_rows :ROW_COUNT
SELECT :removed_temporary_rows::integer = 1 AND :removed_department_rows::integer = 1
       AND :'removed_temporary_id'::uuid = :'temporary_asset_id'::uuid
       AND :'removed_department_code' = 'MECH'
       AND NOT EXISTS (SELECT 1 FROM assets WHERE asset_code = 'LAB-TEMP')
       AND NOT EXISTS (SELECT 1 FROM departments WHERE code = 'MECH') AS child_first_delete_ok \gset
\if :child_first_delete_ok
  \echo PASS: DELETE RETURNING identifies removed rows; deleting the temporary child first permits its parent deletion.
\else
  \echo FAIL: The temporary child/parent deletion did not match the intended rows.
  \ir fail.sql
\endif

INSERT INTO assets (asset_code, name, department_id, category_id, location)
VALUES ('ROLLBACK-ONLY', 'Uncommitted Study Asset', :'cse_id', :'computer_id', 'Rollback Room')
RETURNING id, asset_code \gset rollback_asset_
-- PC-002 is a disposable asset with no ticket history, not a production delete policy.
DELETE FROM assets WHERE asset_code = 'PC-002' RETURNING id, asset_code, location \gset deleted_
\set deleted_rows :ROW_COUNT
\echo DELETE RETURNING: id=:deleted_id asset_code=:deleted_asset_code location=:deleted_location
SELECT :deleted_rows::integer = 1 AND :'deleted_asset_code' = 'PC-002'
       AND NOT EXISTS (SELECT 1 FROM assets WHERE asset_code = 'PC-002')
       AND EXISTS (SELECT 1 FROM assets WHERE id = :'rollback_asset_id') AS pending_changes_ok \gset
\if :pending_changes_ok
  \echo PASS: Before ROLLBACK the writer sees the new asset and the deletion of committed PC-002.
\else
  \echo FAIL: The pending insert/delete did not change the writer view as expected.
  \ir fail.sql
\endif

UPDATE assets SET location = 'No Match' WHERE asset_code = 'MISSING-ASSET' RETURNING id;
\set empty_update_rows :ROW_COUNT
\set empty_update_state :SQLSTATE
DELETE FROM assets WHERE asset_code = 'MISSING-ASSET' RETURNING id;
\set empty_delete_rows :ROW_COUNT
\set empty_delete_state :SQLSTATE
SELECT :empty_update_rows::integer = 0 AND :empty_delete_rows::integer = 0
       AND :'empty_update_state' = '00000' AND :'empty_delete_state' = '00000' AS no_match_ok \gset
\if :no_match_ok
  \echo PASS: An UPDATE or DELETE matching no rows succeeds with zero returned/affected rows.
\else
  \echo FAIL: Zero-match DML was mistaken for a successful one-row change or an error.
  \ir fail.sql
\endif
ROLLBACK;

SELECT NOT EXISTS (SELECT 1 FROM college_step08.assets WHERE asset_code = 'ROLLBACK-ONLY')
       AND NOT EXISTS (SELECT 1 FROM college_step08.departments WHERE code = 'MECH') AS insert_rollback_ok \gset
\if :insert_rollback_ok
  \echo PASS: ROLLBACK removes the inserted study asset and leaves no temporary department.
\else
  \echo FAIL: A rolled-back insert persisted.
  \ir fail.sql
\endif
SELECT id = :'original_projector_id'::uuid AND location = 'Lecture Hall A' AND status = 'active' AS update_rollback_ok
FROM college_step08.assets WHERE asset_code = 'PRJ-001' \gset
\if :update_rollback_ok
  \echo PASS: ROLLBACK restores the updated asset values and preserves its original UUID.
\else
  \echo FAIL: A rolled-back update persisted.
  \ir fail.sql
\endif
SELECT id = :'deleted_id'::uuid AND location = 'Electronics Lab' AS delete_rollback_ok
FROM college_step08.assets WHERE asset_code = 'PC-002' \gset
\if :delete_rollback_ok
  \echo PASS: ROLLBACK restores the deleted committed asset with the same UUID.
\else
  \echo FAIL: A rolled-back delete persisted.
  \ir fail.sql
\endif

\echo === A real statement error aborts its transaction until ROLLBACK ===
BEGIN;
SET LOCAL search_path TO college_step08, public;
UPDATE assets SET location = 'Change Before Error' WHERE asset_code = 'PC-001' RETURNING asset_code, location;
\set before_error_rows :ROW_COUNT
-- Only these two deliberately failing statements may continue after errors.
-- The exact SQLSTATE values are saved immediately and asserted after rollback.
\set VERBOSITY sqlstate
\set ON_ERROR_STOP off
INSERT INTO assets (asset_code, name, department_id, category_id, location)
VALUES ('PRJ-001', 'Duplicate Projector', :'cse_id', :'projector_id', 'Duplicate Room');
\set duplicate_state :SQLSTATE
SELECT asset_code FROM assets;
\set blocked_state :SQLSTATE
\set ON_ERROR_STOP on
\set VERBOSITY default
ROLLBACK;
SELECT :'duplicate_state' = '23505' AS duplicate_failed_ok \gset
\if :duplicate_failed_ok
  \echo PASS: EXPECTED ERROR 23505 rejects the duplicate business identifier inside the transaction.
\else
  \echo FAIL: The duplicate insert did not return its expected error code.
  \ir fail.sql
\endif
SELECT :'blocked_state' = '25P02' AS aborted_transaction_ok \gset
\if :aborted_transaction_ok
  \echo PASS: EXPECTED ERROR 25P02 prevents the next SELECT from running in the aborted transaction.
\else
  \echo FAIL: The transaction did not enter the expected aborted state.
  \ir fail.sql
\endif
SELECT :before_error_rows::integer = 1 AND location = 'Computer Lab 1'
       AND (SELECT count(*) FROM college_step08.assets) = 3 AS error_rollback_ok
FROM college_step08.assets WHERE asset_code = 'PC-001' \gset
\if :error_rollback_ok
  \echo PASS: ROLLBACK recovers the connection and undoes the earlier successful update in the failed transaction.
\else
  \echo FAIL: Recovery left a preceding update or extra row committed.
  \ir fail.sql
\endif
\echo INFO: The committed baseline remains for independent verification, then guarded cleanup.
