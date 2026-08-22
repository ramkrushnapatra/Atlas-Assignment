from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Tolerance:
  amt_abs: Decimal = Decimal("0.01")
  amt_pct: Decimal = Decimal("0.001")
  qty_abs: Decimal = Decimal("0.001")
  time_mins: int = 60

  def amt_ok(self, a: Decimal, b: Decimal) -> bool:
    d = abs(a - b)
    return d <= self.amt_abs or d <= abs(a) * self.amt_pct

  def qty_ok(self, a: Decimal, b: Decimal) -> bool:
    return abs(a - b) <= self.qty_abs


ToleranceConfig = Tolerance
