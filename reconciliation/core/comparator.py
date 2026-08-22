from __future__ import annotations

from datetime import timedelta

from reconciliation.core.canonical import FieldDiff, Txn
from reconciliation.core.config import Tolerance


def compare(a: Txn, b: Txn, tol: Tolerance | None = None) -> list[FieldDiff]:
  t = tol or Tolerance()
  diffs = [
    _exact("instrument", a.instrument, b.instrument),
    _exact("side", a.side, b.side),
  ]

  for name, av, bv, check in [
    ("quantity", a.quantity, b.quantity, t.qty_ok),
    ("price", a.price, b.price, t.amt_ok),
    ("gross_amount", a.gross_amount, b.gross_amount, t.amt_ok),
  ]:
    diffs.append(FieldDiff(name, av, bv, abs(av - bv), check(av, bv)))

  td = abs(a.traded_at - b.traded_at)
  diffs.append(FieldDiff("traded_at", a.traded_at, b.traded_at, td, td <= timedelta(minutes=t.time_mins)))
  return diffs


def has_diffs(diffs: list[FieldDiff]) -> bool:
  return any(not d.ok for d in diffs)


def _exact(field: str, av, bv) -> FieldDiff:
  return FieldDiff(field, av, bv, None if av == bv else f"{av} vs {bv}", av == bv)


compare_transactions = compare
has_significant_differences = has_diffs
