-- psql \quit does not accept an exit code. Raise a real SQL error under
-- ON_ERROR_STOP instead, so every failed assertion stops psql with exit 3.
\set ON_ERROR_STOP on
DO $$ BEGIN RAISE EXCEPTION 'Step 8 assertion failed; see the preceding FAIL message'; END $$;
