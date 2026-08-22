from __future__ import annotations

import csv
import io
from abc import ABC, abstractmethod
from typing import Iterable

from reconciliation.core.canonical import CanonicalTransaction, SourceSystem
from reconciliation.core.normalizer import (
  normalize_side,
  normalize_state,
  parse_datetime,
  parse_decimal,
)


class BaseParser(ABC):
  """Adapter interface — add a new parser for each incoming file format."""

  source_system: SourceSystem

  @abstractmethod
  def parse_row(self, row: dict[str, str], source_file: str) -> CanonicalTransaction:
    raise NotImplementedError

  def parse_csv(self, csv_text: str, source_file: str = "") -> list[CanonicalTransaction]:
    reader = csv.DictReader(io.StringIO(csv_text.strip()))
    return [self.parse_row(row, source_file) for row in reader]


class LedgerParser(BaseParser):
  """
  Our ledger format:
  trade_id, traded_at, instrument, side, quantity, price, gross_amount, state
  """

  source_system = SourceSystem.LEDGER

  def parse_row(self, row: dict[str, str], source_file: str) -> CanonicalTransaction:
    return CanonicalTransaction(
      source=self.source_system,
      external_id=row["trade_id"].strip(),
      traded_at=parse_datetime(row["traded_at"]),
      instrument=row["instrument"].strip(),
      side=normalize_side(row["side"]),
      quantity=parse_decimal(row["quantity"]),
      price=parse_decimal(row["price"]),
      gross_amount=parse_decimal(row["gross_amount"]),
      state=normalize_state(row["state"]),
      source_file=source_file,
      raw_row=dict(row),
    )


class StatementParser(BaseParser):
  """
  Counterparty statement format:
  reference, executed_at, symbol, direction, qty, unit_price, total, status
  """

  source_system = SourceSystem.STATEMENT

  def parse_row(self, row: dict[str, str], source_file: str) -> CanonicalTransaction:
    return CanonicalTransaction(
      source=self.source_system,
      external_id=row["reference"].strip(),
      traded_at=parse_datetime(row["executed_at"]),
      instrument=row["symbol"].strip(),
      side=normalize_side(row["direction"]),
      quantity=parse_decimal(row["qty"]),
      price=parse_decimal(row["unit_price"]),
      gross_amount=parse_decimal(row["total"]),
      state=normalize_state(row["status"]),
      source_file=source_file,
      raw_row=dict(row),
    )


PARSER_REGISTRY: dict[SourceSystem, BaseParser] = {
  SourceSystem.LEDGER: LedgerParser(),
  SourceSystem.STATEMENT: StatementParser(),
}


def get_parser(source: SourceSystem) -> BaseParser:
  parser = PARSER_REGISTRY.get(source)
  if parser is None:
    raise ValueError(f"No parser registered for source: {source}")
  return parser


def parse_csv(source: SourceSystem, csv_text: str, source_file: str = "") -> list[CanonicalTransaction]:
  """Parse a CSV string for the given source system."""
  return get_parser(source).parse_csv(csv_text, source_file)


def parse_transactions(
  source: SourceSystem,
  rows: Iterable[dict[str, str]],
  source_file: str = "",
) -> list[CanonicalTransaction]:
  """Parse already-loaded CSV rows (useful for tests)."""
  parser = get_parser(source)
  return [parser.parse_row(row, source_file) for row in rows]
