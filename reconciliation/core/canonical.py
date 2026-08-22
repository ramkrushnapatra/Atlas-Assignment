from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any


class Source(str, Enum):
  LEDGER = "ledger"
  STATEMENT = "statement"


class TxnState(str, Enum):
  SETTLED = "SETTLED"
  CANCELLED = "CANCELLED"
  PENDING = "PENDING"
  UNKNOWN = "UNKNOWN"


class Status(str, Enum):
  OK = "matched_ok"
  DIFF = "matched_with_differences"
  UNMATCHED_L = "unmatched_ledger"
  UNMATCHED_S = "unmatched_statement"
  MANUAL = "manually_matched"
  ORPHAN = "accepted_orphan"


@dataclass(frozen=True)
class Txn:
  source: Source
  external_id: str
  traded_at: datetime
  instrument: str
  side: str
  quantity: Decimal
  price: Decimal
  gross_amount: Decimal
  state: TxnState
  source_file: str = ""
  raw_row: dict[str, Any] = field(default_factory=dict, compare=False)

  @property
  def cancelled(self) -> bool:
    return self.state == TxnState.CANCELLED


@dataclass(frozen=True)
class FieldDiff:
  field: str
  ledger_val: Any
  statement_val: Any
  diff: Any = None
  ok: bool = False


@dataclass
class Match:
  status: Status
  ledger: Txn | None = None
  statement: Txn | None = None
  diffs: list[FieldDiff] = field(default_factory=list)
  key: str | None = None
  manual: bool = False


@dataclass
class RunResult:
  matches: list[Match]
  run_at: datetime = field(default_factory=datetime.utcnow)

  def _filter(self, status: Status) -> list[Match]:
    return [m for m in self.matches if m.status == status]

  @property
  def ok(self) -> list[Match]:
    return self._filter(Status.OK)

  @property
  def with_diffs(self) -> list[Match]:
    return self._filter(Status.DIFF)

  @property
  def unmatched_l(self) -> list[Match]:
    return self._filter(Status.UNMATCHED_L)

  @property
  def unmatched_s(self) -> list[Match]:
    return self._filter(Status.UNMATCHED_S)

  @property
  def attention(self) -> list[Match]:
    return [m for m in self.matches if m.status in (Status.DIFF, Status.UNMATCHED_L, Status.UNMATCHED_S)]


# aliases for imports that still use old names
SourceSystem = Source
TransactionState = TxnState
MatchStatus = Status
CanonicalTransaction = Txn
MatchResult = Match
ReconciliationResult = RunResult
