# Reconciliation Problem — Take-Home Assignment B

Daily reconciliation tool: compare our **ledger** CSV against a counterparty **statement** CSV, find mismatches, and let an operator resolve them manually. Manual decisions persist across runs.

**Stack:** Python 3.9+, Flask, SQLAlchemy, SQLite, Jinja2 (server-rendered HTML)

---

## Prerequisites

- Python 3.9 or higher
- pip

Check your version:

```bash
python --version
pip --version
```

---

## Setup & Run

### 1. Clone the repo

```bash
git clone <your-repo-url>
cd Atlas-Assignment
```

### 2. (Recommended) Create virtual environment

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Mac/Linux
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

| Package | Purpose |
|---|---|
| `flask` | Web server + HTML UI |
| `sqlalchemy` | Database ORM (SQLite) |
| `python-dateutil` | Parse different date formats |
| `pytest` | Run unit tests |

**Windows note:** If SQLAlchemy install fails, try:

```bash
pip install sqlalchemy --only-binary :all:
```

### 4. Start the app

```bash
python app.py
```

Open: **http://localhost:5000**

`reconciliation.db` is created automatically on first run (not committed to git).

### 5. Run tests

```bash
python -m pytest tests/ -v
```

19 tests — core logic only (no database, no browser).

---

## Quick test with sample data

Sample files are included:

```
data/
├── ledger.csv      ← upload as Ledger
└── statement.csv   ← upload as Statement
```

**Steps:**

1. Start app → open dashboard
2. Upload `data/ledger.csv` → **Upload Ledger**
3. Upload `data/statement.csv` → **Upload Statement**
4. Click **Start Reconciliation Run**
5. Review results:

| Row | Expected result |
|---|---|
| T-1001 | Matched OK |
| T-1011 | Matched with differences (price +$17) |
| T-1015 | Matched OK (40 min time drift OK) |
| T-1020 | Matched OK |
| T-1016 | Unmatched ledger |
| C-9001 | Unmatched statement |
| T-1018 | Cancelled — excluded |

6. Click **View** on T-1011 to see field diffs
7. Click **Manual Match** to pair T-1016 ↔ C-9001 (optional)

**Correction file checkbox:** Check only when re-uploading a fixed version of an earlier file. For first upload, leave unchecked.

---

## Assignment checklist

| Requirement | Done | Where |
|---|---|---|
| Database design (tables) | ✅ | `reconciliation/db/models.py` — 5 tables |
| Backend — load files, match, compare | ✅ | `reconciliation/services/service.py` |
| Core logic testable without DB/browser | ✅ | `reconciliation/core/` |
| UI — start run, see results | ✅ | `templates/run_detail.html` |
| UI — inspect field diffs | ✅ | `templates/match_detail.html` |
| UI — manual match | ✅ | `templates/manual_match.html` |
| Tests for logic that matters | ✅ | `tests/` — 19 tests |
| README — how to run, decisions, left out | ✅ | this file |
| Sample data | ✅ | `data/ledger.csv`, `data/statement.csv` |

---

## Daily workflow

1. Upload new ledger/statement CSVs (if arrived)
2. **Start Reconciliation Run**
3. Review matched OK / differences / unmatched
4. **View** rows with differences
5. **Manual Match** or **Accept as Orphan** for unresolved rows
6. Tomorrow — repeat; manual decisions from step 5 still apply

---

## Project structure

```
Atlas-Assignment/
├── app.py                    # Flask routes
├── requirements.txt          # pip dependencies
├── .gitignore
├── data/
│   ├── ledger.csv            # sample ledger file
│   └── statement.csv         # sample statement file
├── tests/                    # unit tests (core logic)
├── templates/                # HTML pages
├── static/style.css
└── reconciliation/
    ├── core/                 # pure logic — no DB
    │   ├── canonical.py      # Txn, Match, Status
    │   ├── normalizer.py     # date/side/state parsing
    │   ├── parsers.py        # LedgerParser, StatementParser
    │   ├── config.py         # Tolerance settings
    │   ├── comparator.py     # compare()
    │   └── matcher.py        # match()
    ├── db/
    │   ├── connection.py
    │   └── models.py         # 5 SQLAlchemy tables
    └── services/
        └── service.py        # upload, start_run, resolutions
```

| Layer | Responsibility |
|---|---|
| `core/` | Parse, normalize, match, compare — **no DB imports** |
| `db/` | SQLite persistence |
| `services/` | Orchestrates core + db |
| `app.py` | HTTP routes + HTML |

---

## Database (5 tables)

| Table | Purpose |
|---|---|
| `source_files` | Uploaded CSVs, SHA-256 hash for dedup |
| `transactions` | Current normalized rows (one per trade ID) |
| `reconciliation_runs` | Each daily run |
| `match_results` | Results + field diffs as JSON |
| `manual_resolutions` | Persistent manual match / accept orphan |

---

## Matching logic

```
1. Skip cancelled rows
2. Apply manual pairs first
3. Auto-match by external_id (trade_id / reference)
4. Fuzzy-match leftovers (instrument + side + qty + time)
5. Mark remaining as unmatched or accepted orphan
```

### Tolerances

| Field | Rule |
|---|---|
| instrument, side | exact match |
| quantity | ±0.001 |
| price, gross_amount | ±$0.01 or ±0.1% |
| traded_at | ±60 minutes |

---

## Manual features (assignment requirement)

| Action | When | How |
|---|---|---|
| **Manual match** | Same trade, different IDs | Manual Match screen → pick both → Match Selected |
| **Accept orphan** | Row truly has no pair | Manual Match screen → Accept as Orphan |
| **Persistence** | Decisions hold tomorrow | Saved in `manual_resolutions`, loaded every run |

---

## Design decisions

| Decision | Why |
|---|---|
| Match by `external_id` first | Most reliable key from assignment example |
| Fuzzy match as fallback | Handles different IDs (e.g. C-9001) |
| Cancelled rows excluded | Assignment: "never meant to be compared" |
| SHA-256 dedup | Same file sent twice → skip |
| Corrections overwrite row | Fixed values win; kept simple (no audit table) |
| Field diffs as JSON | Fewer tables, same UI functionality |
| 5 tables not 7 | Scoped for 5–6 hour take-home |
| Server-rendered Flask | Assignment says plain pages are fine |
| No auth | Single operator, out of scope |

---

## What was left out

- User authentication / multi-user
- REST API / React frontend
- SFTP / webhook file ingestion
- Export to Excel/PDF
- Background job queue
- Configurable tolerances in UI
- Correction audit history UI
- Bulk manual match

---

## What I would do next

1. Correction history table + UI ("what did the row used to say?")
2. Configurable tolerances per instrument
3. PostgreSQL for production
4. Scheduled morning runs via cron
5. Plugin registry for new CSV formats

---

## Challenges faced

1. **Python 3.9 + SQLAlchemy** — used `Optional[int]` instead of `int | None` in models
2. **Windows pip** — SQLAlchemy/greenlet compile error; use prebuilt wheels
3. **Scope** — trimmed 7 tables → 5, merged services into one file
4. **Correction handling** — overwrite row instead of full audit trail
5. **Cancelled vs unmatched** — cancelled filtered before matching, not shown in results

---

## CSV formats

**Ledger (our system):**
```
trade_id,traded_at,instrument,side,quantity,price,gross_amount,state
T-1001,2025-07-01T09:15:00Z,BTC-USD,BUY,0.50,62000.00,31000.00,SETTLED
```

**Statement (counterparty):**
```
reference,executed_at,symbol,direction,qty,unit_price,total,status
T-1001,2025-07-01 09:15:00,BTC-USD,B,0.5,62000,31000.00,SETTLED
```

| Txn field | Ledger column | Statement column |
|---|---|---|
| external_id | trade_id | reference |
| traded_at | traded_at (ISO) | executed_at |
| instrument | instrument | symbol |
| side | BUY/SELL | B/S |
| quantity | quantity | qty |
| price | price | unit_price |
| gross_amount | gross_amount | total |
| state | state | status |

New format = new parser class in `parsers.py`. Rest of system unchanged.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `ModuleNotFoundError: flask` | `pip install -r requirements.txt` |
| SQLAlchemy install fails on Windows | `pip install sqlalchemy --only-binary :all:` |
| `BuildError: endpoint 'upload'` | Restart app after latest code pull |
| Old/stale data | Delete `reconciliation.db` and restart app |
| Port 5000 in use | Change port in `app.py`: `app.run(port=5001)` |

---

