from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session, joinedload

from reconciliation.core.canonical import Source, Status
from reconciliation.core.matcher import Orphan, ManualPair, match
from reconciliation.core.parsers import parse_csv
from reconciliation.db.models import MatchRow, Resolution, ResType, Run, SourceFile, TxnRow


@dataclass
class UploadResult:
  ok: bool
  msg: str
  file_id: Optional[int] = None
  imported: int = 0
  updated: int = 0
  unchanged: int = 0
  duplicate: bool = False

  @property
  def success(self) -> bool:
    return self.ok

  @property
  def message(self) -> str:
    return self.msg

  @property
  def is_duplicate(self) -> bool:
    return self.duplicate


def upload(session: Session, fname: str, content: str, src: Source, correction: bool = False) -> UploadResult:
  h = hashlib.sha256(content.encode()).hexdigest()
  dup = session.query(SourceFile).filter_by(content_hash=h).first()
  if dup:
    return UploadResult(False, f"duplicate of '{dup.filename}'", duplicate=True, file_id=dup.id)

  f = SourceFile(filename=fname, source_system=src.value, content_hash=h, is_correction=correction)
  session.add(f)
  session.flush()

  imp = upd = same = 0
  for t in parse_csv(src, content, fname):
    row = session.query(TxnRow).filter_by(source_system=src.value, external_id=t.external_id).first()
    if not row:
      session.add(TxnRow.from_txn(t, f.id))
      imp += 1
    elif _changed(row, t):
      _update(row, t, f.id)
      upd += 1
    else:
      same += 1

  session.commit()
  return UploadResult(True, f"{fname}: {imp} new, {upd} updated, {same} same", f.id, imp, upd, same)


def list_files(session: Session) -> list[SourceFile]:
  return session.query(SourceFile).order_by(SourceFile.uploaded_at.desc()).all()


def start_run(session: Session) -> int:
  run = Run(status="running")
  session.add(run)
  session.flush()

  ledger = _txns(session, Source.LEDGER)
  statement = _txns(session, Source.STATEMENT)
  manual = [ManualPair(r.ledger_eid, r.statement_eid) for r in _resolutions(session, ResType.MATCH) if r.ledger_eid and r.statement_eid]
  orphans = [Orphan(Source(r.source_system), r.external_id) for r in _resolutions(session, ResType.ORPHAN) if r.source_system and r.external_id]

  lookup = {(r.source_system, r.external_id): r.id for r in session.query(TxnRow).all()}
  for m in match(ledger, statement, manual, orphans):
    lid = lookup.get((Source.LEDGER.value, m.ledger.external_id)) if m.ledger else None
    sid = lookup.get((Source.STATEMENT.value, m.statement.external_id)) if m.statement else None
    diffs = json.dumps([{
      "field_name": d.field,
      "ledger_value": str(d.ledger_val),
      "statement_value": str(d.statement_val),
      "difference": str(d.diff) if d.diff is not None else None,
      "within_tolerance": d.ok,
    } for d in m.diffs])

    session.add(MatchRow(
      run_id=run.id, status=m.status.value,
      ledger_id=lid, statement_id=sid,
      match_key=m.key, is_manual=m.manual, diffs_json=diffs,
    ))

  run.status = "completed"
  run.completed_at = datetime.now(timezone.utc)
  session.commit()
  return run.id


def get_run(session: Session, run_id: int) -> Optional[Run]:
  return (
    session.query(Run)
    .options(
      joinedload(Run.matches).joinedload(MatchRow.ledger),
      joinedload(Run.matches).joinedload(MatchRow.statement),
    )
    .filter_by(id=run_id).first()
  )


def list_runs(session: Session) -> list[Run]:
  return session.query(Run).order_by(Run.started_at.desc()).all()


def get_match(session: Session, mid: int) -> Optional[MatchRow]:
  return (
    session.query(MatchRow)
    .options(joinedload(MatchRow.ledger), joinedload(MatchRow.statement))
    .filter_by(id=mid).first()
  )


def count_status(run: Run) -> dict[str, int]:
  c = {s.value: 0 for s in Status}
  for m in run.matches:
    c[m.status] = c.get(m.status, 0) + 1
  return c


def save_match(session: Session, lid: str, sid: str, notes: Optional[str] = None) -> Resolution:
  r = Resolution(res_type=ResType.MATCH.value, ledger_eid=lid, statement_eid=sid, notes=notes)
  session.add(r)
  session.commit()
  return r


def save_orphan(session: Session, src: Source, eid: str, notes: Optional[str] = None) -> Resolution:
  r = Resolution(res_type=ResType.ORPHAN.value, source_system=src.value, external_id=eid, notes=notes)
  session.add(r)
  session.commit()
  return r


def _txns(session: Session, src: Source) -> list:
  return [r.to_txn() for r in session.query(TxnRow).filter_by(source_system=src.value).all()]


def _resolutions(session: Session, rtype: ResType) -> list[Resolution]:
  return session.query(Resolution).filter_by(res_type=rtype.value, active=True).all()


def _changed(row: TxnRow, t) -> bool:
  return any([
    str(row.traded_at) != str(t.traded_at),
    row.instrument != t.instrument, row.side != t.side,
    str(row.quantity) != str(t.quantity), str(row.price) != str(t.price),
    str(row.gross_amount) != str(t.gross_amount), row.state != t.state.value,
  ])


def _update(row: TxnRow, t, fid: int) -> None:
  row.source_file_id = fid
  row.traded_at, row.instrument, row.side = t.traded_at, t.instrument, t.side
  row.quantity, row.price, row.gross_amount = t.quantity, t.price, t.gross_amount
  row.state, row.raw_json = t.state.value, json.dumps(t.raw_row)
  row.updated_at = datetime.now(timezone.utc)


# aliases
upload_file = upload
list_uploaded_files = list_files
start_reconciliation_run = start_run
get_match_result = get_match
count_by_status = count_status
create_manual_match = save_match
accept_orphan = save_orphan
