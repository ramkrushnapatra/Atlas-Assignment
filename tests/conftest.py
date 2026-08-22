from datetime import datetime, timezone
from decimal import Decimal

from reconciliation.core.canonical import Source, Txn, TxnState


def make_txn(eid, source=Source.LEDGER, instrument="BTC-USD", side="BUY",
             qty="1", price="100", amount="100", state=TxnState.SETTLED,
             traded_at=None):
  return Txn(
    source=source,
    external_id=eid,
    traded_at=traded_at or datetime(2025, 7, 1, 9, 0, tzinfo=timezone.utc),
    instrument=instrument,
    side=side,
    quantity=Decimal(qty),
    price=Decimal(price),
    gross_amount=Decimal(amount),
    state=state,
  )
