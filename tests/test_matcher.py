from reconciliation.core.canonical import Source, Status, TxnState
from reconciliation.core.matcher import ManualPair, Orphan, match
from tests.conftest import make_txn


def test_match_by_same_id_ok():
  ledger = [make_txn("T-1001")]
  statement = [make_txn("T-1001", source=Source.STATEMENT)]
  results = match(ledger, statement)
  assert len(results) == 1
  assert results[0].status == Status.OK


def test_match_with_price_difference():
  ledger = [make_txn("T-1011", price="3400", amount="34000")]
  statement = [make_txn("T-1011", source=Source.STATEMENT, price="3417", amount="34170")]
  assert match(ledger, statement)[0].status == Status.DIFF


def test_cancelled_excluded_from_ledger_pool():
  ledger = [make_txn("T-1018", state=TxnState.CANCELLED)]
  statement = [make_txn("T-1018", source=Source.STATEMENT)]
  results = match(ledger, statement)
  # cancelled ledger row skipped; statement row has no ledger pair
  assert len(results) == 1
  assert results[0].status == Status.UNMATCHED_S


def test_unmatched_both_sides():
  ledger = [make_txn("T-1016", instrument="BTC-USD")]
  statement = [make_txn("C-9001", source=Source.STATEMENT, instrument="ETH-USD")]
  results = match(ledger, statement)
  statuses = {r.status for r in results}
  assert Status.UNMATCHED_L in statuses
  assert Status.UNMATCHED_S in statuses


def test_manual_match():
  ledger = [make_txn("T-1016")]
  statement = [make_txn("C-9001", source=Source.STATEMENT)]
  manual = [ManualPair("T-1016", "C-9001")]
  results = match(ledger, statement, manual=manual)
  assert any(r.status == Status.MANUAL for r in results)


def test_accepted_orphan():
  ledger = [make_txn("T-1016")]
  orphans = [Orphan(Source.LEDGER, "T-1016")]
  results = match(ledger, [], orphans=orphans)
  assert results[0].status == Status.ORPHAN


def test_assignment_sample_counts():
  from pathlib import Path
  from reconciliation.core.parsers import parse_csv

  root = Path(__file__).parent.parent / "data"
  ledger = parse_csv(Source.LEDGER, (root / "ledger.csv").read_text())
  statement = parse_csv(Source.STATEMENT, (root / "statement.csv").read_text())
  results = match(ledger, statement)

  by_status = {}
  for r in results:
    by_status[r.status] = by_status.get(r.status, 0) + 1

  assert by_status.get(Status.OK, 0) == 3
  assert by_status.get(Status.DIFF, 0) == 1
  assert by_status.get(Status.UNMATCHED_L, 0) == 1
  assert by_status.get(Status.UNMATCHED_S, 0) == 1
