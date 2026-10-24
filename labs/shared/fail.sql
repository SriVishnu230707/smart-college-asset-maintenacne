-- psql has no numeric exit argument for \quit. A SQL error under
-- ON_ERROR_STOP exits with status 3 and rolls back any open transaction.
\set ON_ERROR_STOP on
DO $$ BEGIN RAISE EXCEPTION 'Lab assertion failed; see the preceding FAIL message'; END $$;
