\ir orm-guard.sql
SELECT to_regnamespace(:'lab_schema') IS NULL AS absent \gset
\if :absent
  \echo INFO: The study schema is already absent.
\else
  BEGIN;
  SELECT nspowner=(SELECT oid FROM pg_roles WHERE rolname=current_user)
         AS owned FROM pg_namespace WHERE nspname=:'lab_schema' \gset
  \if :owned
  \else
    \echo FAIL: Refusing cleanup of a foreign schema.
    \ir fail.sql
  \endif
  SELECT set_config('college.lab_schema',:'lab_schema',true), set_config('college.lab_run_id',:'lab_run_id',true);
  \set VERBOSITY verbose
  DO $$ DECLARE matches boolean; name text; schema_name text := current_setting('college.lab_schema');
  BEGIN
    EXECUTE format('SELECT count(*)=1 AND bool_and(run_id=$1) FROM %I.lab_run',schema_name)
      INTO matches USING current_setting('college.lab_run_id')::uuid;
    IF NOT matches THEN
      RAISE EXCEPTION USING ERRCODE='22023', MESSAGE='REFUSED: '||upper(replace(schema_name,'college_',''))||'_RUN_ID_MISMATCH';
    END IF;
    FOREACH name IN ARRAY ARRAY['maintenance_tickets','assets','users','asset_categories','departments','lab_run'] LOOP
      EXECUTE format('DROP TABLE IF EXISTS %I.%I',schema_name,name);
    END LOOP;
    EXECUTE format('DROP SCHEMA %I',schema_name);
  END $$;
  COMMIT;
  \echo PASS: Guarded cleanup removed only the exact run schema and known tables.
\endif
