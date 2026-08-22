from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from dateutil import parser as date_parser

from reconciliation.core.canonical import TransactionState

SIDE_MAP = {
  "B": "BUY",
  "BUY": "BUY",
  "S": "SELL",
  "SELL": "SELL",
}

STATE_MAP = {
  "SETTLED": TransactionState.SETTLED,
  "CANCELLED": TransactionState.CANCELLED,
  "CANCELED": TransactionState.CANCELLED,
  "PENDING": TransactionState.PENDING,
  "VOID": TransactionState.CANCELLED,
}


def parse_datetime(value: str) -> datetime:
  """Parse dates from multiple formats and return UTC-aware datetime."""
  dt = date_parser.parse(value.strip())
  if dt.tzinfo is None:
    return dt.replace(tzinfo=timezone.utc)
  return dt.astimezone(timezone.utc)


def parse_decimal(value: str | int | float) -> Decimal:
  """Convert numeric strings to Decimal for precise money math."""
  try:
    return Decimal(str(value).strip())
  except (InvalidOperation, ValueError) as exc:
    raise ValueError(f"Invalid decimal value: {value!r}") from exc


def normalize_side(value: str) -> str:
  """Map source-specific side codes to BUY or SELL."""
  normalized = SIDE_MAP.get(value.strip().upper())
  if normalized is None:
    raise ValueError(f"Unknown side value: {value!r}")
  return normalized


def normalize_state(value: str) -> TransactionState:
  """Map source-specific status values to a canonical state."""
  normalized = STATE_MAP.get(value.strip().upper())
  if normalized is None:
    return TransactionState.UNKNOWN
  return normalized
