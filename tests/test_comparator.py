from datetime import datetime, timedelta, timezone
from decimal import Decimal

from reconciliation.core.comparator import compare, has_diffs
from reconciliation.core.config import Tolerance
from tests.conftest import make_txn


def test_compare_identical_pair():
  a = make_txn("T-1")
  b = make_txn("T-1")
  assert not has_diffs(compare(a, b))


def test_compare_price_beyond_tolerance():
  a = make_txn("T-1", price="3400", amount="34000")
  b = make_txn("T-1", price="3417", amount="34170")
  diffs = compare(a, b)
  assert has_diffs(diffs)
  price = next(d for d in diffs if d.field == "price")
  assert not price.ok


def test_compare_time_within_60_minutes():
  a = make_txn("T-1", traded_at=datetime(2025, 7, 5, 10, 0, tzinfo=timezone.utc))
  b = make_txn("T-1", traded_at=datetime(2025, 7, 5, 10, 40, tzinfo=timezone.utc))
  td = next(d for d in compare(a, b) if d.field == "traded_at")
  assert td.ok


def test_compare_time_beyond_tolerance():
  tol = Tolerance(time_mins=30)
  a = make_txn("T-1", traded_at=datetime(2025, 7, 5, 10, 0, tzinfo=timezone.utc))
  b = make_txn("T-1", traded_at=datetime(2025, 7, 5, 11, 0, tzinfo=timezone.utc))
  td = next(d for d in compare(a, b, tol) if d.field == "traded_at")
  assert not td.ok
