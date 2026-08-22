# Reconciliation Problem — Take-Home Assignment B

**Stack:** Python 3.9+, Flask, SQLAlchemy, SQLite, Jinja2 templates

---

## How to Run

```bash
pip install -r requirements.txt
python app.py
# open http://localhost:5000
```


### Daily workflow

1. Upload ledger and/or statement CSV on the dashboard
2. Click **Start Reconciliation Run**
3. Review results — OK, differences, unmatched
4. Click **View** to see field-level diffs
5. Click **Manual Match** to pair rows or accept orphans
6. Next day — repeat; step 5 decisions still apply

---

## Project Structure

```
Atlas-Assignment/
├── app.py                    # Flask routes
├── requirements.txt
├── reconciliation.db         # auto-created
├── templates/
│   ├── base.html
│   ├── index.html            # dashboard + upload
│   ├── run_detail.html       # run results
│   ├── match_detail.html     # field diffs
│   └── manual_match.html
├── static/style.css
└── reconciliation/
    ├── core/                 # pure logic, no DB
    │   ├── canonical.py      # Txn, Match, Status, FieldDiff
    │   ├── normalizer.py     # parse_dt, norm_side, norm_state
    │   ├── parsers.py        # LedgerParser, StatementParser
    │   ├── config.py         # Tolerance
    │   ├── comparator.py     # compare()
    │   └── matcher.py        # match()
    ├── db/
    │   ├── connection.py     # engine, get_session, init_db
    │   └── models.py         # 5 tables
    └── services/
        └── service.py        # upload, start_run, resolutions
```

| Layer | Does what | Imports |
|---|---|---|
| `core/` | parse, match, compare | nothing external |
| `db/` | SQLite tables + sessions | core types only |
| `services/` | wires core ↔ db | core + db |
| `app.py` | HTTP + HTML | services |



---

## Key Code Reference

### Core types (`canonical.py`)

| Name | Purpose |
|---|---|
| `Txn` | normalized transaction row |
| `Match` | one match result (status, ledger, statement, diffs) |
| `Status` | `OK`, `DIFF`, `UNMATCHED_L`, `UNMATCHED_S`, `MANUAL`, `ORPHAN` |
| `FieldDiff` | one field difference (`field`, `ledger_val`, `statement_val`, `ok`) |
| `Source` | `LEDGER` or `STATEMENT` |

Aliases kept for compatibility: `CanonicalTransaction = Txn`, `MatchStatus = Status`, etc.

### Core functions

| Function | File | What it does |
|---|---|---|
| `parse_csv(source, text)` | parsers.py | CSV → list of `Txn` |
| `compare(a, b, tol)` | comparator.py | field-by-field diff |
| `match(ledger, statement)` | matcher.py | auto-match + classify |
| `upload(session, fname, content, src)` | service.py | save file + rows to DB |
| `start_run(session)` | service.py | run reconciliation, save results |
| `save_match(session, lid, sid)` | service.py | persist manual pair |
| `save_orphan(session, src, eid)` | service.py | accept row has no pair |

### Flask routes (`app.py`)

| Route | Action |
|---|---|
| `GET /` | dashboard |
| `POST /upload` | upload CSV |
| `POST /run` | start reconciliation |
| `GET /run/<id>` | run results |
| `GET /run/<id>/match/<mid>` | field diffs |
| `GET/POST /run/<id>/manual-match` | manual match / accept orphan |

---

## Architecture

```
Browser → app.py → service.py → core (match/compare)
                      ↕
                    db (SQLite)
```

### Start run pipeline

1. Load transactions from `transactions` table
2. Load active rows from `manual_resolutions`
3. Call `match()` — pure Python, no I/O
4. Save results to `match_results` (diffs as JSON)
5. Show results page

### Upload pipeline

1. SHA-256 hash → skip if duplicate
2. `parse_csv()` → `Txn` objects
3. New `external_id` → insert
4. Existing + changed values → overwrite row
5. Existing + same values → skip

---

## Database (5 tables)

| Table | Model class | Purpose |
|---|---|---|
| `source_files` | `SourceFile` | uploaded files, hash for dedup |
| `transactions` | `TxnRow` | current normalized rows |
| `reconciliation_runs` | `Run` | each daily run |
| `match_results` | `MatchRow` | results + `field_diffs_json` |
| `manual_resolutions` | `Resolution` | persistent manual decisions |

Field diffs stored as JSON on `match_results.field_diffs_json` — no separate diffs table.

Correction files overwrite the current row in `transactions` — no audit history table (kept simple for 5–6 hour scope).

---

## Matching logic (`matcher.py`)

```
1. skip cancelled rows
2. apply manual pairs first
3. auto-match by external_id
4. fuzzy-match leftovers (same instrument + side + qty + time)
5. mark remaining as unmatched or accepted orphan
```

### Tolerances (`config.py`)

```python
Tolerance(amt_abs=0.01, amt_pct=0.001, qty_abs=0.001, time_mins=60)
```

| Field | Rule |
|---|---|
| instrument, side | exact |
| quantity | ±0.001 |
| price, gross_amount | ±$0.01 or ±0.1% |
| traded_at | ±60 minutes |

---

## Design Decisions

| Area | Decision | Why |
|---|---|---|
| Match key | `external_id` first, fuzzy fallback | reliable + handles different IDs |
| Cancelled rows | excluded from matching | not meant to be compared |
| Duplicate files | SHA-256 hash | same content = skip |
| Corrections | overwrite current row | simple, fixed values win |
| Manual decisions | `manual_resolutions` table | must hold tomorrow |
| Field diffs | JSON on match row | fewer tables, same UI |
| UI | server-rendered Flask | assignment allows it |
| Auth | none | single operator, out of scope |

---

## What Was Left Out

- User authentication
- REST API / SPA frontend
- SFTP / webhook file ingestion
- Export to Excel/PDF
- Background job queue
- Configurable tolerances in UI
- Correction audit history UI
- Bulk manual match

---

## What I Would Do Next

1. Unit tests for `parse_csv`, `match`, `compare`, upload dedup
2. Sample CSV files in `data/` for demo video
3. Correction history table + UI
4. Configurable tolerances per instrument
5. PostgreSQL for production
6. Scheduled morning runs via cron

---

## Challenges Faced

1. **Python 3.9 + SQLAlchemy** — `Mapped[int | None]` fails at runtime; used `Optional[int]` instead
2. **Windows pip** — SQLAlchemy tried to compile `greenlet`; fixed with prebuilt wheels
3. **Scope vs completeness** — trimmed from 7 tables to 5, merged 3 service files into 1
4. **Correction handling** — overwrite instead of full audit trail to stay within time box
5. **Cancelled rows** — parsed and stored but filtered out before matching

---

## CSV Formats

**Ledger:**
```
trade_id,traded_at,instrument,side,quantity,price,gross_amount,state
T-1001,2025-07-01T09:15:00Z,BTC-USD,BUY,0.50,62000.00,31000.00,SETTLED
```

**Statement:**
```
reference,executed_at,symbol,direction,qty,unit_price,total,status
T-1001,2025-07-01 09:15:00,BTC-USD,B,0.5,62000,31000.00,SETTLED
```

| Txn field | Ledger col | Statement col |
|---|---|---|
| external_id | trade_id | reference |
| traded_at | traded_at | executed_at |
| instrument | instrument | symbol |
| side | side (BUY/SELL) | direction (B/S) |
| quantity | quantity | qty |
| price | price | unit_price |
| gross_amount | gross_amount | total |
| state | state | status |

Side mapping: `B` → `BUY`, `S` → `SELL`  
State mapping: `VOID` / `CANCELED` → `CANCELLED`

---


