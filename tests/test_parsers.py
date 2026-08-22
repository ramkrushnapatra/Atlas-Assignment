from decimal import Decimal

from reconciliation.core.canonical import Source, TxnState
from reconciliation.core.parsers import parse_csv


LEDGER = """trade_id,traded_at,instrument,side,quantity,price,gross_amount,state
T-1001,2025-07-01T09:15:00Z,BTC-USD,BUY,0.50,62000.00,31000.00,SETTLED"""

STATEMENT = """reference,executed_at,symbol,direction,qty,unit_price,total,status
T-1001,2025-07-01 09:15:00,BTC-USD,B,0.5,62000,31000.00,SETTLED"""


def test_ledger_parser():
  rows = parse_csv(Source.LEDGER, LEDGER)
  assert len(rows) == 1
  t = rows[0]
  assert t.external_id == "T-1001"
  assert t.side == "BUY"
  assert t.quantity == Decimal("0.50")
  assert t.state == TxnState.SETTLED


def test_statement_parser_normalizes_side():
  rows = parse_csv(Source.STATEMENT, STATEMENT)
  t = rows[0]
  assert t.external_id == "T-1001"
  assert t.side == "BUY"
  assert t.instrument == "BTC-USD"
