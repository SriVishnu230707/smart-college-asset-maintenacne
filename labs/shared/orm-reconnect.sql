\ir orm-guard.sql
BEGIN READ ONLY;
SELECT set_config('college.lab_schema',:'lab_schema',true), set_config('college.lab_run_id',:'lab_run_id',true);
DO $$ DECLARE marker record; pair record; actual jsonb; schema_name text := current_setting('college.lab_schema');
BEGIN
  EXECUTE format('SELECT * FROM %I.lab_run',schema_name) INTO STRICT marker;
  IF marker.run_id <> current_setting('college.lab_run_id')::uuid OR marker.writer_backend_pid=pg_backend_pid()
     OR EXISTS (SELECT 1 FROM pg_stat_activity WHERE pid=marker.writer_backend_pid) THEN
    RAISE EXCEPTION 'Wrong run or writer still connected';
  END IF;
  FOR pair IN SELECT * FROM jsonb_each(marker.expected_snapshot) LOOP
    EXECUTE format('SELECT COALESCE(jsonb_agg(to_jsonb(t) ORDER BY to_jsonb(t)::text),''[]''::jsonb) FROM %I.%I AS t',schema_name,pair.key) INTO actual;
    IF actual IS DISTINCT FROM pair.value THEN RAISE EXCEPTION 'Independent rows differ in %',pair.key; END IF;
  END LOOP;
END $$;
\echo PASS: Independent psql verifies the exact run and disposed writer.
\echo PASS: Independent SQL agrees with every recorded committed table value.
COMMIT;
