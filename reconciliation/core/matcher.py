from __future__ import annotations

from dataclasses import dataclass

from reconciliation.core.canonical import Match, Source, Status, Txn
from reconciliation.core.comparator import compare, has_diffs
from reconciliation.core.config import Tolerance


@dataclass(frozen=True)
class ManualPair:
  ledger_id: str
  statement_id: str


@dataclass(frozen=True)
class Orphan:
  source: Source
  external_id: str


ManualMatch = ManualPair
AcceptedOrphan = Orphan


def match(ledger: list[Txn], statement: list[Txn],
          manual: list[ManualPair] | None = None,
          orphans: list[Orphan] | None = None,
          tol: Tolerance | None = None) -> list[Match]:
  t = tol or Tolerance()
  manual = manual or []
  orphans = orphans or []

  lmap = {x.external_id: x for x in ledger if not x.cancelled}
  smap = {x.external_id: x for x in statement if not x.cancelled}
  acc_l = {o.external_id for o in orphans if o.source == Source.LEDGER}
  acc_s = {o.external_id for o in orphans if o.source == Source.STATEMENT}

  out: list[Match] = []
  used_l, used_s = set(), set()

  for m in manual:
    lt, st = lmap.get(m.ledger_id), smap.get(m.statement_id)
    if not lt or not st:
      continue
    out.append(Match(Status.MANUAL, lt, st, compare(lt, st, t), m.ledger_id, True))
    used_l.add(m.ledger_id)
    used_s.add(m.statement_id)

  for eid in set(lmap) & set(smap) - used_l - used_s:
    lt, st = lmap[eid], smap[eid]
    diffs = compare(lt, st, t)
    st_status = Status.OK if not has_diffs(diffs) else Status.DIFF
    out.append(Match(st_status, lt, st, diffs, eid))
    used_l.add(eid)
    used_s.add(eid)

  for lt, st in _fuzzy([lmap[i] for i in lmap if i not in used_l],
                       [smap[i] for i in smap if i not in used_s], t):
    diffs = compare(lt, st, t)
    st_status = Status.OK if not has_diffs(diffs) else Status.DIFF
    out.append(Match(st_status, lt, st, diffs, f"fuzzy:{lt.external_id}:{st.external_id}"))
    used_l.add(lt.external_id)
    used_s.add(st.external_id)

  for eid, lt in lmap.items():
    if eid in used_l:
      continue
    st = Status.ORPHAN if eid in acc_l else Status.UNMATCHED_L
    out.append(Match(st, ledger=lt, key=eid))

  for eid, st in smap.items():
    if eid in used_s:
      continue
    status = Status.ORPHAN if eid in acc_s else Status.UNMATCHED_S
    out.append(Match(status, statement=st, key=eid))

  return out


def _fuzzy(ledger: list[Txn], statement: list[Txn], t: Tolerance) -> list[tuple[Txn, Txn]]:
  pairs, used = [], set()
  for lt in ledger:
    for st in statement:
      if st.external_id in used:
        continue
      if (lt.instrument == st.instrument and lt.side == st.side
          and t.qty_ok(lt.quantity, st.quantity)
          and abs(lt.traded_at - st.traded_at).total_seconds() <= t.time_mins * 60):
        pairs.append((lt, st))
        used.add(st.external_id)
        break
  return pairs


match_transactions = match
