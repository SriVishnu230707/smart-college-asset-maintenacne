\set ON_ERROR_STOP on
\pset pager off
\echo === Step 5: exact money and event timestamps ===
\conninfo
SELECT current_database() = 'college_learning'
       AND current_user = 'college_learner' AS identity_ok \gset
\if :identity_ok
\else
  \echo FAIL: Use the learning database and role.
  \quit 1
\endif
SELECT to_regnamespace('college_step05') IS NULL AS namespace_free \gset
\if :namespace_free
\else
  \echo FAIL: college_step05 already exists; inspect it before rerunning.
  \quit 1
\endif

BEGIN;
CREATE SCHEMA college_step05;
SET LOCAL search_path TO college_step05, public;
SET LOCAL timezone TO 'UTC';
SET LOCAL datestyle TO 'ISO, YMD';

\echo === Exact numeric arithmetic and coercion ===
SELECT 0.10::numeric + 0.20::numeric AS exact_sum,
       0.10::double precision + 0.20::double precision AS binary_sum;
SELECT 0.10::numeric + 0.20::numeric = 0.30::numeric
       AND 0.10::double precision + 0.20::double precision <> 0.30::double precision
       AS exact_numeric_ok \gset
\if :exact_numeric_ok
  \echo PASS: Numeric decimal arithmetic preserves the exact monetary sum; binary float differs.
\else
  \echo FAIL: The numeric/float comparison differed from expectations.
  \quit 1
\endif
SELECT 1.005::numeric(12,2) AS silently_rounded_value;
SELECT 1.005::numeric(12,2) = 1.01 AS coercion_rounds \gset
\if :coercion_rounds
  \echo PASS: NUMERIC(12,2) rounds excess scale, so strict input validation must precede coercion.
\else
  \echo FAIL: Numeric coercion differed from expectations.
  \quit 1
\endif

-- A lab input guard accepts unconstrained numeric, so the original scale is
-- still available. It is called before assignment to NUMERIC(12,2).
-- This is not a trigger protecting arbitrary direct inserts into the probes.
CREATE FUNCTION require_money(raw numeric) RETURNS numeric
LANGUAGE plpgsql AS $$
BEGIN
    IF raw IS NULL OR raw::text IN ('NaN', 'Infinity', '-Infinity') THEN
        RAISE EXCEPTION 'Money must be a finite non-null value' USING ERRCODE = '22023';
    END IF;
    IF scale(raw) > 2 THEN
        RAISE EXCEPTION 'Money input has more than two fractional places' USING ERRCODE = '22023';
    END IF;
    IF raw < 0 OR raw > 9999999999.99 THEN
        RAISE EXCEPTION 'Money is outside the chosen nonnegative NUMERIC(12,2) range' USING ERRCODE = '22023';
    END IF;
    RETURN raw;
END $$;

DO $$
DECLARE invalid numeric;
BEGIN
    FOREACH invalid IN ARRAY ARRAY[1.005::numeric, 1.230::numeric, 0.001::numeric] LOOP
        BEGIN
            PERFORM require_money(invalid);
            RAISE EXCEPTION 'Excess-scale money was incorrectly accepted';
        EXCEPTION WHEN invalid_parameter_value THEN
            RAISE NOTICE 'Expected SQLSTATE 22023 for excess-scale input %.', invalid;
        END;
    END LOOP;
END $$;
\echo PASS: Raw validation rejects excess scale, including trailing third-place zeros, before rounding.
DO $$
DECLARE invalid numeric;
BEGIN
    FOREACH invalid IN ARRAY ARRAY[-0.01::numeric, 'NaN'::numeric, 'Infinity'::numeric,
                                   '-Infinity'::numeric, NULL::numeric,
                                   10000000000.00::numeric, 2 * 9999999999.99::numeric] LOOP
        BEGIN
            PERFORM require_money(invalid);
            RAISE EXCEPTION 'Invalid monetary input or an oversized repair total was accepted';
        EXCEPTION WHEN invalid_parameter_value THEN
            RAISE NOTICE 'Expected SQLSTATE 22023 for invalid or out-of-range money %.', invalid;
        END;
    END LOOP;
END $$;
\echo PASS: Raw validation rejects nonfinite, negative, null, and oversized monetary values and repair totals.
SELECT require_money(9999999999.99)::numeric(12,2) = 9999999999.99
       AND require_money(0.00)::numeric(12,2) = 0.00 AS money_boundaries_ok \gset
\if :money_boundaries_ok
  \echo PASS: Zero and the selected maximum 9999999999.99 are represented exactly.
\else
  \echo FAIL: Monetary boundary values were not preserved.
  \quit 1
\endif
DO $$
BEGIN
    BEGIN
        PERFORM 10000000000.00::numeric(12,2);
        RAISE EXCEPTION 'NUMERIC(12,2) incorrectly accepted eleven integer digits';
    EXCEPTION WHEN numeric_value_out_of_range THEN
        RAISE NOTICE 'Expected SQLSTATE 22003 for NUMERIC(12,2) storage overflow.';
    END;
END $$;
\echo PASS: The numeric storage type also rejects values exceeding its integer capacity.

-- Reduced study tables, not the complete application work-order schema.
CREATE TABLE part_catalog (
    part_code text PRIMARY KEY,
    standard_unit_cost numeric(12,2) NOT NULL
);
CREATE TABLE repair_costs (
    repair_ref text PRIMARY KEY,
    labor_cost numeric(12,2) NOT NULL,
    completed_at timestamptz NOT NULL
);
CREATE TABLE repair_part_lines (
    repair_ref text REFERENCES repair_costs(repair_ref),
    part_code text REFERENCES part_catalog(part_code),
    quantity_used integer NOT NULL,
    unit_cost_at_use numeric(12,2) NOT NULL,
    PRIMARY KEY (repair_ref, part_code)
);
CREATE TABLE cost_events (
    event_ref text PRIMARY KEY,
    total_cost numeric(12,2) NOT NULL,
    completed_at timestamptz NOT NULL
);

\echo === A repair cost calculated from frozen part prices ===
INSERT INTO part_catalog VALUES
    ('LAMP', require_money(250.10)), ('FUSE', require_money(0.10));
INSERT INTO repair_costs VALUES
    ('REPAIR-EXACT', require_money(100.00), timestamptz '2026-10-21 18:30:00+00');
INSERT INTO repair_part_lines
SELECT 'REPAIR-EXACT', part_code,
       CASE WHEN part_code = 'LAMP' THEN 2 ELSE 3 END,
       standard_unit_cost
FROM part_catalog;
SELECT r.repair_ref, r.labor_cost,
       sum(p.quantity_used * p.unit_cost_at_use) AS parts_cost,
       r.labor_cost + sum(p.quantity_used * p.unit_cost_at_use) AS total_cost
FROM repair_costs AS r JOIN repair_part_lines AS p USING (repair_ref)
GROUP BY r.repair_ref, r.labor_cost;
SELECT r.labor_cost + sum(p.quantity_used * p.unit_cost_at_use) = 600.50 AS repair_total_ok
FROM repair_costs AS r JOIN repair_part_lines AS p USING (repair_ref)
GROUP BY r.repair_ref, r.labor_cost \gset
\if :repair_total_ok
  \echo PASS: Labor 100.00 plus two parts at 250.10 and three at 0.10 is exactly 600.50 INR.
\else
  \echo FAIL: The exact repair-cost fixture is incorrect.
  \quit 1
\endif
UPDATE part_catalog SET standard_unit_cost = require_money(300.00) WHERE part_code = 'LAMP';
SELECT r.labor_cost + sum(p.quantity_used * p.unit_cost_at_use) = 600.50 AS frozen_price_ok
FROM repair_costs AS r JOIN repair_part_lines AS p USING (repair_ref)
GROUP BY r.repair_ref, r.labor_cost \gset
\if :frozen_price_ok
  \echo PASS: Changing a current catalog price does not change the recorded repair cost.
\else
  \echo FAIL: Historical cost was calculated from mutable catalog prices.
  \quit 1
\endif
SELECT sum(value) AS unrestricted_report_total
FROM (VALUES (9999999999.99::numeric(12,2)), (9999999999.99::numeric(12,2))) AS amounts(value);
SELECT sum(value) = 19999999999.98 AS aggregate_ok
FROM (VALUES (9999999999.99::numeric(12,2)), (9999999999.99::numeric(12,2))) AS amounts(value)
\gset
\if :aggregate_ok
  \echo PASS: Report aggregates may exceed the per-repair cap without being cast back to NUMERIC(12,2).
\else
  \echo FAIL: The unrestricted report aggregate lost precision.
  \quit 1
\endif

INSERT INTO cost_events VALUES
    ('BEFORE', require_money(0.10), timestamptz '2026-10-21 18:29:59+00'),
    ('LAST-SECOND', require_money(0.20), timestamptz '2026-10-22 18:29:59+00'),
    ('NEXT-DAY', require_money(0.30), timestamptz '2026-10-22 18:30:00+00');
INSERT INTO cost_events
SELECT r.repair_ref, require_money(r.labor_cost + sum(p.quantity_used * p.unit_cost_at_use)),
       r.completed_at
FROM repair_costs AS r JOIN repair_part_lines AS p USING (repair_ref)
GROUP BY r.repair_ref, r.labor_cost, r.completed_at;

\echo === One instant displayed in UTC ===
SELECT completed_at, extract(epoch FROM completed_at) AS epoch
FROM cost_events WHERE event_ref = 'REPAIR-EXACT';
SELECT extract(epoch FROM completed_at) AS original_epoch
FROM cost_events WHERE event_ref = 'REPAIR-EXACT' \gset
SELECT extract(epoch FROM '2026-10-22 00:00:00'::timestamptz) AS naive_utc_epoch \gset
SELECT (completed_at AT TIME ZONE 'UTC') = timestamp '2026-10-21 18:30:00'
       AND (completed_at AT TIME ZONE 'Asia/Kolkata') = timestamp '2026-10-22 00:00:00'
       AS display_ok
FROM cost_events WHERE event_ref = 'REPAIR-EXACT' \gset
\if :display_ok
  \echo PASS: One instant displays as 18:30 UTC and midnight on the following date in Asia/Kolkata.
\else
  \echo FAIL: Explicit timezone displays were incorrect.
  \quit 1
\endif
SELECT timestamptz '2026-10-22 00:00:00+05:30' = timestamptz '2026-10-21 18:30:00+00'
       AS same_instant_ok \gset
\if :same_instant_ok
  \echo PASS: Offset-aware input strings with different clock readings can identify the same instant.
\else
  \echo FAIL: Equivalent offset-aware timestamps were not equal.
  \quit 1
\endif

\echo === Reporting days around midnight with the session in UTC ===
SELECT (completed_at AT TIME ZONE 'Asia/Kolkata')::date AS reporting_day,
       count(*) AS event_count, sum(total_cost) AS total_cost
FROM cost_events GROUP BY reporting_day ORDER BY reporting_day;
SELECT ((completed_at AT TIME ZONE 'UTC')::date = date '2026-10-21')
       AND ((completed_at AT TIME ZONE 'Asia/Kolkata')::date = date '2026-10-22')
       AS calendar_difference_ok
FROM cost_events WHERE event_ref = 'REPAIR-EXACT' \gset
\if :calendar_difference_ok
  \echo PASS: UTC and the reporting timezone assign different calendar dates without changing the instant.
\else
  \echo FAIL: The midnight calendar-date example is incorrect.
  \quit 1
\endif
SELECT json_agg(d ORDER BY reporting_day)::text AS original_daily_totals
FROM (
    SELECT (completed_at AT TIME ZONE 'Asia/Kolkata')::date AS reporting_day,
           count(*) AS event_count, sum(total_cost) AS total_cost
    FROM cost_events GROUP BY reporting_day
) AS d \gset

SET LOCAL timezone TO 'Asia/Kolkata';
\echo === The same stored instant displayed in Asia/Kolkata ===
SELECT completed_at, extract(epoch FROM completed_at) AS epoch
FROM cost_events WHERE event_ref = 'REPAIR-EXACT';
SELECT extract(epoch FROM completed_at) = :'original_epoch'::numeric AS epoch_unchanged
FROM cost_events WHERE event_ref = 'REPAIR-EXACT' \gset
\if :epoch_unchanged
  \echo PASS: Changing the session timezone changes display, not the stored instant.
\else
  \echo FAIL: The observed instant changed.
  \quit 1
\endif
SELECT :'naive_utc_epoch'::numeric
       - extract(epoch FROM '2026-10-22 00:00:00'::timestamptz) = 19800
       AS missing_offset_ambiguous \gset
\if :missing_offset_ambiguous
  \echo PASS: Input without an offset depends on the session timezone; event inputs must be aware.
\else
  \echo FAIL: The missing-offset counterexample was not demonstrated.
  \quit 1
\endif
SELECT timestamp '2026-10-22 00:00:00+05:30' = timestamp '2026-10-22 00:00:00'
       AS timestamp_drops_offset \gset
\if :timestamp_drops_offset
  \echo PASS: A timestamp-without-time-zone literal discards its offset rather than storing an instant.
\else
  \echo FAIL: The timestamp-without-time-zone counterexample differed from expectations.
  \quit 1
\endif

WITH actual AS (
    SELECT (completed_at AT TIME ZONE 'Asia/Kolkata')::date AS day,
           count(*) AS n, sum(total_cost) AS total
    FROM cost_events GROUP BY day
), expected(day, n, total) AS (
    VALUES (date '2026-10-21', 1, 0.10::numeric),
           (date '2026-10-22', 2, 600.70::numeric),
           (date '2026-10-23', 1, 0.30::numeric)
)
SELECT count(*) = 3
       AND bool_and(actual.day IS NOT NULL AND expected.day IS NOT NULL
                    AND actual.n = expected.n AND actual.total = expected.total)
       AS grouping_ok
FROM actual FULL JOIN expected USING (day) \gset
\if :grouping_ok
  \echo PASS: Local daily counts and exact totals match the hand-calculated three-day fixture.
\else
  \echo FAIL: Local-day grouping or totals were incorrect.
  \quit 1
\endif
SELECT json_agg(d ORDER BY reporting_day)::text = :'original_daily_totals'
       AS grouping_session_independent
FROM (
    SELECT (completed_at AT TIME ZONE 'Asia/Kolkata')::date AS reporting_day,
           count(*) AS event_count, sum(total_cost) AS total_cost
    FROM cost_events GROUP BY reporting_day
) AS d \gset
\if :grouping_session_independent
  \echo PASS: Explicit Asia/Kolkata reporting groups are identical in UTC and Kolkata sessions.
\else
  \echo FAIL: The report depended on the session timezone.
  \quit 1
\endif
SELECT count(*) = 2 AND sum(total_cost) = 600.70 AS day_window_ok
FROM cost_events
WHERE completed_at >= (timestamp '2026-10-22 00:00:00' AT TIME ZONE 'Asia/Kolkata')
  AND completed_at < (timestamp '2026-10-23 00:00:00' AT TIME ZONE 'Asia/Kolkata')
\gset
\if :day_window_ok
  \echo PASS: A half-open local-day interval includes both October 22 events and excludes neighboring days.
\else
  \echo FAIL: The local-day interval has a boundary error.
  \quit 1
\endif
SELECT pg_typeof(date '2026-10-22')::text = 'date'
       AND date '2026-10-22'::text = '2026-10-22' AS date_only_ok \gset
\if :date_only_ok
  \echo PASS: A calendar-only date is a date value, not an event instant with an assumed midnight.
\else
  \echo FAIL: The date-only observation differed from expectations.
  \quit 1
\endif

-- Send actual SQL results to the Python exercise using decimal/ISO strings.
-- This explicit psql/JSON transport introduces no driver or ORM dependency.
\pset format unaligned
\pset tuples_only on
SELECT 'PYTHON_FIXTURE=' || json_build_object(
    'labor_cost', (SELECT labor_cost::text FROM repair_costs WHERE repair_ref = 'REPAIR-EXACT'),
    'parts', (SELECT json_agg(json_build_object('quantity', quantity_used, 'unit_cost', unit_cost_at_use::text)
                            ORDER BY part_code) FROM repair_part_lines),
    'total_cost', (SELECT total_cost::text FROM cost_events WHERE event_ref = 'REPAIR-EXACT'),
    'events', (SELECT json_agg(json_build_object(
                 'ref', event_ref, 'cost', total_cost::text,
                 'instant', to_char(completed_at AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS.US') || '+00:00')
                 ORDER BY completed_at) FROM cost_events),
    'daily_totals', (SELECT json_agg(json_build_object('day', day::text, 'count', n, 'total', total::text)
                                   ORDER BY day) FROM (
        SELECT (completed_at AT TIME ZONE 'Asia/Kolkata')::date AS day,
               count(*) AS n, sum(total_cost) AS total
        FROM cost_events GROUP BY day
    ) AS daily)
)::text;
\pset tuples_only off
\pset format aligned

ROLLBACK;
SELECT to_regnamespace('college_step05') IS NULL AS cleanup_ok \gset
\if :cleanup_ok
  \echo PASS: All money/time probe tables and the raw-input helper were rolled back.
\else
  \echo FAIL: The Step 5 demonstration left an unexpected schema behind.
  \quit 1
\endif
