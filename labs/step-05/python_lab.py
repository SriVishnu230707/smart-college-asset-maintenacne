"""Compare Decimal/aware datetime values with real PostgreSQL results on stdin."""

import json
import platform
import sys
from collections import defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_EVEN, localcontext
from importlib.metadata import version
from zoneinfo import ZoneInfo

CENT = Decimal("0.01")
MONEY_MAX = Decimal("9999999999.99")
REPORTING_ZONE = ZoneInfo("Asia/Kolkata")


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)
    print(f"PASS: {message}")


def require_money(raw: str | Decimal) -> Decimal:
    """Validate original scale and range before normalizing an accepted amount."""
    if not isinstance(raw, (str, Decimal)):
        raise TypeError("Money requires a decimal string or Decimal, never float")
    try:
        amount = Decimal(raw)
    except InvalidOperation as exc:
        raise ValueError("Invalid decimal money") from exc
    if not amount.is_finite():
        raise ValueError("Money must be finite")
    if amount.as_tuple().exponent < -2:
        raise ValueError("Money has more than two fractional places")
    if not Decimal("0") <= amount <= MONEY_MAX:
        raise ValueError("Money exceeds the nonnegative per-repair range")
    with localcontext() as context:
        context.prec = 38
        return amount.quantize(CENT)


def require_aware(instant: datetime) -> datetime:
    if not isinstance(instant, datetime) or instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("Event timestamps must identify an aware instant")
    return instant.astimezone(timezone.utc)


def repair_total(labor: str, parts: list[dict]) -> Decimal:
    with localcontext() as context:
        context.prec = 38
        total = require_money(labor)
        for part in parts:
            quantity = part["quantity"]
            if type(quantity) is not int or quantity <= 0:
                raise ValueError("Part quantity must be a positive integer")
            total += quantity * require_money(part["unit_cost"])
        return require_money(total)


def expect_rejection(operation, error_type: type[Exception]) -> None:
    try:
        operation()
    except error_type:
        return
    raise AssertionError("An invalid input was accepted")


def main() -> None:
    fixture = json.load(sys.stdin)
    print(f"Python {platform.python_version()}; tzdata {version('tzdata')}")
    check(Decimal("0.10") + Decimal("0.20") == Decimal("0.30") and 0.1 + 0.2 != 0.3,
          "Decimal string arithmetic is exact where the binary-float example differs.")
    amount = require_money(fixture["total_cost"])
    check(isinstance(amount, Decimal) and format(amount, ".2f") == "600.50",
          "PostgreSQL's decimal text maps to Decimal without a float conversion.")
    check(repair_total(fixture["labor_cost"], fixture["parts"]) == amount,
          "Python's exact repair calculation equals PostgreSQL's 600.50 INR result.")
    for invalid in ("1.005", "1.230", "0.001", "-0.01", "NaN", "Infinity", "-Infinity",
                    "10000000000.00", "not-money"):
        expect_rejection(lambda value=invalid: require_money(value), ValueError)
    for invalid in (0.1, True, None):
        expect_rejection(lambda value=invalid: require_money(value), TypeError)
    check(True, "Money validation rejects excess scale, invalid range, nonfinite values, and float inputs.")
    check(require_money("0") == Decimal("0.00") and require_money("1.2") == Decimal("1.20")
          and require_money(MONEY_MAX) == MONEY_MAX,
          "Valid zero, short decimal input, and maximum amounts normalize without losing value.")
    expect_rejection(lambda: repair_total("0.00", [{"quantity": 2, "unit_cost": str(MONEY_MAX)}]), ValueError)
    check(sum([MONEY_MAX, MONEY_MAX], Decimal("0.00")) == Decimal("19999999999.98"),
          "An oversized individual repair is rejected while a wider report sum remains exact.")
    check(Decimal("1.005").quantize(CENT, rounding=ROUND_HALF_EVEN) == Decimal("1.00"),
          "Python's half-even rounding illustrates why the contract rejects excess scale instead of rounding it.")

    events = [(row, require_aware(datetime.fromisoformat(row["instant"]))) for row in fixture["events"]]
    instant = next(value for row, value in events if row["ref"] == "REPAIR-EXACT")
    local = instant.astimezone(REPORTING_ZONE)
    print(f"Same instant: UTC={instant.isoformat()}; Asia/Kolkata={local.isoformat()}")
    check(instant == local and local.isoformat() == "2026-10-22T00:00:00+05:30"
          and require_aware(local) == instant,
          "UTC conversion and Asia/Kolkata display preserve the same aware instant.")
    expect_rejection(lambda: require_aware(datetime(2026, 10, 22)), ValueError)
    expect_rejection(lambda: require_aware(date(2026, 10, 22)), ValueError)
    check(True, "Naive datetimes and date-only values cannot silently become event instants.")
    check(instant.date().isoformat() == "2026-10-21" and local.date().isoformat() == "2026-10-22"
          and type(date(2026, 10, 22)) is date,
          "An instant's UTC date can differ from its reporting date; date-only facts stay dates.")

    totals = defaultdict(lambda: Decimal("0.00"))
    counts = defaultdict(int)
    for row, value in events:
        day = value.astimezone(REPORTING_ZONE).date().isoformat()
        totals[day] += require_money(row["cost"])
        counts[day] += 1
    actual = {day: (counts[day], total) for day, total in totals.items()}
    expected = {row["day"]: (row["count"], Decimal(row["total"])) for row in fixture["daily_totals"]}
    check(actual == expected and actual["2026-10-22"] == (2, Decimal("600.70")),
          "Python and PostgreSQL agree on every local reporting day, count, and exact total.")
    start = datetime(2026, 10, 22, tzinfo=REPORTING_ZONE).astimezone(timezone.utc)
    end = datetime(2026, 10, 23, tzinfo=REPORTING_ZONE).astimezone(timezone.utc)
    check({row["ref"] for row, value in events if start <= value < end} == {"REPAIR-EXACT", "LAST-SECOND"},
          "The half-open local-day window includes exactly the same two events in Python.")
    encoded = json.dumps({"total_cost": format(amount, ".2f"),
                          "completed_at": instant.isoformat().replace("+00:00", "Z")})
    decoded = json.loads(encoded)
    check(require_money(decoded["total_cost"]) == amount
          and require_aware(datetime.fromisoformat(decoded["completed_at"].replace("Z", "+00:00"))) == instant,
          "Decimal strings and offset-aware ISO timestamps survive a JSON round trip.")


if __name__ == "__main__":
    main()
