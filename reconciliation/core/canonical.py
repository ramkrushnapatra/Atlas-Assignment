from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any


class SourceSystem(str, Enum):
  LEDGER = "ledger"
  STATEMENT = "statement"


class TransactionState(str, Enum):
  SETTLED = "SETTLED"
  CANCELLED = "CANCELLED"
  PENDING = "PENDING"
  UNKNOWN = "UNKNOWN"


class MatchStatus(str, Enum):
  MATCHED_OK = "matched_ok"
  MATCHED_WITH_DIFFERENCES = "matched_with_differences"
  UNMATCHED_LEDGER = "unmatched_ledger"
  UNMATCHED_STATEMENT = "unmatched_statement"
  MANUALLY_MATCHED = "manually_matched"
  ACCEPTED_ORPHAN = "accepted_orphan"


@dataclass(frozen=True)
class CanonicalTransaction:
  """Normalized transaction — same shape regardless of source format."""

  source: SourceSystem
  external_id: str
  traded_at: datetime
  instrument: str
  side: str  # BUY or SELL
  quantity: Decimal
  price: Decimal
  gross_amount: Decimal
  state: TransactionState
  source_file: str = ""
  raw_row: dict[str, Any] = field(default_factory=dict, compare=False)

  @property
  def is_cancelled(self) -> bool:
    return self.state == TransactionState.CANCELLED


@dataclass(frozen=True)
class FieldDiff:
  field_name: str
  ledger_value: Any
  statement_value: Any
  difference: Any = None
  within_tolerance: bool = False


@dataclass
class MatchResult:
  status: MatchStatus
  ledger: CanonicalTransaction | None = None
  statement: CanonicalTransaction | None = None
  field_diffs: list[FieldDiff] = field(default_factory=list)
  match_key: str | None = None
  is_manual: bool = False


@dataclass
class ReconciliationResult:
  matches: list[MatchResult]
  run_at: datetime = field(default_factory=datetime.utcnow)

  @property
  def matched_ok(self) -> list[MatchResult]:
    return [m for m in self.matches if m.status == MatchStatus.MATCHED_OK]

  @property
  def matched_with_differences(self) -> list[MatchResult]:
    return [m for m in self.matches if m.status == MatchStatus.MATCHED_WITH_DIFFERENCES]

  @property
  def unmatched_ledger(self) -> list[MatchResult]:
    return [m for m in self.matches if m.status == MatchStatus.UNMATCHED_LEDGER]

  @property
  def unmatched_statement(self) -> list[MatchResult]:
    return [m for m in self.matches if m.status == MatchStatus.UNMATCHED_STATEMENT]

  @property
  def needs_attention(self) -> list[MatchResult]:
    return [
      m
      for m in self.matches
      if m.status
      in (
        MatchStatus.MATCHED_WITH_DIFFERENCES,
        MatchStatus.UNMATCHED_LEDGER,
        MatchStatus.UNMATCHED_STATEMENT,
      )
    ]
