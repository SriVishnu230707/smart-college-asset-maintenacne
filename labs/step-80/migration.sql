-- Optional feature migration, applied only in the exact-run study schema.
CREATE TABLE {schema}.booking_revision(version text PRIMARY KEY);
INSERT INTO {schema}.booking_revision VALUES('booking_v1');
CREATE TABLE {schema}.booking_keys(
  id integer GENERATED ALWAYS AS IDENTITY PRIMARY KEY CHECK(id>0 AND id<2147483647),
  asset_id uuid NOT NULL UNIQUE REFERENCES {schema}.assets(id) ON DELETE RESTRICT
);
CREATE TABLE {schema}.preventive_bookings(
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  asset_key integer NOT NULL REFERENCES {schema}.booking_keys(id) ON DELETE RESTRICT,
  department_id uuid NOT NULL REFERENCES {schema}.departments(id) ON DELETE RESTRICT,
  requested_by_id uuid NOT NULL REFERENCES {schema}.users(id) ON DELETE RESTRICT,
  request_key uuid NOT NULL UNIQUE,
  slot tstzrange NOT NULL CHECK(NOT isempty(slot) AND lower(slot) IS NOT NULL AND upper(slot) IS NOT NULL AND lower_inc(slot) AND NOT upper_inc(slot)),
  asset_span int4range GENERATED ALWAYS AS(int4range(asset_key,asset_key,'[]')) STORED,
  reason text NOT NULL CHECK(length(btrim(reason)) BETWEEN 1 AND 500),
  status text NOT NULL DEFAULT 'scheduled' CHECK(status IN ('scheduled','cancelled')),
  version integer NOT NULL DEFAULT 1 CHECK(version>0),
  CONSTRAINT booking_no_overlap EXCLUDE USING gist(asset_span WITH &&,slot WITH &&) WHERE(status='scheduled')
);
