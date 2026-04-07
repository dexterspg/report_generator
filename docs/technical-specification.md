# Implementation Brief: CTR FX Remeasurement Tool

## UI Design Reference

**Mockup:** `webapp/mockup-v1.html` — 9 screens covering all Phase 1 states (empty, partial config, file uploaded, processing, error, results, account mapping config, exchange rates config, history). Frontend components should match these screens.

## Sister Project / Pattern

**CTR Mapper (Poliza Ledger)** at `C:/workarea/maturity_analysis_report/webapp/`

FastAPI + Vue 3 (Options API with Composition `setup()`) + openpyxl. Background job processing with status polling. Dual-mode: web server (`0.0.0.0:8000`) and desktop (`localhost:5001` + auto-browser). Same blue brand background `#009cde`.

## What's Reused

- **Backend skeleton:** FastAPI app structure, CORS middleware, upload directory management, `cleanup_old_files()`, background task pattern with job ID + status polling, `/status/{job_id}` + `/health` + `/cleanup` endpoints, dual-mode `main()` with `--desktop` flag, PyInstaller path resolution
- **CTR parsing logic:** `pd.read_excel(source, header=26)` reads header row 27, core column validation, `input_header_start` / `input_data_start` defaults (27/28). The CTR format is fixed (Nakisa system export) — the same source columns are present regardless of which output report is being generated. `ctr_reader.py` owns this shared knowledge; each output processor defines only the subset it needs.
- **Pydantic models:** `ProcessingRequest`, `ProcessingResponse`, `JobStatus` schemas (with minor field additions)
- **Frontend infrastructure:** Vue 3 project scaffolding, `main.js`, `vite.config.js`, `package.json` deps (axios, vue)
- **Shared components (adapted):** `ProgressSection.vue`, `ErrorSection.vue`, `AppFooter.vue` carry over as-is. `AppHeader.vue` carries over with new title/subtitle text
- **Global CSS:** `styles.css` reused nearly verbatim (background `#009cde`, `.card`, `.btn-*`, `.upload-area`, `.progress-*`, `.results-grid`, `.download-section`, animations). The base styling IS the brand identity
- **File validation:** 50MB limit, `.xlsx`/`.xls`/`.csv` accept types, drag-and-drop behavior

## What's New

1. **FX Remeasurement processing engine** (`fx_processor.py` — replaces `formula_mapper.py` + `ExcelProcessor`)
   - Uses vectorized `COLUMN_MAPPINGS` dict pattern: `{ column_name: callable(df, account_mapping, exchange_rates) -> pd.Series }`
   - Group by `{Account Number, Account Name, Contract Currency}` and aggregate `Amount in Contract Currency` and `Amount in Company Currency`
   - Apply account mapping (Account Type: free text e.g. Asset, Liability, Contra Asset; Monetary: Monetary/Non-Monetary)
   - Apply period-end exchange rates per currency pair
   - Calculate Re-measured Balance: `balance_cc * spot_rate` (monetary) or `initial_measurement` (non-monetary)
   - Calculate FX (Gain) or Loss: `remeasured_balance - initial_measurement`
   - Output 12-column workbook (Contract ID + 11 data columns) with one worksheet per unique Contract Currency

2. **File-based configuration management** (replaces single-file upload + editable table approach)
   - Both configs (account mapping + exchange rates) managed as uploadable/downloadable CSV/Excel files
   - Account mapping columns: `Account Number`, `Account Type`, `Monetary?`, `Rate` (4 columns)
   - Exchange rates columns: `RateType`, `FromCurrency`, `ToCurrency`, `ValidFrom`, `ExchangeRate` (5 columns). Duplicate detection uses internal auto-generated ID; merge key is composite `{FromCurrency, ToCurrency, ValidFrom}`
   - Exchange rate lookup: match `FromCurrency` → account's contract currency, `ToCurrency` → company currency
   - Two upload modes: **Replace** (overwrite all) and **Merge** (add new + update existing by key)
   - Download current config as styled Excel for sharing between desktop users
   - Reset capability to clear all saved data per config type
   - Internal persistence as JSON files in `%LOCALAPPDATA%/CTR-FX-Remeasurement/config/`

3. **Configuration history (view-only)**
   - Every config change (upload, reset) recorded as a history entry with full snapshots
   - Users can view history as a read-only table (Timestamp, Action, Config, Details)
   - Rollback is manual: user navigates to the history folder and deletes the most recent entry
   - No rollback button in the UI (Phase 2 feature)
   - Stored as individual JSON files in `%LOCALAPPDATA%/CTR-FX-Remeasurement/history/`

4. **Frontend redesign** (clean, purpose-built)
   - No company code dropdown scaffolding
   - No i18n (English only per FR-020) — removed `vue-i18n` dependency entirely
   - No `HelpGuide` modal or `LanguageSelector` component
   - Two-step UI: Step 1 (Configuration) with side-by-side account mapping + exchange rates panels, Step 2 (Upload CTR) with drag-and-drop
   - Simplified results view: source filename, processing time, summary stats (input rows, output rows, currencies) + download button only. No multi-currency table preview or warnings in the UI

5. **CSV support** (FR-001, FR-024) — `pandas.read_csv()` path alongside Excel

6. **Metadata extraction** from rows 1-26 (FR-002) — contract currency, company currency, and company only (the three fields actually consumed by the processing logic)

## Deployment Model

**Desktop mode is the primary deployment target.** The application is distributed as a single `.exe` file built with PyInstaller. Users run it on their own laptops — no server, no internet access required.

- **Desktop mode (`--desktop` or `.exe`):** `localhost:5001`, auto-opens browser, single-user
- **Web mode (dev/secondary):** `0.0.0.0:8000`, multi-user server
- **Data storage (desktop):** `%LOCALAPPDATA%/CTR-FX-Remeasurement/` — per-user, no admin rights, survives `.exe` updates
- **Data storage (dev):** `webapp/backend/` directory
- **Config sharing:** Users download configs as Excel files and share them (email, network drive, etc.); recipients upload into their own copy

## File Tree

```
webapp/
  backend/
    app.py                          -- FastAPI app with config management, history, and processing endpoints
    config/                         -- Dev-mode config storage (desktop uses %LOCALAPPDATA%)
      account_mapping.json
      exchange_rates.json
    history/                        -- Dev-mode history storage
      {uuid}.json                   -- One file per history entry (timestamp, action, snapshots)
    uploads/                        -- Temporary file storage (cleaned up after 1 hour)
    models/
      __init__.py
      schemas.py                    -- ProcessingRequest, ProcessingResponse, JobStatus, FileInfo
    services/
      __init__.py
      ctr_reader.py                 -- Shared CTR parsing layer. Validates 7 core columns, extracts contract currency + company currency + company from rows 1-26 (Excel only), normalizes currencies, fills missing Account Names, coerces numeric amounts, detects conflicting Account Names. CSV returns None for metadata fields.
      fx_processor.py               -- FX Remeasurement engine using COLUMN_MAPPINGS dict pattern. Each column is a callable taking (df, account_mapping, exchange_rates) → pd.Series. Uses numpy vectorized operations (np.where) instead of row-by-row iteration.
      config_store.py               -- Config persistence + file parsing/export + history. Key functions:
                                       - _get_app_data_dir() → resolves %LOCALAPPDATA% (desktop) or backend/ (dev)
                                       - load/save/reset_account_mapping(), load/save/reset_exchange_rates()
                                       - parse_account_mapping_file(), parse_exchange_rates_file() — parse CSV/Excel with flexible column name aliases
                                       - merge_account_mapping(), merge_exchange_rates() — merge incoming into existing
                                       - export_account_mapping(), export_exchange_rates() — export as styled Excel for sharing
                                       - save_history_entry() — snapshots both configs at time of action
                                       - list_history(), get_history_entry() — retrieve history (list returns summaries, get returns full with snapshots)
  frontend-vue/
    index.html
    vite.config.js
    package.json
    src/
      main.js                       -- Vue 3 app mount (no i18n plugin)
      App.vue                       -- View state machine: upload -> progress -> results -> error
      assets/
        styles.css                  -- Cloned from sister project, minor tweaks
      components/
        AppHeader.vue               -- Title: "CTR FX Remeasurement", subtitle: "Consolidated Transaction Report — FX Gain/Loss Calculator"
        AppFooter.vue               -- Minimal footer (same as sister)
        ProgressSection.vue         -- Progress bar + spinner (hardcoded English)
        ErrorSection.vue            -- Error display + retry (hardcoded English)
        ProcessCTR.vue              -- File upload area with readiness checklist (Account Mapping count, Exchange Rates count)
        AccountMapping.vue          -- Upload interface with Replace/Merge modes, Download, and Clear All buttons (no preview table)
        ExchangeRates.vue           -- Upload interface with Replace/Merge modes, Download, and Clear All buttons (no preview table)
        ResultsView.vue             -- Source filename, processing time, summary stats (Input Rows, Output Rows, Currencies) with Download button only
        HistoryView.vue             -- Read-only history table showing audit trail of configuration changes
        ProcessingView.vue          -- Progress polling display during file processing
        ErrorView.vue               -- Error state display with retry option
```

## Backend API Endpoints

### Configuration — Account Mapping

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/config/account-mapping` | Return current saved account mapping |
| `POST` | `/config/account-mapping` | Upload account mapping file (CSV/Excel). Form fields: `file` (multipart), `mode` ("replace" or "merge") |
| `GET` | `/config/account-mapping/download` | Download current mapping as styled Excel file |
| `DELETE` | `/config/account-mapping` | Reset (clear) all saved account mapping data |

### Configuration — Exchange Rates

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/config/exchange-rates` | Return current saved exchange rates |
| `POST` | `/config/exchange-rates` | Upload exchange rates file (CSV/Excel). Form fields: `file` (multipart), `mode` ("replace" or "merge") |
| `GET` | `/config/exchange-rates/download` | Download current rates as styled Excel file |
| `DELETE` | `/config/exchange-rates` | Reset (clear) all saved exchange rate data |

### History

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/history` | List config change history (most recent first). Query param: `limit` (default 50). Returns: timestamp, action, config_type, details |
| `GET` | `/history/{entry_id}` | Get full history entry including config snapshots |
| `DELETE` | `/history` | Clear all history entries |
| `POST` | `/history/{entry_id}/rollback` | **Phase 2** — not implemented in Phase 1 |

### Core Processing

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Serve frontend (index.html) or API info |
| `GET` | `/status/{job_id}` | Get processing status for a job |
| `GET` | `/health` | Health check (includes mode: desktop/web) |
| `DELETE` | `/cleanup` | Manual cleanup of old files and jobs |

**Note:** The CTR upload and processing endpoint (`POST /upload` or equivalent) is not yet implemented — it will accept the CTR file, run `ctr_reader.py` → `fx_processor.py`, and return results via the job status polling pattern.

## Key Design Decisions

### 1. Account Mapping Input: File upload (not editable table)

**Why:** The application is a standalone desktop tool distributed as a `.exe`. Multiple team members on different laptops need to share the same account mapping. A file-based approach (upload CSV/Excel, download to share) is simpler than an editable UI table and supports the desktop sharing model naturally.

**How it works:**
- User uploads a CSV or Excel file with columns: `Account Number`, `Account Type`, `Monetary?` (Monetary/Non-Monetary), `Rate` (Historical/Period End)
- Column names are matched flexibly (e.g., "Acct Num", "Account No.", "account_number" all work)
- Upload mode is either **Replace** (clear existing, load from file) or **Merge** (add new, update existing by Account Number)
- Phase 1 UI: Upload area with Replace/Merge toggle, plus Download and Clear All buttons (no preview table of current mapping)
- API supports viewing current mapping via `GET /config/account-mapping` and downloading styled Excel via `GET /config/account-mapping/download`
- Reset via `DELETE /config/account-mapping` clears all saved data
- Every upload and reset is recorded in history with a full config snapshot for rollback

### 2. Exchange Rate Input: File upload with Replace/Merge

**Why:** Same rationale as account mapping — file-based for desktop sharing. Clients already maintain rate tables in Excel.

**How it works:**
- User uploads a CSV or Excel file with columns: `RateType`, `FromCurrency`, `ToCurrency`, `ValidFrom`, `ExchangeRate`
- The system auto-generates an internal `id` (UUID) on insert; merge key is composite `{FromCurrency, ToCurrency, ValidFrom}`
- The system finds the correct rate by matching `FromCurrency` to the account's contract currency and `ToCurrency` to the company currency (from CTR metadata)
- Same Replace/Merge upload modes as account mapping
- Phase 1 UI: Upload area with Replace/Merge toggle, plus Download and Clear All buttons (no preview table of current rates)
- Same API download, reset, and history tracking capabilities (preview table is Phase 2 feature)
- Currency codes normalized to uppercase; rates stored as exact text (Python `Decimal` used for all arithmetic — no float conversion)

**Why SQLite (not JSON) for exchange rates:**
Clients may have multiple rates per currency pair across different time periods (e.g. monthly period-end rates). The processor must find the rate valid on or before the CTR's fiscal period date — a date-range lookup that is error-prone in flat JSON but trivial in SQL. Account mapping has no time dimension, so it stays as JSON.

**Rate lookup query (executed by `config_store.py`):**
```sql
SELECT exchange_rate FROM exchange_rates
WHERE from_currency = ? AND to_currency = ?
  AND valid_from <= ?
ORDER BY valid_from DESC
LIMIT 1
```

**Future migration note:** Raw `sqlite3` (Python stdlib) is used — zero added bundle size, no client install. When deploying to Render, swap `config_store.py`'s connection to PostgreSQL (connection string change only). SQL queries are compatible. SQLAlchemy can be introduced at that point if needed.

### 3. Local Storage in %LOCALAPPDATA%

**Why:** Desktop `.exe` users should not need admin rights, and config data should survive when a new version of the `.exe` is distributed. `%LOCALAPPDATA%` is per-user, writable without elevation, and independent of the `.exe` location.

**Storage structure:**
```
%LOCALAPPDATA%/CTR-FX-Remeasurement/
  ctr_fx.db                       -- Single SQLite database (all persistent data)
  uploads/                        -- Temporary files (auto-cleaned after 1 hour)
```

### 3a. Database Schema

All persistent data lives in a single SQLite file: `ctr_fx.db`. Three tables.

---

**`account_mapping` table**

| Column | Type | Description |
|---|---|---|
| `id` | TEXT PRIMARY KEY | Auto-generated UUID on insert |
| `account_number` | TEXT UNIQUE | Account number from CTR — merge key |
| `account_type` | TEXT | Free text from client (e.g. `Asset`, `Liability`, `Contra Asset`) |
| `monetary` | TEXT | `Monetary` or `Non-Monetary` |
| `rate` | TEXT | `Historical` or `Period End` |

```sql
CREATE TABLE IF NOT EXISTS account_mapping (
    id             TEXT PRIMARY KEY,
    account_number TEXT NOT NULL UNIQUE,
    account_type   TEXT NOT NULL,
    monetary       TEXT NOT NULL,
    rate           TEXT NOT NULL
);
```

**Merge key:** `account_number` (UNIQUE constraint) — on merge, `INSERT OR REPLACE` using the UNIQUE constraint.
**Replace mode:** `DELETE FROM account_mapping` then bulk insert.

---

**`exchange_rates` table**

| Column | Type | Description |
|---|---|---|
| `id` | TEXT PRIMARY KEY | Auto-generated UUID on insert |
| `rate_type` | TEXT | Rate type code (e.g. `M` for month-end) |
| `from_currency` | TEXT | Contract currency (e.g. `EUR`) — normalized to uppercase |
| `to_currency` | TEXT | Company currency (e.g. `USD`) — normalized to uppercase |
| `valid_from` | TEXT | ISO date `YYYY-MM-DD` — the date this rate becomes effective |
| `exchange_rate` | TEXT | The exchange rate value — stored as text to preserve exact decimal precision (no float rounding) |

```sql
CREATE TABLE IF NOT EXISTS exchange_rates (
    id            TEXT PRIMARY KEY,
    rate_type     TEXT,
    from_currency TEXT NOT NULL,
    to_currency   TEXT NOT NULL,
    valid_from    TEXT NOT NULL,
    exchange_rate TEXT NOT NULL,
    UNIQUE(from_currency, to_currency, valid_from)
);

CREATE INDEX IF NOT EXISTS idx_exchange_rates_lookup
    ON exchange_rates (from_currency, to_currency, valid_from);
```

**Rate lookup:** most recent rate on or before the CTR fiscal period date.
**Merge key:** composite `{from_currency, to_currency, valid_from}` — on merge, `INSERT OR REPLACE` using the UNIQUE constraint.
**Replace mode:** `DELETE FROM exchange_rates` then bulk insert.

---

**`config_history` table**

| Column | Type | Description |
|---|---|---|
| `id` | TEXT PRIMARY KEY | UUID generated at insert time |
| `timestamp` | TEXT | ISO datetime `YYYY-MM-DDTHH:MM:SS` |
| `action` | TEXT | `upload`, `reset` |
| `config_type` | TEXT | `account_mapping`, `exchange_rates`, `both` |
| `source_filename` | TEXT | Original uploaded filename (null for reset) |
| `details` | TEXT | Human-readable summary (e.g. "42 rows loaded") |
| `snapshot_account_mapping` | TEXT | Full JSON snapshot of account_mapping at this point |
| `snapshot_exchange_rates` | TEXT | Full JSON snapshot of exchange_rates at this point |

```sql
CREATE TABLE IF NOT EXISTS config_history (
    id                        TEXT PRIMARY KEY,
    timestamp                 TEXT NOT NULL,
    action                    TEXT NOT NULL,
    config_type               TEXT NOT NULL,
    source_filename           TEXT,
    details                   TEXT,
    snapshot_account_mapping  TEXT,
    snapshot_exchange_rates   TEXT
);
```

**Append-only** — never updated, only inserted. Snapshots retained for Phase 2 rollback capability.

### 4. Configuration History with Rollback

**Why:** Audit trail for accountability — users can see what config changes were made and when.

**How it works:**
- `save_history_entry()` is called on every config change (upload, reset)
- Each entry stores: timestamp, action, config_type, source_filename, details, plus full snapshots of both configs at that moment
- `list_history()` returns summaries (without bulky snapshots) for display as a read-only table
- UI displays: Timestamp, Action, Config, Details — read-only audit log
- Snapshots are stored for Phase 2 rollback capability but not used in Phase 1
- **Phase 1 recovery from bad upload:** download current config → edit in Excel → re-upload with Replace mode

### 5. COLUMN_MAPPINGS Vectorized Pattern in fx_processor.py

**Why:** Same pattern as the sister project's `FORMULA_MAPPINGS` in `formula_mapper.py`. Each output column is a pure function that takes the DataFrame + config and returns a pandas Series. This enables vectorized numpy operations instead of row-by-row iteration, and makes adding/modifying columns trivial.

**Structure:**
```python
COLUMN_MAPPINGS = {
    "Contract ID": _col_contract_id,
    "Account Number": _col_account_number,
    "Account Name": _col_account_name,
    "Account Type": _col_account_type,
    "Monetary?": _col_monetary,
    "Account Currency": _col_account_currency,
    "Balance in Contract Currency": _col_balance_cc,
    "Initial Measurement Company Currency Balance": _col_initial_measurement,
    "Rate": _col_rate,                          # from account mapping (Historical / Period End)
    "Period-End Spot Exchange Rate": _col_spot_rate,  # matched by FromCurrency + ToCurrency
    "Re-measured Balance": _col_remeasured_balance,
    "FX (Gain) or Loss": _col_fx_gain_loss,
}
```

Each callable: `(df: pd.DataFrame, account_mapping: list[dict], exchange_rates: list[dict]) -> pd.Series`

### 6. Output: Single `.xlsx` file (not ZIP)

Unlike the sister project which generates one file per company code and ZIPs them, this tool produces a single workbook with one worksheet per currency. No ZIP needed in Phase 1.

### 7. Drop `template_header_start` / `template_data_start` from sister project

The sister project's `ProcessingRequest` includes `template_header_start` and `template_data_start` for configurable output formatting. These are NOT carried over — the FX tool's output format is fixed (headers in row 1, data from row 2) per FR-013.

### 8. No i18n

Per FR-020, English only. Remove `vue-i18n` dependency entirely. All strings are hardcoded in templates. This eliminates the `i18n/` directory, locale JSON files, `LanguageSelector.vue`, and `useI18n()` calls.

## Data Flow

```
                                          +---------------------+
                                          |  User's Desktop     |
                                          |                     |
                                          |  Step 1: Configure  |
                                          |   - Upload account  |
                                          |     mapping file    |
                                          |   - Upload exchange |
                                          |     rates file      |
                                          |   (Replace / Merge) |
                                          +--------+------------+
                                                   |
                                          POST /config/account-mapping
                                          POST /config/exchange-rates
                                                   |
                                                   v
                                     +-------------+-------------+
                                     |  config_store.py           |
                                     |                           |
                                     |  - Parse CSV/Excel file   |
                                     |  - Apply replace/merge    |
                                     |  - Save to JSON           |
                                     |  - Record history entry   |
                                     |  - Return current config  |
                                     +-------------+-------------+
                                                   |
                                          (Configs saved locally)
                                                   |
                                                   v
                                          +--------+------------+
                                          |  Step 2: Upload CTR  |
                                          |                     |
                                          |  - Drag-and-drop    |
                                          |    CTR report file   |
                                          |  - Click "Process"   |
                                          +--------+------------+
                                                   |
                                          POST /upload (multipart)
                                                   |
                                                   v
                                     +-------------+-------------+
                                     |  ctr_reader.py             |
                                     |                           |
                                     |  - Parse metadata 1-26   |
                                     |  - Read headers row 27   |
                                     |  - Validate 7 core cols  |
                                     |  - Normalize currencies  |
                                     |  - Coerce numeric amounts|
                                     +-------------+-------------+
                                                   |
                                                   v
                                     +-------------+-------------+
                                     |  fx_processor.py (bg task)|
                                     |                           |
                                     |  - Load saved configs    |
                                     |  - Group by {AcctNum,    |
                                     |    AcctName, Currency}   |
                                     |  - Apply COLUMN_MAPPINGS |
                                     |    (vectorized)          |
                                     |  - Write .xlsx (1 sheet  |
                                     |    per currency)         |
                                     +-------------+-------------+
                                                   |
                                      GET /status/{job_id} (poll)
                                                   |
                                                   v
                                          +--------+------------+
                                          |  Results View        |
                                          |                     |
                                          |  - Summary stats    |
                                          |    (rows, ccys)     |
                                          |  - Download .xlsx   |
                                          +---------------------+
```

### Output Excel Structure (per worksheet, one per currency)

Rows within each worksheet are sorted by Account Number ascending (FR-010).

| Col | Header | Source |
|-----|--------|--------|
| 1 | Contract ID | CTR grouping key |
| 2 | Account Number | CTR grouping key |
| 3 | Account Name | CTR grouping key (first occurrence) |
| 4 | Account Type | Account mapping config |
| 5 | Monetary? | Account mapping config (Monetary / Non-Monetary) |
| 6 | Account Currency | CTR Contract Currency (worksheet name) |
| 7 | Balance in Contract Currency | SUM(Amount in Contract Currency) per group |
| 8 | Initial Measurement Company Currency Balance | SUM(Amount in Company Currency) per group |
| 9 | Rate | Account mapping config (Historical / Period End) |
| 10 | Period-End Spot Exchange Rate | Exchange rates config (matched by FromCurrency → contract ccy, ToCurrency → company ccy) |
| 11 | Re-measured Balance | col7 * col10 (Period End) or col8 (Historical) |
| 12 | FX (Gain) or Loss | col11 - col8 |

**Number Formatting:** All numeric values are stored and calculated using Python `Decimal` — no float conversion at any stage. Output columns preserve the exact precision from the input. No rounding or truncation. What the user uploads is exactly what they get back.

### Data Quality Handling (FR-011)

- **Missing Account Name:** If Account Name is null or empty in the source data, it defaults to "—"
- **Conflicting Account Names:** When the same Account Number appears with different Account Names across CTR rows, the first occurrence is used and a warning is logged

### Unmapped Account Handling

Accounts present in the CTR but missing from the account mapping config:
- Columns 1-3, 6-8 are populated (aggregation works regardless)
- Columns 4-5 show "N/A"
- Columns 9-12 are left blank
- The output Excel includes these rows so the user can see what was missed

---

**Document Status:** Draft
**Last Updated:** 2026-03-24
