# Implementation Brief: CTR FX Remeasurement Tool

## Sister Project / Pattern

**CTR Mapper (Poliza Ledger)** at `C:/workarea/maturity_analysis_report/webapp/`

FastAPI + Vue 3 (Options API with Composition `setup()`) + i18n (vue-i18n) + openpyxl. Background job processing with status polling. Dual-mode: web server (`0.0.0.0:8000`) and desktop (`localhost:5001` + auto-browser). Same blue brand background `#009cde`.

## What's Reused

- **Backend skeleton:** FastAPI app structure, CORS middleware, upload directory management, `cleanup_old_files()`, background task pattern with job ID + status polling, `/upload` + `/status/{job_id}` + `/download/{job_id}` + `/health` + `/cleanup` endpoints, dual-mode `main()` with `--desktop` flag, PyInstaller path resolution
- **CTR parsing logic:** `pd.read_excel(source, header=26)` reads header row 27, core column validation, `input_header_start` / `input_data_start` defaults (27/28). The CTR format is fixed (Nakisa system export) — the same source columns are present regardless of which output report is being generated. `ctr_reader.py` owns this shared knowledge; each output processor (Poliza's `formula_mapper.py`, FX's `fx_processor.py`) defines only the subset it needs.
- **Pydantic models:** `ProcessingRequest`, `ProcessingResponse`, `JobStatus` schemas (with minor field additions)
- **Frontend infrastructure:** Vue 3 project scaffolding, `main.js`, `vite.config.js`, `package.json` deps (axios, vue)
- **Shared components (adapted):** `ProgressSection.vue`, `ErrorSection.vue`, `AppFooter.vue` carry over as-is. `AppHeader.vue` carries over with new title/subtitle text
- **Global CSS:** `styles.css` reused nearly verbatim (background `#009cde`, `.card`, `.btn-*`, `.upload-area`, `.progress-*`, `.results-grid`, `.download-section`, animations). The base styling IS the brand identity
- **File validation:** 50MB limit, `.xlsx`/`.xls`/`.csv` accept types, drag-and-drop behavior

## What's New

1. **FX Remeasurement processing engine** (replaces `formula_mapper.py` + `ExcelProcessor`)
   - Group by `{Account Number, Account Name, Contract Currency}` and aggregate `Amount in Contract Currency` and `Amount in Company Currency`
   - Apply account mapping (Account Type: BS/P&L, Monetary: Yes/No)
   - Apply period-end exchange rates per currency pair
   - Calculate Re-measured Balance: `balance_cc * spot_rate` (monetary) or `initial_measurement` (non-monetary)
   - Calculate FX (Gain) or Loss: `remeasured_balance - initial_measurement`
   - Output 11-column workbook with one worksheet per unique Contract Currency

2. **Multi-input upload flow** (replaces single-file upload)
   - CTR file upload (required) -- same drag-and-drop area
   - Account mapping input (required for full calculation, optional for partial output)
   - Period-end exchange rate input (required for full calculation, optional for partial output)

3. **Frontend redesign** (clean, purpose-built)
   - No company code dropdown scaffolding
   - No i18n (English only per FR-020) -- remove `vue-i18n` dependency entirely
   - No `HelpGuide` modal or `LanguageSelector` component
   - New `InputPanel` component for account mapping + exchange rate entry
   - New results view showing per-currency summary with warnings for unmapped accounts

4. **CSV support** (FR-001, FR-024) -- `pandas.read_csv()` path alongside Excel

5. **Metadata extraction** from rows 1-26 (FR-002) -- fiscal year, period, accounting standard, company currency, etc.

## Files to Create

### Backend

```
webapp-fx/
  backend/
    app.py                          -- FastAPI app (cloned from sister, stripped of company-code endpoints, new /upload accepting 3 inputs)
    config/
      account_mapping.json          -- Persisted account mapping (Account Number → Account Type + Monetary). Created on first save, survives restarts.
      exchange_rates.json           -- Persisted exchange rates (Currency → Rate). Created on first save, survives restarts.
    models/
      __init__.py
      schemas.py                    -- ProcessingRequest (adds account_mapping field), ProcessingResponse, JobStatus. Exchange rates come in as a file upload, parsed server-side into dict.
    services/
      __init__.py
      ctr_reader.py                 -- Shared CTR parsing layer, usable by any CTR-based output report. Validates the core CTR column set present in every Nakisa CTR export (Account Number, Account Name, Contract Currency, Amount in Contract Currency, Amount in Company Currency, Fiscal Year, Fiscal Period, Company Code, Transaction Type). Each processor defines its own required subset on top; ctr_reader.py rejects the file only if the core schema is missing. Metadata extraction from rows 1-26 is Excel-only; for CSV, metadata fields are returned as null with a user-facing warning.
      fx_processor.py               -- FX Remeasurement transformation layer. Consumes the clean DataFrame from ctr_reader.py, applies group + aggregate + account mapping + rate logic, writes multi-sheet workbook. Adding a future CTR-based report type means adding a new processor here — ctr_reader.py does not change.
      config_store.py               -- Read/write account_mapping.json and exchange_rates.json. Exposes load_account_mapping(), save_account_mapping(), load_exchange_rates(), save_exchange_rates(), reset_account_mapping(), reset_exchange_rates()
```

### Frontend

```
webapp-fx/
  frontend-vue/
    index.html
    vite.config.js
    package.json
    src/
      main.js                       -- Vue 3 app mount (no i18n plugin)
      App.vue                       -- View state machine: upload -> progress -> results -> error
      assets/
        styles.css                  -- Cloned from sister project, minor tweaks (no language selector positioning)
      components/
        AppHeader.vue               -- Title: "FX Remeasurement Tool", subtitle: "CTR Closing Balance Extraction & FX Gain/Loss Calculator"
        AppFooter.vue               -- Minimal footer (same as sister)
        UploadSection.vue           -- CTR file drag-and-drop (simplified, no company code cruft). Includes collapsible "Advanced" section for input_header_start / input_data_start overrides
        InputPanel.vue              -- NEW: account mapping table (pre-populated from saved config; new accounts blank) + exchange rates file upload (pre-populated from saved rates; re-upload to replace) + Reset buttons per section (calls DELETE /config/account-mapping or DELETE /config/exchange-rates)
        ProgressSection.vue         -- Reused as-is (progress bar + spinner)
        ResultsSection.vue          -- NEW: per-currency summary cards, warnings for unmapped accounts, download button
        ErrorSection.vue            -- Reused as-is (error display + retry)
```

## Files to Modify

None. This is a new standalone application in `webapp-fx/` alongside the existing `webapp/`.

## Key Design Decisions

### 1. Account Mapping Input: Editable table in UI (not a file upload)

**Why:** The account mapping is a small dataset (typically 5-30 unique GL accounts per client). A second file upload adds friction for a tiny payload. An inline editable table lets the user see the accounts extracted from the CTR and simply fill in Account Type and Monetary flag per row.

**How it works:**
- After CTR file upload, backend extracts unique `{Account Number, Account Name}` pairs and returns them in the `/upload` response alongside `saved_account_mapping` loaded from `config/account_mapping.json`
- Frontend renders an editable table in `InputPanel.vue` with columns: Account Number (read-only), Account Name (read-only), Account Type (dropdown: BS / P&L), Monetary (dropdown: Yes / No)
- Rows with saved mapping are pre-populated; rows for new accounts (not in saved config) appear with blank dropdowns
- User reviews/edits, then clicks "Process"
- Account mapping is sent as JSON in the process request body; on success, backend auto-saves to `config/account_mapping.json`
- A "Reset account mapping" button calls `DELETE /config/account-mapping` and clears the saved file, allowing the user to start fresh if a previous configuration was wrong

**Fallback:** If the user skips the mapping, columns 3-4 and 8-11 in the output are left blank with a warning banner. The aggregation (columns 1-2, 5-7) still works.

### 2. Exchange Rate Input: File upload (CSV or Excel)

**Why:** Clients like Abbott already maintain exchange rate tables in Excel/CSV as part of their period-end process. A file upload fits their existing workflow and avoids manual re-entry of rates each period.

**How it works:**
- `/upload` response includes `saved_exchange_rates` (loaded from `config/exchange_rates.json`). If rates are already saved, `InputPanel.vue` displays them as "Current rates: USD = 17.05, EUR = 18.50 …" with a "Re-upload to replace" option
- If no saved rates exist, the upload field is shown blank
- User uploads a new rates file (`.xlsx`, `.xls`, or `.csv`) to replace saved rates, or proceeds with saved rates (no new file needed)
- Expected format: two columns — `Currency` and `Rate` (e.g., `USD, 17.05`)
- Backend parses the file (if provided) and builds `{ "USD": 17.05, "EUR": 18.50, ... }` internally; on success, saves to `config/exchange_rates.json`
- Currency codes are matched case-insensitively against the CTR's Contract Currencies
- A "Reset exchange rates" button calls `DELETE /config/exchange-rates`, clearing the saved file so the user can re-upload correct rates

**Fallback:** If the user has no saved rates and skips the upload, columns 9-11 in the output are left blank with a warning listing which currencies have no rate supplied.

### 3. Upload Flow: Two-step (upload then configure then process)

The flow is:

```
[Step 1: Upload CTR]  -->  [Step 2: Configure & Process]  -->  [Progress]  -->  [Results]
     drag-and-drop           account mapping table                polling          download
                             exchange rates file upload
                             "Process" button
```

This is different from the sister project's single-step flow. The reason is that Step 2 depends on data extracted from the CTR in Step 1 (unique accounts, unique currencies, company currency from metadata).

**Backend endpoints:**
- `POST /upload` -- accepts CTR file as multipart, plus optional form fields `input_header_start` (default 27) and `input_data_start` (default 28) for configurable row positions (FR-005). Returns `UploadResponse` (see schema below) including `saved_account_mapping` (pre-populated from `config/account_mapping.json` if it exists) and `saved_exchange_rates` (pre-populated from `config/exchange_rates.json` if it exists). Synchronous, fast -- just reads, extracts, and loads saved config. The UI exposes `input_header_start` / `input_data_start` as a collapsible "Advanced" section in `UploadSection.vue`
- `POST /process/{job_id}` -- accepts multipart form: `account_mapping` as JSON + `rates_file` as file upload (`.xlsx`, `.xls`, `.csv`). Triggers background processing. On success, auto-saves `account_mapping` to `config/account_mapping.json` and parsed rates to `config/exchange_rates.json` (FR-025, FR-026).
- `GET /status/{job_id}` -- same polling pattern as sister project
- `GET /download/{job_id}` -- same download pattern. Download filename: `CTR_FX_Remeasurement_{FiscalYear}_{FiscalPeriod}_{Timestamp}.xlsx`. Note: `fiscal_year` and `fiscal_period` must be persisted in job state from the upload step for use in the download filename
- `DELETE /config/account-mapping` -- clears `config/account_mapping.json`; returns 204. Used by the Reset button in `InputPanel.vue` (FR-027)
- `DELETE /config/exchange-rates` -- clears `config/exchange_rates.json`; returns 204. Used by the Reset button in `InputPanel.vue` (FR-027)

This splits the sister project's single `/upload` endpoint into two steps: upload (extract) and process (compute). The status polling and download remain identical.

**`/upload` Response Schema (Pydantic model in `schemas.py`):**

```python
class AccountInfo(BaseModel):
    account_number: str
    account_name: str

class AccountMappingEntry(BaseModel):
    account_number: str
    account_type: str | None   # "BS" | "P&L" | None if not yet mapped
    monetary: str | None       # "Yes" | "No" | None if not yet mapped

class UploadMetadata(BaseModel):
    fiscal_year: str | None
    fiscal_period: str | None
    accounting_standard: str | None
    company_code: str | None

class UploadResponse(BaseModel):
    job_id: str
    accounts: list[AccountInfo]
    currencies: list[str]
    company_currency: str | None
    metadata: UploadMetadata
    saved_account_mapping: list[AccountMappingEntry]  # pre-populated from config/account_mapping.json; empty list if no saved config
    saved_exchange_rates: dict[str, float]            # pre-populated from config/exchange_rates.json; empty dict if no saved config
```

**`/process/{job_id}` Validation:** Returns 404 if job not found. Returns 409 if job is already processing or completed.

**Error Response Structure (FR-019):**

The sister project's simple `error: str` in `JobStatus` is replaced with a structured error object to support specific, actionable error messages:

```python
class ErrorDetail(BaseModel):
    row: int
    column: str
    value: str
    reason: str

class ErrorResponse(BaseModel):
    type: str          # e.g. "missing_columns", "insufficient_rows", "currency_parse", "invalid_numeric"
    message: str       # human-readable summary
    details: list[ErrorDetail]  # per-cell details (empty list if not applicable)
```

`JobStatus.error` uses `ErrorResponse | None` instead of `str | None`.

### 4. Output: Single `.xlsx` file (not ZIP)

Unlike the sister project which generates one file per company code and ZIPs them, this tool produces a single workbook with one worksheet per currency. No ZIP needed in Phase 1.

### 5. Drop `template_header_start` / `template_data_start` from sister project

The sister project's `ProcessingRequest` includes `template_header_start` and `template_data_start` for configurable output formatting. These are NOT carried over -- the FX tool's output format is fixed (headers in row 1, data from row 2) per FR-013.

### 6. No i18n

Per FR-020, English only. Remove `vue-i18n` dependency entirely. All strings are hardcoded in templates. This eliminates the `i18n/` directory, locale JSON files, `LanguageSelector.vue`, and `useI18n()` calls.

## Data Flow

```
                                          +---------------------+
                                          |  User's Browser     |
                                          |                     |
                                          |  1. Upload CTR file |
                                          |     (drag & drop)   |
                                          +--------+------------+
                                                   |
                                          POST /upload (multipart)
                                                   |
                                                   v
                                     +-------------+-------------+
                                     |  FastAPI Backend           |
                                     |                           |
                                     |  ctr_reader.py:           |
                                     |    - Parse metadata 1-26  |
                                     |    - Read headers row 27  |
                                     |    - Validate core CTR    |
                                     |      columns (shared set) |
                                     |    - Extract unique       |
                                     |      accounts & currencies|
                                     +-------------+-------------+
                                                   |
                              Response: { accounts[], currencies[], company_currency }
                                                   |
                                                   v
                                          +--------+------------+
                                          |  InputPanel.vue      |
                                          |                     |
                                          |  2. User fills in:  |
                                          |   - Account Type    |
                                          |     (BS/P&L) per GL |
                                          |   - Monetary flag   |
                                          |     (Yes/No) per GL |
                                          |   - Spot rate per   |
                                          |     currency pair   |
                                          +--------+------------+
                                                   |
                                    POST /process/{job_id} (multipart form)
                                                   |
                                                   v
                                     +-------------+-------------+
                                     |  fx_processor.py (bg task)|
                                     |                           |
                                     |  - Group by {AcctNum,     |
                                     |    AcctName, Currency}    |
                                     |  - Sum contract & company |
                                     |    currency amounts       |
                                     |  - Join account mapping   |
                                     |  - Apply exchange rates   |
                                     |  - Calc remeasured bal    |
                                     |  - Calc FX gain/loss      |
                                     |  - Write .xlsx (1 sheet   |
                                     |    per currency)          |
                                     +-------------+-------------+
                                                   |
                                      GET /status/{job_id} (poll)
                                                   |
                                                   v
                                          +--------+------------+
                                          |  ResultsSection.vue  |
                                          |                     |
                                          |  3. Summary:        |
                                          |   - Rows per ccy    |
                                          |   - Warnings for    |
                                          |     unmapped accts  |
                                          |   - Download .xlsx  |
                                          +---------------------+
```

### Output Excel Structure (per worksheet, one per currency)

Rows within each worksheet are sorted by Account Number ascending (FR-010).

| Col | Header | Source |
|-----|--------|--------|
| 1 | Account Number | CTR grouping key |
| 2 | Account Name | CTR grouping key (first occurrence) |
| 3 | Account Type | User-supplied mapping (BS / P&L) |
| 4 | Monetary? | User-supplied mapping (Yes / No) |
| 5 | Account Currency | CTR Contract Currency (worksheet name) |
| 6 | Balance in Contract Currency | SUM(Amount in Contract Currency) per group |
| 7 | Initial Measurement Company Currency Balance | SUM(Amount in Company Currency) per group |
| 8 | Rate | "Historical" if non-monetary, "Period End" if monetary |
| 9 | Period-End Spot Exchange Rate | User-supplied rate for this currency |
| 10 | Re-measured Balance | col6 * col9 (monetary) or col7 (non-monetary) |
| 11 | FX (Gain) or Loss | col10 - col7 |

**Number Formatting:** Numeric output columns (6, 7, 9, 10, 11) use at least 2 decimal places formatting, consistent with the sister project's `CELL_NUMBER_FORMAT` pattern (FR-014).

### Data Quality Handling (FR-011)

- **Missing Account Name:** If Account Name is null or empty in the source data, it defaults to "—"
- **Conflicting Account Names:** When the same Account Number appears with different Account Names across CTR rows, the first occurrence is used and a warning is logged

### Unmapped Account Handling

Accounts present in the CTR but missing from the user-supplied mapping:
- Columns 1-2, 5-7 are populated (aggregation works regardless)
- Columns 3-4 show "N/A"
- Columns 8-11 are left blank
- A warning appears in the results view listing the unmapped accounts
- The output Excel includes these rows so the user can see what was missed

---

**Document Status:** Draft
**Last Updated:** 2026-03-20
