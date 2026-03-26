# Product Requirements: CTR Closing Balance Extraction for FX Remeasurement

**Ticket:** LAE-44136
**Pilot Client:** Abbott Laboratories
**Priority:** High
**Project Size:** Standard
**Status:** New Feature Definition
**Created:** 2026-03-19

---

## 1. Problem Statement

Multi-currency lease portfolio clients — clients whose lease contracts are denominated in one or more currencies different from their company (reporting) currency — need to know the **FX (Gain) or Loss** on each GL account at period end — the discrepancy between the initial company currency balance (recorded at historical rates) and the re-measured balance (at the current period-end exchange rate). This number is what drives the FX adjustment journal entry.

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

This tool is designed to be reusable across any multi-currency client. Abbott Laboratories is the first client and serves as the pilot for validation.

**Impact of Not Solving:**
- Risk of incorrect FX adjustment journal entries
- Delayed period-end closing and financial reporting
- Consultant resource burnout on routine manual tasks

---

## 2. User Stories

### Phase 1 (This Ticket) — FX Gain/Loss Calculation

**US-01 — Automatic FX Gain/Loss per GL Account**
- **As a** client accountant
- **I want to** upload a CTR file (after configuring account mapping and exchange rates), process it, and download an Excel file with FX (Gain) or Loss calculated for each GL account — the discrepancy between the initial company currency balance and the re-measured balance at the period-end exchange rate
- **So that** I can book the correct FX adjustment journal entry without manual calculation
- **Priority:** P0 (must) — this is the primary deliverable

**US-02 — Closing Balance Aggregation by Contract, Account, and Currency**
- **As a** client accountant
- **I want to** have closing balances grouped by Contract ID, account number, account name, and contract currency (contract currency balance + initial company currency balance) included in the output Excel file
- **So that** the aggregation feeding the FX gain/loss calculation is transparent and auditable per contract
- **Priority:** P0 (must) — prerequisite for US-01 after US-03 and US-04 are complete *(See Open Questions — OQ-001)*

**US-03 — Account Mapping Configuration**
- **As a** client accountant or implementation consultant
- **I want to** upload an account mapping file (CSV or Excel) that specifies Account Type, Monetary classification, and Rate method (Historical or Period End) for each GL account, and manage this configuration via Replace/Merge upload modes, download, and Clear All
- **So that** the system can apply the correct remeasurement logic and FX calculation treatment to each account during CTR processing
- **Priority:** P0 (must) — required input for FX calculation

**US-04 — Exchange Rates Configuration**
- **As a** client accountant or implementation consultant
- **I want to** upload an exchange rates file (CSV or Excel) with period-end spot rates for each currency pair, and manage this configuration via Replace/Merge upload modes, download, and Clear All
- **So that** the system can apply the correct period-end exchange rate to re-measure each account's balance during FX remeasurement
- **Priority:** P0 (must) — required input for FX calculation

**US-05 — Multi-Sheet Output by Currency**
- **As a** client accountant
- **I want to** receive one worksheet per contract currency containing grouped accounts with their FX gain/loss
- **So that** I can navigate currency-specific results efficiently
- **Priority:** P0 (must)

**US-06 — Standalone Desktop Application with Multi-Step Workflow**
- **As a** client accountant or implementation consultant
- **I want to** use a standalone desktop application (distributed as a single `.exe` file) with three accessible sections (Process CTR, Configuration, Audit History) navigable via sidebar
- **So that** I can configure accounts and rates, upload CTR files, and track all changes on my own laptop without needing a server, internet access, or additional tools
- **Priority:** P0 (must)

**US-07 — Shareable Configuration Files**
- **As a** client accountant or implementation consultant
- **I want to** download my account mapping and exchange rates as Excel files and share them with other team members who can upload them into their own copy of the application
- **So that** teams can maintain consistent configuration across multiple desktops without a shared server
- **Priority:** P0 (must)

**US-08 — Configuration History (Audit Trail)**
- **As a** client accountant
- **I want to** view a read-only history of all configuration changes (uploads, Clear All actions) and clear it when needed
- **So that** I have a transparent audit trail of what config changes were made and when
- **Priority:** P0 (must)

**US-09 — Processing Error Display and Retry**
- **As a** client accountant
- **I want to** see specific, actionable error messages when CTR processing fails (missing columns, invalid data, etc.) and retry the upload with a corrected file
- **So that** I can quickly understand what went wrong and fix the issue without re-entering configuration
- **Priority:** P1 (should) — Phase 1

### Phase 2 (Future) — Multi-Period & Exclusions

**US-10 — Prior Period FX Adjustment Carryforward**
- **As a** client accountant in period 2+
- **I want to** optionally supply a prior period's FX adjustment balance
- **So that** I can accurately track cumulative FX impacts across the fiscal year
- **Priority:** P1 (should) — Phase 2

**US-11 — Exclude P&L Accounts from Remeasurement**
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
- Start Date
- End Date
- Accounting Standard (IFRS / GAAP)
- Contract Currency
- Company Currency
- Company

*Metadata extraction applies to Excel files only (`.xlsx`, `.xls`). For CSV files, metadata fields are not available and shall default to `Unknown`.*

**FR-003:** The system shall read column headers from row 27 and identify the following columns:

**Required (10 columns):**
- Contract ID
- Account Number
- Account Name
- Contract Currency
- Company Currency
- Amount in Contract Currency
- Amount in Company Currency
- Company
- Fiscal Year
- Fiscal Period

**Optional (1 column):**
- Transaction Type (not used in Phase 1 processing)

**FR-004:** The system shall detect and report mismatches if required columns are absent; processing shall not proceed.

### Processing Logic

**FR-005:** The system shall group input records by {Contract ID, Account Number, Account Name, Contract Currency} and aggregate:
- Sum of Amount in Contract Currency → "Balance in Contract Currency"
- Sum of Amount in Company Currency → "Initial Measurement Company Currency Balance"

*(See Open Questions — OQ-001)*

**FR-006:** The system shall create one output worksheet per unique Contract Currency found in the input, named by currency code (e.g., "USD", "EUR", "GBP").

**FR-030:** The system shall normalize currency code fields by extracting the 3-letter ISO code from values in the format `"{CODE} - {Description}"` — taking all characters before the first `" - "` separator and converting to uppercase. This applies to both Contract Currency and Company Currency fields from the CTR input. If the value does not contain `" - "`, the full value shall be used as-is (assumed to already be a 3-letter code).

Examples:
- `"USD - United States Dollar"` → `"USD"`
- `"CAD - Canadian Dollar"` → `"CAD"`
- `"EUR"` → `"EUR"` (no change)

**FR-007:** The system shall output the following columns:
1. Contract ID — from CTR grouping key
2. Account Number
3. Account Name
4. Account Type — from user-supplied account mapping
5. Monetary? — from user-supplied account mapping (Monetary/Non-Monetary)
6. Account Currency — contract currency for the group
7. Company Currency — from CTR input
8. Balance in Contract Currency — aggregated from CTR
9. Initial Measurement Company Currency Balance — aggregated from CTR
10. Rate — from user-supplied account mapping (Historical or Period End)
11. Period-End Spot Exchange Rate — from user-supplied exchange rates (matched by FromCurrency → contract currency and ToCurrency → company currency)
12. Re-measured Balance — col8 × col11 for monetary accounts, or = col9 for non-monetary accounts
13. FX (Gain) or Loss — col9 − col12 (Initial Measurement Company Currency Balance minus Re-measured Balance, the primary deliverable)

**FR-008:** The system shall accept two configuration inputs, both supplied as file uploads (`.xlsx`, `.xls`, or `.csv`):
- **Account mapping** — maps Account Number to Account Type, Monetary classification, and Rate method. Uploaded as a file with columns: `Account Number`, `Account Type`, `Monetary?`, `Rate`. The Rate column specifies whether the account uses "Historical" or "Period End" rates. Supports two upload modes: **Replace** (clear existing, load from file) and **Merge** (add new entries, update existing entries with the same Account Number). The current mapping can be downloaded as an Excel file for sharing with other users. A Clear All button clears all saved mapping data.
- **Period-end exchange rates** — spot rates per currency pair. Uploaded as a file with columns: `RateType`, `FromCurrency`, `ToCurrency`, `ValidFrom`, `ExchangeRate`. The system matches `FromCurrency` to the account's contract currency and `ToCurrency` to the company currency to find the correct spot rate. Duplicate detection uses the composite key `{FromCurrency, ToCurrency, ValidFrom}`. Supports the same **Replace** and **Merge** upload modes. The current rates can be downloaded as an Excel file for sharing. A Clear All button clears all saved rate data.

Both configuration files are independent of the CTR report — they can be uploaded, downloaded, shared, and managed before any CTR file is processed.

**FR-009:** The system shall sort output rows by Account Number (ascending) within each worksheet.

**FR-010:** The system shall handle duplicate or missing Account Names gracefully; if a name is missing, it shall be left blank or default to "—" (dash).

**FR-032:** The system shall include all CTR rows in the output regardless of whether the account exists in the Account Mapping configuration. For accounts not found in the mapping:
- Column D (Account Type) shall show "N/A"
- Column E (Monetary?) shall show "N/A"
- Column J (Rate) shall show "N/A"
- Columns K (Period-End Spot Exchange Rate), L (Re-measured Balance), and M (FX Gain/Loss) shall be left blank
- A warning shall be logged identifying the unmapped Account Number
- Processing shall continue for all remaining rows

**FR-033:** The system shall include all CTR rows in the output regardless of whether an exchange rate exists for the account's currency pair. For accounts where no matching rate is found in the Exchange Rates configuration:
- Column K (Period-End Spot Exchange Rate) shall be left blank
- Column L (Re-measured Balance) shall be left blank
- Column M (FX Gain/Loss) shall be left blank
- Columns D, E, J shall still be populated if the account exists in the mapping
- A warning shall be logged identifying the missing currency pair (FromCurrency → ToCurrency)
- Processing shall continue for all remaining rows

**FR-034:** When multiple exchange rate entries match the same {FromCurrency, ToCurrency} currency pair but have different ValidFrom dates, the system shall apply the following rate selection logic (floor lookup by date):
- **If the CTR metadata provides an End Date:** Select the exchange rate entry with the most recent ValidFrom date that does not exceed the End Date extracted from CTR metadata (FR-002). If no ValidFrom date is ≤ the End Date, treat as a missing rate — apply FR-033 fallback (columns K, L, M left blank, log warning with the currency pair and reason).
- **If the CTR metadata does not provide an End Date (e.g., CSV input where metadata is unavailable):** Select the entry with the most recent (latest) available ValidFrom date for that currency pair.
- **This rate selection rule applies to monetary accounts only.** Non-monetary accounts use the Historical rate (fixed at initial measurement) and do not require period-end rate lookup; therefore, this logic does not apply to them.

### Output Specification

**FR-011:** The system shall generate an Excel workbook (`.xlsx`) with one or more worksheets (one per currency).

**FR-012:** Each worksheet shall include:
- A header row containing the following 13 columns: Contract ID, Account Number, Account Name, Account Type, Monetary?, Account Currency, Company Currency, Balance in Contract Currency, Initial Measurement Company Currency Balance, Rate, Period-End Spot Exchange Rate, Re-measured Balance, and FX (Gain) or Loss *(see FR-007 for full definitions)*
- Data rows starting immediately after headers (row 2)
- No metadata or non-tabular content in the output sheet

**FR-013:** The system shall preserve exact numeric precision for all currency amounts and exchange rates. No rounding, truncation, or float conversion at any stage — what the user uploads is exactly what appears in the output. All arithmetic uses exact decimal computation.

**FR-031:** The system shall apply accounting number format to all currency amount columns in the output Excel worksheets:
- Columns H, I, L, M shall be formatted with:
  - Thousand separators (comma)
  - Two decimal places
  - Negative values displayed in parentheses e.g. `(113,405.22)` not `-113,405.22`
  - Zero values displayed as `-` (dash)
- Column K (Period-End Spot Exchange Rate) shall be formatted as a plain decimal number with up to 6 decimal places (no parentheses — rates are always positive)
- This formatting applies to Excel cell formatting only and does not affect the underlying stored value or numeric precision

**FR-014:** The output file shall be named with a pattern: `CTR_FX_Remeasurement_{FiscalYear}_{FiscalPeriod}_{Timestamp}.xlsx`. For CSV inputs where fiscal year/period metadata is unavailable, the pattern shall fall back to `CTR_FX_Remeasurement_Unknown_Unknown_{Timestamp}.xlsx`.

### User Interface

**FR-015:** The system shall be a standalone desktop application dedicated to FX Remeasurement processing, distributed as a single `.exe` file built with PyInstaller. It is independent from the existing Poliza Ledger (CTR Mapper) application.

**FR-016:** The application shall follow a two-step configure-then-process workflow:
- **Step 1 — Configuration:** User manages two configuration files (account mapping and exchange rates) via upload, download, replace, merge, and Clear All operations. Configs persist locally and are available across sessions.
- **Step 2 — Upload & Process:** User uploads the CTR report file. The Process button is disabled until both configurations are loaded. Processing runs asynchronously with job ID and status polling.
- **Results:** Upon completion, the results view shows the source filename, fiscal year/period, processing time, summary stats (input rows, output rows, currencies), a "Download Output" button, and a "Process Another File" button. No detailed output table or warnings are displayed in the UI — the full output is in the downloaded Excel file.

*Note: UI layout, sidebar structure, card organization, and component details (button placement, form structure, status indicators) are specified in the mockup at `webapp/mockup-v1.html`. This PRD documents functional behavior and data flow; the mockup is the authoritative source for visual layout and UI component positioning.*

**FR-017:** The application shall support both desktop mode (primary — single-user, `localhost:5001`, auto-opens browser) and web mode (secondary — multi-user server, `0.0.0.0:8000`). Desktop mode is the primary deployment target.

**FR-018:** Error messages shall be specific and actionable:
- Missing required columns (list which)
- Insufficient data rows (count)
- Currency parsing errors (show examples)
- Invalid numeric values (row and column reference)

**FR-019:** The system shall support English only. No i18n or multi-language support is required.

### Data Validation

**FR-020:** The system shall validate that Account Number and Contract Currency are non-empty for each data row; rows missing either shall be logged and skipped with a warning.

**FR-021:** The system shall validate that Amount in Contract Currency and Amount in Company Currency are numeric; if non-numeric, the row shall be logged and skipped, and processing shall continue.

**FR-022:** The system shall enforce a maximum input file size of 50 MB (matching existing policy).

**FR-023:** The system shall validate the input file is a valid Excel or CSV format; malformed files shall be rejected with a clear error message. For CSV files, the system shall auto-detect the header row or assume row 1 as headers (no metadata rows).

*Note: Metadata extraction (FR-002) applies to Excel files only (`.xlsx`, `.xls`). For CSV files, metadata fields (Fiscal Year, Fiscal Period, etc.) are not available and shall default to `Unknown`.*

### Configuration Persistence & Storage

**FR-024:** The system shall persist configuration data (account mapping, exchange rates, history) to the local filesystem:
- **Desktop mode (PyInstaller `.exe`):** `%LOCALAPPDATA%/CTR-FX-Remeasurement/` — per-user, no admin rights required, survives `.exe` updates.
- **Development mode:** `webapp/backend/` directory.
- Internal storage format is SQLite. Users interact with configs via Excel/CSV file upload and download — they never touch the database directly.

**FR-025:** The system shall support two upload modes for both configuration files:
- **Replace** — clear all existing entries and load entirely from the uploaded file.
- **Merge** — add new entries from the uploaded file; update existing entries that share the same key (Account Number for mapping, Currency for rates).

**FR-026:** The system shall provide clear and download capabilities for each configuration:
- **Clear All** clears all saved data for the selected configuration, reverting to blank/empty state.
- **Download** exports the current saved configuration as a styled Excel file (`.xlsx`) for sharing with other users of the application.

### Configuration History & Rollback

**FR-027:** The system shall automatically record a history entry for every configuration change (upload, clear all). Each history entry shall include:
- Timestamp, action type, config type affected, source filename (if applicable)
- A full snapshot of both configuration files at the time of the action

**FR-028:** The system shall display the history of configuration changes as a read-only audit table (most recent first) with columns: Timestamp, Action, Config, Details. The table shall be limited to the most recent 50 entries to prevent page overflow. A "Clear History" button shall delete all history entries. No rollback capability in Phase 1 — recovery from bad uploads is done by downloading the config, editing in Excel, and re-uploading with Replace mode. Rollback (restore from snapshot) is a Phase 2 feature.

**FR-029:** History data shall be stored in SQLite database `ctr_fx.db` (same `%LOCALAPPDATA%` path for desktop, same backend directory for dev) in a `config_history` table.

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
- Configuration (account mapping, exchange rates, history) is persisted to SQLite database in `%LOCALAPPDATA%/CTR-FX-Remeasurement/` (desktop) and survives application restarts and `.exe` updates

**NFR-004 — Security:**
- File uploads shall be restricted to `.xlsx`, `.xls`, and `.csv` formats
- Uploaded files shall be stored in a temporary location and deleted after processing
- No client data shall be logged or persisted beyond the processing session

---

## 5. Acceptance Criteria

### US-01: FX Gain/Loss per GL Account

**Given** a CTR file, account mapping, and period-end exchange rates
**When** the user uploads and processes the file
**Then** column 13 (FX Gain or Loss) shall show the discrepancy between the initial company currency balance and the re-measured balance for each GL account

**Given** a monetary account with Balance in Contract Currency = 10,000 USD, Initial Measurement = 130,000 MXN, and period-end spot rate = 14.0
**When** processed
**Then** Re-measured Balance = 140,000 MXN and FX (Gain) or Loss = −10,000 MXN (Initial 130,000 minus Re-measured 140,000)

**Given** a non-monetary account
**When** processed
**Then** Re-measured Balance = Initial Measurement (historical rate preserved) and FX (Gain) or Loss = 0

### US-02: Closing Balance Aggregation

**Given** a CTR file with duplicate account entries across rows
**When** processed
**Then** the system shall correctly sum all amounts for each {Contract ID, Account Number, Account Name, Contract Currency} group

**Given** amounts with decimal values (e.g., 1234.56)
**When** aggregated and displayed in output
**Then** precision shall be preserved exactly — no rounding or truncation

### US-03: Account Mapping Configuration

**Given** the FX Remeasurement application is loaded
**When** the user navigates to the Configuration tab
**Then** an Account Mapping section shall be visible with Upload (Replace/Merge modes), Download, and Clear All buttons

**Given** the user uploads a valid account mapping file with columns Account Number, Account Type, Monetary?, and Rate
**When** the upload completes successfully
**Then** the system shall store the mapping in local configuration and display a confirmation message

**Given** the user uploads in Merge mode
**When** the upload completes
**Then** new accounts shall be added and existing accounts (matching Account Number) shall be updated with values from the file

**Given** the user uploads in Replace mode
**When** the upload completes
**Then** all previously saved account mappings shall be cleared and only the uploaded mappings shall be retained

**Given** an account mapping file has been uploaded
**When** the user clicks the Download button
**Then** the system shall export the current account mapping as a styled Excel file (`.xlsx`) for sharing with other users

**Given** account mappings have been saved
**When** the user clicks Clear All
**Then** all saved account mapping data shall be cleared and the application shall revert to empty state

### US-04: Exchange Rates Configuration

**Given** the FX Remeasurement application is loaded
**When** the user navigates to the Configuration tab
**Then** an Exchange Rates section shall be visible with Upload (Replace/Merge modes), Download, and Clear All buttons

**Given** the user uploads a valid exchange rates file with columns RateType, FromCurrency, ToCurrency, ValidFrom, and ExchangeRate
**When** the upload completes successfully
**Then** the system shall store the rates in local configuration and display a confirmation message; duplicate detection uses the composite key {FromCurrency, ToCurrency, ValidFrom}

**Given** the user uploads in Merge mode
**When** the upload completes
**Then** new rate entries shall be added and existing rate entries (matching composite key {FromCurrency, ToCurrency, ValidFrom}) shall be updated with values from the file

**Given** the user uploads in Replace mode
**When** the upload completes
**Then** all previously saved exchange rates shall be cleared and only the uploaded rates shall be retained

**Given** exchange rates have been saved
**When** the user clicks Download
**Then** the system shall export the current exchange rates as a styled Excel file (`.xlsx`) for sharing with other users

**Given** exchange rates have been saved
**When** the user clicks Clear All
**Then** all saved exchange rate data shall be cleared and the application shall revert to empty state

### US-05: Multi-Sheet Output by Currency

**Given** a CTR with transactions in USD, EUR, and GBP
**When** processed
**Then** the output workbook shall contain exactly 3 worksheets named "USD", "EUR", "GBP"

**Given** a worksheet in the output
**When** opened in Excel
**Then** all rows shall be sorted by Account Number in ascending order

### US-06: Standalone Desktop Application

**Given** the FX Remeasurement application is loaded
**When** the user views the main page
**Then** an upload area for CTR files shall be visible with a clear "FX Remeasurement" title

**Given** the application is deployed
**When** accessed in web mode or desktop mode
**Then** the full upload-process-download workflow shall function identically in both modes

### US-07: Shareable Configuration Files

**Given** an account mapping has been saved
**When** the user clicks Download on the Account Mapping section
**Then** the system shall export the current account mapping as a styled Excel file (`.xlsx`) with columns Account Number, Account Type, Monetary?, and Rate

**Given** exchange rates have been saved
**When** the user clicks Download on the Exchange Rates section
**Then** the system shall export the current exchange rates as a styled Excel file (`.xlsx`) with columns RateType, FromCurrency, ToCurrency, ValidFrom, and ExchangeRate

**Given** a user has downloaded a configuration file from another team member's application
**When** they upload it to their own application instance using Replace or Merge mode
**Then** the configuration shall be imported successfully and subsequent CTR processing shall use the imported values

### US-08: Configuration History (Audit Trail)

**Given** a configuration change has been made (upload or Clear All)
**When** the user navigates to the Audit History section
**Then** the change shall appear as a new row in the history table with Timestamp, Action, Config, and Details columns

**Given** the history table
**When** viewed
**Then** entries shall be sorted most recent first and limited to the 50 most recent entries

**Given** the history table
**When** viewed
**Then** no edit, rollback, or delete of individual rows shall be possible — the table is read-only

**Given** the user clicks Clear History
**When** confirmed
**Then** all history entries shall be deleted and the table shall show empty state

### US-09: Processing Error Display and Retry

**Given** a CTR file with missing required columns is uploaded
**When** the user clicks Process
**Then** the UI shall display an error state showing: a clear error heading, a summary message, a detailed list of missing and found columns, a helpful hint, and a "Try Again" button

**Given** an error is displayed
**When** the user clicks "Try Again"
**Then** the user shall return to the CTR upload screen ready to upload a corrected file

**Given** invalid numeric values are detected in Amount fields
**When** processing fails
**Then** the error message shall include the row number and column reference

**Given** a file with headers but no data rows is uploaded
**When** processing fails
**Then** the error message shall state "No data rows found" and suggest verifying the export period and filters.

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
- File with headers but no data rows → Return error state with message "No data rows found. Verify export period and filters." and a Try Again button. Processing does not produce an output file.
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

**EC-009 — Unmapped Accounts:**
- Account Number exists in CTR but not in Account Mapping configuration → Include the row in output with Account Type = "N/A", Monetary? = "N/A", Rate = "N/A", and columns K, L, M left blank. Log a warning with the unmapped Account Number. Processing continues for remaining rows (FR-032).

**EC-010 — Missing Exchange Rates:**
- Currency pair (FromCurrency, ToCurrency) exists in CTR but not in Exchange Rates configuration → Include the row in output with columns K, L, M left blank; D, E, J still populated from mapping if available. Log a warning with the missing pair (FromCurrency → ToCurrency). Processing continues for remaining rows (FR-033).

**EC-011 — No Valid Rate for Period:**
- Exchange Rates configuration has entries for a currency pair, but all ValidFrom dates are after the CTR's fiscal period end date (no qualifying rate exists for the period) → Treat as a missing rate; apply FR-033 fallback: columns K, L, M left blank; D, E, J still populated from mapping if available. Log a warning identifying the currency pair and noting that no rate valid as of the period end date was found. Processing continues for remaining rows (FR-034).

---

## 7. Phase 1 Scope (This Ticket)

### In Scope
- Parse CTR metadata (rows 1-26) and extract key fields
- Identify and validate required columns
- Group data by {Contract ID, Account Number, Account Name, Contract Currency}
- Aggregate Amount in Contract Currency and Amount in Company Currency
- Accept account mapping as file upload (CSV/Excel) with Replace/Merge modes
- Accept period-end exchange rates as file upload (CSV/Excel) with Replace/Merge modes
- Download current configs as Excel files for sharing between desktop users
- Clear All buttons to clear saved configs
- Download output Excel file (FX Gain/Loss results) — `CTR_FX_Remeasurement_{FY}_{FP}_{Timestamp}.xlsx`
- Apply rate logic based on the Rate column in account mapping (Historical or Period End)
- Look up spot exchange rate by matching FromCurrency → contract currency and ToCurrency → company currency
- Calculate Re-measured Balance (col8 × col11 for Period End accounts, = col9 for Historical accounts)
- **Calculate FX (Gain) or Loss per account (col9 − col12) — the primary deliverable**
- Create one worksheet per unique currency with all 13 columns populated (including Contract ID)
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
- **Account mapping config** — stored in SQLite database at `%LOCALAPPDATA%/CTR-FX-Remeasurement/ctr_fx.db`; updated on every upload, merge, or reset; survives application restarts and `.exe` updates.
- **Exchange rates config** — stored in same SQLite database (`ctr_fx.db`); same lifecycle.
- **Configuration history** — stored in same SQLite database (`ctr_fx.db`) as `config_history` table; includes full snapshots of both configs at time of action.

### Additional Inputs (Phase 2)
- Prior period FX adjustments — source TBD

### Test Data
- `CTR_0422.xlsx` — 7 unique accounts, provided for validation
- Abbott period P1 data — expected to match manual "3. CTR Pivot P1" sheet

---

## 9. Success Metrics

**Functional Success:**
- FX (Gain) or Loss values match manually verified calculations (Abbott P1)
- All 13 columns populated in output for accounts with mapping data
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
- **Ephemeral Job Data:** Job processing data stored in-memory; not persisted across application restarts. Configuration data (account mapping, exchange rates, history) is persisted as SQLite database in `%LOCALAPPDATA%/CTR-FX-Remeasurement/ctr_fx.db`.
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

## 12. Open Questions

| ID | Question | Owner | Due Date | Status | Resolution |
|----|----------|-------|----------|--------|------------|
| OQ-001 | Can a single GL account number appear in multiple contract currencies within the same Contract ID? If yes, grouping key `{Contract ID, Account Number, Contract Currency}` is correct. If no, it simplifies to `{Contract ID, Account Number}`. Affects US-02 and FR-006. | Abbott Implementation Team | Before Phase 1 sign-off | Resolved | Confirmed grouping key is {Contract ID, Account Number, Account Name, Contract Currency}. Contract ID is a new addition beyond the original Excel. Account Name included per original Jira ticket. |
| OQ-002 | When the Exchange Rates config has multiple entries for the same {FromCurrency, ToCurrency} pair with different ValidFrom dates, should the system use a floor lookup (most recent ValidFrom ≤ CTR End Date), or should users always upload an exact-match rate for the period end date? Affects FR-034 and EC-011. | Abbott Implementation Team | Before Phase 1 sign-off | Open | Working assumption: floor lookup — use the most recent ValidFrom ≤ CTR End Date (FR-034). Implementation will proceed with this assumption. Pending client validation before Phase 1 sign-off. |

---

## 13. Approval & Sign-Off

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
