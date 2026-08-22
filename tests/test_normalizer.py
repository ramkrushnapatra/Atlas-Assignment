from decimal import Decimal

import pytest

from reconciliation.core.config import Tolerance
from reconciliation.core.normalizer import norm_side, norm_state, parse_dec, parse_dt


def test_parse_dt_iso_and_space_format():
  a = parse_dt("2025-07-01T09:15:00Z")
  b = parse_dt("2025-07-01 09:15:00")
  assert a.hour == 9 and b.hour == 9


def test_norm_side_maps_b_and_s():
  assert norm_side("B") == "BUY"
  assert norm_side("S") == "SELL"
  assert norm_side("buy") == "BUY"


def test_norm_side_unknown_raises():
  with pytest.raises(ValueError):
    norm_side("X")


def test_norm_state_and_void():
  assert norm_state("SETTLED").value == "SETTLED"
  assert norm_state("VOID").value == "CANCELLED"


def test_parse_dec():
  assert parse_dec("62000.00") == Decimal("62000.00")
  assert parse_dec(10) == Decimal("10")


def test_tolerance_amount():
  t = Tolerance()
  assert t.amt_ok(Decimal("100"), Decimal("100.01"))
  assert not t.amt_ok(Decimal("100"), Decimal("105"))
