from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from dateutil import parser as dp

from reconciliation.core.canonical import TxnState

SIDES = {"B": "BUY", "BUY": "BUY", "S": "SELL", "SELL": "SELL"}
STATES = {
  "SETTLED": TxnState.SETTLED,
  "CANCELLED": TxnState.CANCELLED,
  "CANCELED": TxnState.CANCELLED,
  "PENDING": TxnState.PENDING,
  "VOID": TxnState.CANCELLED,
}


def parse_dt(val: str) -> datetime:
  dt = dp.parse(val.strip())
  return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt.astimezone(timezone.utc)


def parse_dec(val: str | int | float) -> Decimal:
  try:
    return Decimal(str(val).strip())
  except (InvalidOperation, ValueError) as e:
    raise ValueError(f"bad decimal: {val!r}") from e


def norm_side(val: str) -> str:
  s = SIDES.get(val.strip().upper())
  if not s:
    raise ValueError(f"unknown side: {val!r}")
  return s


def norm_state(val: str) -> TxnState:
  return STATES.get(val.strip().upper(), TxnState.UNKNOWN)


# aliases
parse_datetime = parse_dt
parse_decimal = parse_dec
normalize_side = norm_side
normalize_state = norm_state
