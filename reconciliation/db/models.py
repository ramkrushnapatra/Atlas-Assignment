from __future__ import annotations

import json
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from reconciliation.core.canonical import Source, Txn, TxnState


class Base(DeclarativeBase):
  pass


class ResType(str, Enum):
  MATCH = "manual_match"
  ORPHAN = "accepted_orphan"


class SourceFile(Base):
  __tablename__ = "source_files"

  id: Mapped[int] = mapped_column(Integer, primary_key=True)
  filename: Mapped[str] = mapped_column(String(255), nullable=False)
  source_system: Mapped[str] = mapped_column(String(20), nullable=False)
  content_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
  uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
  is_correction: Mapped[bool] = mapped_column(Boolean, default=False)

  txns: Mapped[list["TxnRow"]] = relationship(back_populates="file")


class TxnRow(Base):
  __tablename__ = "transactions"
  __table_args__ = (UniqueConstraint("source_system", "external_id", name="uq_txn"),)

  id: Mapped[int] = mapped_column(Integer, primary_key=True)
  source_file_id: Mapped[int] = mapped_column(ForeignKey("source_files.id"), nullable=False)
  source_system: Mapped[str] = mapped_column(String(20), nullable=False)
  external_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
  traded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
  instrument: Mapped[str] = mapped_column(String(50), nullable=False)
  side: Mapped[str] = mapped_column(String(10), nullable=False)
  quantity: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
  price: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
  gross_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False)
  state: Mapped[str] = mapped_column(String(20), nullable=False)
  raw_json: Mapped[str] = mapped_column("raw_row_json", Text, default="{}")
  updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

  file: Mapped["SourceFile"] = relationship(back_populates="txns")

  def to_txn(self) -> Txn:
    return Txn(
      source=Source(self.source_system),
      external_id=self.external_id,
      traded_at=self.traded_at,
      instrument=self.instrument,
      side=self.side,
      quantity=Decimal(str(self.quantity)),
      price=Decimal(str(self.price)),
      gross_amount=Decimal(str(self.gross_amount)),
      state=TxnState(self.state),
      source_file=self.file.filename if self.file else "",
      raw_row=json.loads(self.raw_json),
    )

  @classmethod
  def from_txn(cls, t: Txn, file_id: int) -> "TxnRow":
    return cls(
      source_file_id=file_id,
      source_system=t.source.value,
      external_id=t.external_id,
      traded_at=t.traded_at,
      instrument=t.instrument,
      side=t.side,
      quantity=t.quantity,
      price=t.price,
      gross_amount=t.gross_amount,
      state=t.state.value,
      raw_json=json.dumps(t.raw_row),
    )


class Run(Base):
  __tablename__ = "reconciliation_runs"

  id: Mapped[int] = mapped_column(Integer, primary_key=True)
  started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
  completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
  status: Mapped[str] = mapped_column(String(20), default="running")

  matches: Mapped[list["MatchRow"]] = relationship(back_populates="run")

  @property
  def match_results(self) -> list["MatchRow"]:
    return self.matches


class MatchRow(Base):
  __tablename__ = "match_results"

  id: Mapped[int] = mapped_column(Integer, primary_key=True)
  run_id: Mapped[int] = mapped_column(ForeignKey("reconciliation_runs.id"), nullable=False)
  status: Mapped[str] = mapped_column(String(40), nullable=False)
  ledger_id: Mapped[Optional[int]] = mapped_column("ledger_transaction_id", ForeignKey("transactions.id"))
  statement_id: Mapped[Optional[int]] = mapped_column("statement_transaction_id", ForeignKey("transactions.id"))
  match_key: Mapped[Optional[str]] = mapped_column(String(100))
  is_manual: Mapped[bool] = mapped_column(Boolean, default=False)
  diffs_json: Mapped[str] = mapped_column("field_diffs_json", Text, default="[]")

  run: Mapped["Run"] = relationship(back_populates="matches")
  ledger: Mapped[Optional["TxnRow"]] = relationship(foreign_keys=[ledger_id])
  statement: Mapped[Optional["TxnRow"]] = relationship(foreign_keys=[statement_id])

  @property
  def ledger_transaction(self) -> Optional["TxnRow"]:
    return self.ledger

  @property
  def statement_transaction(self) -> Optional["TxnRow"]:
    return self.statement

  @property
  def field_diffs(self) -> list[dict[str, Any]]:
    return json.loads(self.diffs_json or "[]")


class Resolution(Base):
  __tablename__ = "manual_resolutions"

  id: Mapped[int] = mapped_column(Integer, primary_key=True)
  res_type: Mapped[str] = mapped_column("resolution_type", String(20), nullable=False)
  ledger_eid: Mapped[Optional[str]] = mapped_column("ledger_external_id", String(50))
  statement_eid: Mapped[Optional[str]] = mapped_column("statement_external_id", String(50))
  source_system: Mapped[Optional[str]] = mapped_column(String(20))
  external_id: Mapped[Optional[str]] = mapped_column(String(50))
  notes: Mapped[Optional[str]] = mapped_column(Text)
  created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
  active: Mapped[bool] = mapped_column("is_active", Boolean, default=True)


# aliases
Transaction = TxnRow
ReconciliationRun = Run
MatchResultRecord = MatchRow
ManualResolution = Resolution
ResolutionType = ResType
