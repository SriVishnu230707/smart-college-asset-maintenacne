-- A real SQL error gives psql exit 3 under ON_ERROR_STOP.
\set ON_ERROR_STOP on
DO $$ BEGIN RAISE EXCEPTION 'Step 11 assertion failed; see the preceding FAIL message'; END $$;
