from __future__ import annotations

import csv
import io
from abc import ABC, abstractmethod

from reconciliation.core.canonical import Source, Txn
from reconciliation.core.normalizer import norm_side, norm_state, parse_dec, parse_dt


class Parser(ABC):
  source: Source

  @abstractmethod
  def row(self, r: dict[str, str], fname: str) -> Txn:
    ...

  def csv(self, text: str, fname: str = "") -> list[Txn]:
    return [self.row(r, fname) for r in csv.DictReader(io.StringIO(text.strip()))]


class LedgerParser(Parser):
  source = Source.LEDGER

  def row(self, r: dict[str, str], fname: str) -> Txn:
    return Txn(
      source=self.source,
      external_id=r["trade_id"].strip(),
      traded_at=parse_dt(r["traded_at"]),
      instrument=r["instrument"].strip(),
      side=norm_side(r["side"]),
      quantity=parse_dec(r["quantity"]),
      price=parse_dec(r["price"]),
      gross_amount=parse_dec(r["gross_amount"]),
      state=norm_state(r["state"]),
      source_file=fname,
      raw_row=dict(r),
    )


class StatementParser(Parser):
  source = Source.STATEMENT

  def row(self, r: dict[str, str], fname: str) -> Txn:
    return Txn(
      source=self.source,
      external_id=r["reference"].strip(),
      traded_at=parse_dt(r["executed_at"]),
      instrument=r["symbol"].strip(),
      side=norm_side(r["direction"]),
      quantity=parse_dec(r["qty"]),
      price=parse_dec(r["unit_price"]),
      gross_amount=parse_dec(r["total"]),
      state=norm_state(r["status"]),
      source_file=fname,
      raw_row=dict(r),
    )


PARSERS = {Source.LEDGER: LedgerParser(), Source.STATEMENT: StatementParser()}


def parse_csv(source: Source, text: str, fname: str = "") -> list[Txn]:
  return PARSERS[source].csv(text, fname)


# aliases
BaseParser = Parser
get_parser = lambda s: PARSERS[s]
parse_transactions = lambda source, rows, fname="": [PARSERS[source].row(r, fname) for r in rows]
