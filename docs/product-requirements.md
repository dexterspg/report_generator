# Product Requirements: CTR Closing Balance Extraction for FX Remeasurement

**Ticket:** LAE-44136 (Abbott Laboratories)
**Priority:** High
**Project Size:** Mini
**Status:** New Feature Definition
**Created:** 2026-03-19

---

## 1. Problem Statement

Multi-currency lease portfolio clients (e.g., Abbott Laboratories) need to know the **FX (Gain) or Loss** on each GL account at period end — the discrepancy between the initial company currency balance (recorded at historical rates) and the re-measured balance (at the current period-end exchange rate). This number is what drives the FX adjustment journal entry.

Today, getting to that number is entirely manual:

**Current State:**
1. Client exports a Consolidated Transaction Report (CTR) from Nakisa Lease Administration
2. Client manually pivots the CTR in Excel to aggregate closing balances by GL account and currency
3. Client manually applies period-end exchange rates to re-measure each account
4. Client manually calculates the FX gain/loss per account (re-measured balance minus initial measurement)
5. This is repeated every fiscal period (quarterly or monthly)

**The core problem is step 4** — but steps 2-3 must be done first to get there, and each step compounds the risk of error.

**Pain Points:**
- **High-stakes errors:** Manual FX gain/loss calculation directly affects financial statements; a mistake means material FX misstatement (IFRS 16 & GAAP)
- **Error-prone aggregation:** Manual pivoting and summing across hundreds of CTR rows introduces calculation errors before the FX math even begins
- **Repetitive:** The entire 4-step process is repeated every fiscal period for every multi-currency client
- **No auditability:** Manual Excel work is hard to verify and audit

**Impact of Not Solving:**
- Risk of incorrect FX adjustment journal entries
- Delayed period-end closing and financial reporting
- Consultant resource burnout on routine manual tasks

---

## 2. User Stories

### Phase 1 (This Ticket) — FX Gain/Loss Calculation

**US-01 — Automatic FX Gain/Loss per GL Account**
- **As a** client accountant
- **I want to** upload a CTR file and receive the FX (Gain) or Loss for each GL account — the discrepancy between the initial company currency balance and the re-measured balance at the period-end exchange rate
- **So that** I can book the correct FX adjustment journal entry without manual calculation
- **Priority:** P0 (must) — this is the primary deliverable

**US-02 — Closing Balance Aggregation by Account and Currency**
- **As a** client accountant or implementation consultant
- **I want to** see closing balances grouped by GL account and currency (contract currency balance + initial company currency balance)
- **So that** the aggregation feeding the FX gain/loss calculation is transparent and auditable
- **Priority:** P0 (must) — prerequisite for US-01

**US-03 — Supply Period-End Exchange Rates and Account Classification**
- **As a** client accountant
- **I want to** upload a rates file (CSV or Excel) with period-end spot exchange rates, and indicate which accounts are monetary vs. non-monetary
- **So that** the system can apply the correct rate to re-measure each account
- **Priority:** P0 (must) — required input for the FX calculation

**US-04 — Multi-Sheet Output by Currency**
- **As a** client accountant
- **I want to** receive one worksheet per contract currency containing grouped accounts with their FX gain/loss
- **So that** I can navigate currency-specific results efficiently
- **Priority:** P0 (must)

**US-05 — Standalone Desktop Application**
- **As a** client accountant or implementation consultant
- **I want to** use a standalone desktop application (distributed as a single `.exe` file) with a simple configure-upload-process-download workflow
- **So that** I can process CTR files on my own laptop without needing a server, internet access, or additional tools
- **Priority:** P0 (must)

**US-08 — Shareable Configuration Files**
- **As a** team member sharing the tool with colleagues
- **I want to** download my account mapping and exchange rates as Excel files and share them with other users who can upload them into their own copy of the application
- **So that** teams can maintain consistent configuration across multiple desktops without a shared server
- **Priority:** P0 (must)

**US-09 — Configuration History and Rollback**
- **As a** client accountant
- **I want to** view a history of all configuration changes (uploads, resets) as a read-only audit trail
- **So that** I can see what config changes were made and when. Recovery from a bad upload is done by downloading the current config, editing in Excel, and re-uploading with Replace mode
- **Priority:** P0 (must)

### Phase 2 (Future) — Multi-Period & Exclusions

**US-06 — Prior Period FX Adjustment Carryforward**
- **As a** client accountant in period 2+
- **I want to** optionally supply a prior period's FX adjustment balance
- **So that** I can accurately track cumulative FX impacts across the fiscal year
- **Priority:** P1 (should) — Phase 2

**US-07 — Exclude P&L Accounts from Remeasurement**
- **As a** client accountant
- **I want to** automatically exclude P&L accounts (Interest, Depreciation, etc.) from the FX remeasurement calculation
- **So that** we only remeasure Balance Sheet accounts (per IFRS 16)
- **Priority:** P1 (should) — Phase 2

---

## 3. Functional Requirements

### Input Specification

**FR-001:** The system shall accept Excel (`.xlsx`, `.xls`) or CSV (`.csv`) files matching the CTR export format from Nakisa Lease Administration.

**FR-002:** The system shall extract metadata from rows 1-26 of the input file, including but not limited to:
- Fiscal Year
- Fiscal Period
- Accounting Standard (IFRS / GAAP)
- Contract Currency
- Company Currency
- Company Code

**FR-003:** The system shall read column headers from row 27 and identify required columns:
- Account Number
- Account Name
- Contract Currency
- Amount in Contract Currency
- Amount in Company Currency
- Company Code
- Transaction Type (optional in Phase 1)
- Fiscal Year
- Fiscal Period

**FR-004:** The system shall detect and report mismatches if required columns are absent; processing shall not proceed.

**FR-005:** The system shall allow users to configure header and data row start positions (advanced/optional), with defaults:
- Header start row: 27
- Data start row: 28

### Processing Logic

**FR-006:** The system shall group input records by {Contract ID, Account Number, Account Name, Contract Currency} and aggregate:
- Sum of Amount in Contract Currency → "Balance in Contract Currency"
- Sum of Amount in Company Currency → "Initial Measurement Company Currency Balance"

**FR-007:** The system shall create one output worksheet per unique Contract Currency found in the input, named by currency code (e.g., "USD", "EUR", "GBP").

**FR-008:** The system shall output the following columns:
1. Contract ID — from CTR grouping key
2. Account Number
3. Account Name
4. Account Type — from user-supplied account mapping
5. Monetary? — from user-supplied account mapping (Monetary/Non-Monetary)
6. Account Currency
7. Balance in Contract Currency — aggregated from CTR
8. Initial Measurement Company Currency Balance — aggregated from CTR
9. Rate — from user-supplied account mapping (Historical or Period End)
10. Period-End Spot Exchange Rate — from user-supplied exchange rates (matched by FromCurrency → contract currency and ToCurrency → company currency)
11. Re-measured Balance — col7 × col10 for monetary accounts, or = col8 for non-monetary accounts
12. FX (Gain) or Loss — col11 − col8 (the primary deliverable)

**FR-009:** The system shall accept two configuration inputs, both supplied as file uploads (`.xlsx`, `.xls`, or `.csv`):
- **Account mapping** — maps Account Number to Account Type, Monetary classification, and Rate method. Uploaded as a file with columns: `Account Number`, `Account Type`, `Monetary?`, `Rate`. The Rate column specifies whether the account uses "Historical" or "Period End" rates. Supports two upload modes: **Replace** (clear existing, load from file) and **Merge** (add new entries, update existing entries with the same Account Number). The current mapping can be downloaded as an Excel file for sharing with other users. A Reset button clears all saved mapping data.
- **Period-end exchange rates** — spot rates per currency pair. Uploaded as a file with columns: `RateType`, `FromCurrency`, `ToCurrency`, `ValidFrom`, `ExchangeRate`. The system matches `FromCurrency` to the account's contract currency and `ToCurrency` to the company currency to find the correct spot rate. Duplicate detection uses the composite key `{FromCurrency, ToCurrency, ValidFrom}`. Supports the same **Replace** and **Merge** upload modes. The current rates can be downloaded as an Excel file for sharing. A Reset button clears all saved rate data.

Both configuration files are independent of the CTR report — they can be uploaded, downloaded, shared, and managed before any CTR file is processed.

**FR-010:** The system shall sort output rows by Account Number (ascending) within each worksheet.

**FR-011:** The system shall handle duplicate or missing Account Names gracefully; if a name is missing, it shall be left blank or default to "—" (dash).

### Output Specification

**FR-012:** The system shall generate an Excel workbook (`.xlsx`) with one or more worksheets (one per currency).

**FR-013:** Each worksheet shall include:
- A header row containing all 12 columns (Contract ID through FX Gain/Loss)
- Data rows starting immediately after headers (row 2)
- No metadata or non-tabular content in the output sheet

**FR-014:** The system shall preserve exact numeric precision for all currency amounts and exchange rates. No rounding, truncation, or float conversion at any stage — what the user uploads is exactly what appears in the output. All arithmetic uses exact decimal computation.

**FR-015:** The output file shall be named with a pattern: `CTR_FX_Remeasurement_{FiscalYear}_{FiscalPeriod}_{Timestamp}.xlsx`. For CSV inputs where fiscal year/period metadata is unavailable, the pattern shall fall back to `CTR_FX_Remeasurement_Unknown_Unknown_{Timestamp}.xlsx`.

### User Interface

**FR-016:** The system shall be a standalone desktop application dedicated to FX Remeasurement processing, distributed as a single `.exe` file built with PyInstaller. It is independent from the existing Poliza Ledger (CTR Mapper) application.

**FR-017:** The application shall follow a two-step configure-then-process workflow:
- **Step 1 — Configuration:** User manages two configuration files (account mapping and exchange rates) via upload, download, replace, merge, and reset operations. Each config shows a preview table of the current saved data. Configs persist locally and are available across sessions.
- **Step 2 — Upload & Process:** User uploads the CTR report file. The Process button is disabled until both configurations are loaded. Processing runs asynchronously with job ID and status polling.
- **Results:** Upon completion, the results view shows the source filename, fiscal year/period, processing time, summary stats (input rows, output rows, currencies), and a download button. No detailed output table or warnings are displayed in the UI — the full output is in the downloaded Excel file.

**FR-018:** The application shall support both desktop mode (primary — single-user, `localhost:5001`, auto-opens browser) and web mode (secondary — multi-user server, `0.0.0.0:8000`). Desktop mode is the primary deployment target.

**FR-019:** Error messages shall be specific and actionable:
- Missing required columns (list which)
- Insufficient data rows (count)
- Currency parsing errors (show examples)
- Invalid numeric values (row and column reference)

**FR-020:** The system shall support English only. No i18n or multi-language support is required.

### Data Validation

**FR-021:** The system shall validate that Account Number and Contract Currency are non-empty for each data row; rows missing either shall be logged and skipped with a warning.

**FR-022:** The system shall validate that Amount in Contract Currency and Amount in Company Currency are numeric; if non-numeric, the row shall be logged and skipped, and processing shall continue.

**FR-023:** The system shall enforce a maximum input file size of 50 MB (matching existing policy).

**FR-024:** The system shall validate the input file is a valid Excel or CSV format; malformed files shall be rejected with a clear error message. For CSV files, the system shall auto-detect the header row or assume row 1 as headers (no metadata rows).

### Configuration Persistence & Storage

**FR-025:** The system shall persist configuration data (account mapping, exchange rates, history) to the local filesystem:
- **Desktop mode (PyInstaller `.exe`):** `%LOCALAPPDATA%/CTR-FX-Remeasurement/` — per-user, no admin rights required, survives `.exe` updates.
- **Development mode:** `webapp/backend/` directory.
- Internal storage format is JSON. Users interact with configs via Excel/CSV file upload and download — they never touch JSON files directly.

**FR-026:** The system shall support two upload modes for both configuration files:
- **Replace** — clear all existing entries and load entirely from the uploaded file.
- **Merge** — add new entries from the uploaded file; update existing entries that share the same key (Account Number for mapping, Currency for rates).

**FR-027:** The system shall provide reset and download capabilities for each configuration:
- **Reset** clears all saved data for the selected configuration, reverting to blank/empty state.
- **Download** exports the current saved configuration as a styled Excel file (`.xlsx`) for sharing with other users of the application.

### Configuration History & Rollback

**FR-028:** The system shall automatically record a history entry for every configuration change (upload, reset). Each history entry shall include:
- Timestamp, action type, config type affected, source filename (if applicable)
- A full snapshot of both configuration files at the time of the action

**FR-029:** The system shall display the history of configuration changes as a read-only audit table (most recent first) with columns: Timestamp, Action, Config, Details. The table shall be limited to the most recent 50 entries to prevent page overflow. A "Clear History" button shall delete all history entries. No rollback capability in Phase 1 — recovery from bad uploads is done by downloading the config, editing in Excel, and re-uploading with Replace mode. Rollback (restore from snapshot) is a Phase 2 feature.

**FR-030:** History data shall be stored locally alongside configuration data (same `%LOCALAPPDATA%` path for desktop, same backend directory for dev).

---

## 4. Non-Functional Requirements

**NFR-001 — Performance:**
- Processing shall complete within 10 seconds for files up to 50,000 data rows
- Memory usage shall not exceed 500 MB for standard use cases
- File I/O shall be optimized using vectorized operations (pandas)

**NFR-002 — Housekeeping:**
- Temporary files shall be cleaned up automatically after 1 hour
- Concurrency is inherited from FastAPI's default handling (sufficient for small-team usage)

**NFR-003 — Reliability:**
- Processing failures shall not corrupt the input file or affect concurrent jobs
- Job status is ephemeral (in-memory) and not persisted across application restarts
- Configuration (account mapping, exchange rates, history) is persisted to local JSON files in `%LOCALAPPDATA%/CTR-FX-Remeasurement/` (desktop) and survives application restarts and `.exe` updates

**NFR-004 — Security:**
- File uploads shall be restricted to `.xlsx`, `.xls`, and `.csv` formats
- Uploaded files shall be stored in a temporary location and deleted after processing
- No client data shall be logged or persisted beyond the processing session

---

## 5. Acceptance Criteria

### US-01: FX Gain/Loss per GL Account

**Given** a CTR file, account mapping, and period-end exchange rates
**When** the user uploads and processes the file
**Then** column 11 (FX Gain or Loss) shall show the discrepancy between the initial company currency balance and the re-measured balance for each GL account

**Given** a monetary account with Balance in Contract Currency = 10,000 USD, Initial Measurement = 130,000 MXN, and period-end spot rate = 14.0
**When** processed
**Then** Re-measured Balance = 140,000 MXN and FX (Gain) or Loss = 10,000 MXN

**Given** a non-monetary account
**When** processed
**Then** Re-measured Balance = Initial Measurement (historical rate preserved) and FX (Gain) or Loss = 0

### US-02: Closing Balance Aggregation

**Given** a CTR file with duplicate account entries across rows
**When** processed
**Then** the system shall correctly sum all amounts for each {Account Number, Account Name, Contract Currency} group

**Given** amounts with decimal values (e.g., 1234.56)
**When** aggregated and displayed in output
**Then** precision shall be preserved exactly — no rounding or truncation

### US-03: Exchange Rate and Account Classification Input

**Given** the application
**When** the user uploads a CTR file
**Then** the system shall also accept account mapping (Account Type + Monetary flag) and period-end exchange rates as inputs

**Given** an account that appears in the CTR but is missing from the account mapping
**When** processed
**Then** the system shall flag it in the output; columns 4-5 (Account Type, Monetary?) shall show "N/A" and columns 9-12 (Rate, Spot Rate, Re-measured Balance, FX Gain/Loss) shall be left blank for that account

### US-04: Multi-Sheet Output by Currency

**Given** a CTR with transactions in USD, EUR, and GBP
**When** processed
**Then** the output workbook shall contain exactly 3 worksheets named "USD", "EUR", "GBP"

**Given** a worksheet in the output
**When** opened in Excel
**Then** all rows shall be sorted by Account Number in ascending order

### US-05: Standalone Web Application

**Given** the FX Remeasurement application is loaded
**When** the user views the main page
**Then** an upload area for CTR files shall be visible with a clear "FX Remeasurement" title

**Given** the application is deployed
**When** accessed in web mode or desktop mode
**Then** the full upload-process-download workflow shall function identically in both modes

### Verification Against Provided Data

**Given** the test file `CTR_0422.xlsx` with 7 unique accounts
**When** processed
**Then** the output grouping and FX gain/loss shall be verifiable by the Abbott implementation team

**Given** Abbott's test data from period P1
**When** processed
**Then** the output shall match the existing "3. CTR Pivot P1" sheet manually created by Abbott

---

## 6. Edge Cases & Error Handling

**EC-001 — Empty or Minimal Input:**
- File with headers but no data rows → Return an empty workbook with headers only; display info message "No data rows found."
- File missing all required columns → Reject with specific list of missing columns.

**EC-002 — Malformed Data:**
- Account Number is empty but Contract Currency is present → Skip the row; log warning.
- Amount in Contract Currency is text (e.g., "N/A") → Skip the row; log warning including row number.
- Contract Currency contains spaces or special characters → Normalize to uppercase; warn if non-standard code (e.g., "U SD" → error).

**EC-003 — Large Files:**
- File with >50,000 data rows → Accept and process normally; pandas handles this volume in memory.
- File with >100 unique currencies → Accept; create 100+ worksheets.

**EC-004 — Duplicate Accounts:**
- Two rows with same Account Number, same Contract Currency, different Account Name → Use first occurrence's name; log warning about name mismatch.
- Multiple different Account Names for the same Account Number → Highlight in output or log for data quality review.

**EC-005 — Negative or Zero Balances:**
- Accept negative balances (represent liabilities or reversals); no special handling.
- Accept zero balances; include in output.

**EC-006 — Currency Code Parsing:**
- Non-standard currency codes (e.g., "XXX", "ZZZ") → Accept and create worksheet; warn user of non-standard code.
- Case sensitivity (e.g., "usd" vs "USD") → Normalize to uppercase; worksheet name shall be "USD".

**EC-007 — Special Characters in Account Names:**
- Account Name with quotes, slashes, or special characters (e.g., "A/R - Interco") → Include in output as-is; no sanitization needed for Excel.

**EC-008 — Round-Tripping:**
- User downloads FX Remeasurement output and re-uploads it as input → System shall either reject with clear message or handle gracefully (not a priority for Phase 1).

---

## 7. Phase 1 Scope (This Ticket)

### In Scope
- Parse CTR metadata (rows 1-26) and extract key fields
- Identify and validate required columns
- Group data by {Account Number, Account Name, Contract Currency}
- Aggregate Amount in Contract Currency and Amount in Company Currency
- Accept account mapping as file upload (CSV/Excel) with Replace/Merge modes
- Accept period-end exchange rates as file upload (CSV/Excel) with Replace/Merge modes
- Download current configs as Excel files for sharing between desktop users
- Reset (Clear All) buttons to clear saved configs
- Download output Excel file (FX Gain/Loss results) — `CTR_FX_Remeasurement_{FY}_{FP}_{Timestamp}.xlsx`
- Apply rate logic based on the Rate column in account mapping (Historical or Period End)
- Look up spot exchange rate by matching FromCurrency → contract currency and ToCurrency → company currency
- Calculate Re-measured Balance (col7 × spot rate for Period End accounts, = col8 for Historical accounts)
- **Calculate FX (Gain) or Loss per account (col11 − col8) — the primary deliverable**
- Create one worksheet per unique currency with all 12 columns populated (including Contract ID)
- Sort by Account Number
- Build standalone desktop application (`.exe` via PyInstaller) with upload-process-download workflow
- Local data storage in `%LOCALAPPDATA%/CTR-FX-Remeasurement/` (no admin rights, survives updates)
- Follow same architectural pattern as existing CTR Mapper (FastAPI + Vue.js)
- Support both desktop (primary) and web (secondary) modes
- English-only interface

### Out of Scope (Phase 2+)
- Configuration preview tables (view current account mapping and exchange rates as data tables)
- Rollback capability (restore config from history snapshot via UI or API)
- Prior period FX adjustment carryforward
- P&L account exclusion logic (auto-filtering Interest, Depreciation, etc.)
- Multi-company output (separate files per company)
- Database persistence of historical results

---

## 8. Data Sources & Dependencies

### Input Files
- **Nakisa Lease Administration CTR Export** (Excel format)
  - Standard structure: metadata rows 1-26, headers row 27, data rows 28+
  - Client provides via manual export

### Additional Inputs (Phase 1) — Configuration Files
- **Account mapping** — Account Type, Monetary classification, and Rate method per GL account. Uploaded as CSV or Excel file with columns: `Account Number`, `Account Type`, `Monetary?`, `Rate`. Supports Replace and Merge upload modes. Downloadable as Excel for sharing.
- **Period-end exchange rates** — spot rates per currency pair. Uploaded as CSV or Excel file with columns: `RateType`, `FromCurrency`, `ToCurrency`, `ValidFrom`, `ExchangeRate`. Duplicate detection uses composite key `{FromCurrency, ToCurrency, ValidFrom}`. The system matches `FromCurrency` to the contract currency and `ToCurrency` to the company currency. Supports Replace and Merge upload modes. Downloadable as Excel for sharing.

### Local Configuration Storage
- **Account mapping config** — stored in SQLite at `%LOCALAPPDATA%/CTR-FX-Remeasurement/ctr_fx.db`; updated on every upload, merge, or reset; survives application restarts and `.exe` updates.
- **Exchange rates config** — JSON file in same location; same lifecycle.
- **Configuration history** — JSON files in `%LOCALAPPDATA%/CTR-FX-Remeasurement/history/`; one file per history entry; includes full snapshots of both configs at time of action.

### Additional Inputs (Phase 2)
- Prior period FX adjustments — source TBD

### Test Data
- `CTR_0422.xlsx` — 7 unique accounts, provided for validation
- Abbott period P1 data — expected to match manual "3. CTR Pivot P1" sheet

---

## 9. Success Metrics

**Functional Success:**
- FX (Gain) or Loss values match manually verified calculations (Abbott P1)
- All 11 columns populated in output for accounts with mapping data
- Standalone application loads and presents clear FX Remeasurement workflow
- Error messages are clear and actionable

**Performance Success:**
- Files up to 50,000 rows process in <10 seconds
- No memory leaks or crashes on concurrent uploads

**Adoption Success:**
- Client (Abbott) validates output and approves for production use
- Implementation consultants report reduced manual work time

**Quality Success:**
- Zero FX gain/loss calculation errors in Phase 1 (only balance aggregation)
- <2% data skipping rate due to validation errors in typical clients
- Application works in both web and desktop modes

---

## 10. Constraints & Assumptions

### Constraints
- **File Format:** Input must be Excel (`.xlsx`, `.xls`) or CSV (`.csv`)
- **Row Structure:** CTR structure must match Nakisa standard (metadata in 1-26, headers at 27, data from 28)
- **No Database:** Job data stored in-memory; not persisted across application restarts. Configuration data (account mapping, exchange rates, history) is persisted as local JSON files in `%LOCALAPPDATA%/CTR-FX-Remeasurement/` — no relational database required.
- **No Authentication:** Same security model as existing application (no auth/authz layer)
- **Currency Codes:** 3-letter ISO currency codes expected (USD, EUR, GBP, etc.)

### Assumptions
- Users understand their CTR structure and can identify metadata rows
- All GL accounts within the same currency have the same Company Currency equivalent rate
- Fiscal Year and Fiscal Period in metadata are consistent with data rows
- Amount fields are consistently formatted (no mixed currencies in a single column)
- Test data (CTR_0422.xlsx, Abbott P1) accurately represents production use cases
- FX rate logic and account classification rules will be supplied by clients as input

---

## 11. Future Roadmap

### Phase 2: Multi-Period & Exclusions
- Support optional prior period FX adjustment input
- Exclude P&L accounts from remeasurement automatically
- Cumulative FX balance tracking
- Multi-company file output (ZIP with one file per company code)
- Audit trail and calculation transparency (e.g., formula audit table)
- Configuration preview tables with single-row delete/edit capability (Phase 1 workaround: download, edit in Excel, re-upload with Replace)
- Rollback UI button in history view
- Downloadable error log

### Beyond Phase 2: Integration & Automation
- Direct API integration with Nakisa to fetch CTR automatically
- Batch processing for multiple periods
- Scheduled remeasurement runs
- Integration with accounting systems (SAP, NetSuite, etc.) for journal entry generation
- Historical trend analysis and variance reporting

---

## 12. Approval & Sign-Off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| Product Manager | — | — | — |
| Implementation Consultant (Account) | — | — | — |
| Client (Abbott Laboratories) | — | — | — |
| Technical Lead | — | — | — |

---

**Document Status:** Draft
**Last Updated:** 2026-03-24
**Next Review:** Upon implementation kickoff
