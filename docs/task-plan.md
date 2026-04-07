# Task Plan: CTR FX Remeasurement Tool

**Source PRD:** docs/product-requirements.md
**Source Tech Spec:** docs/technical-specification.md
**Project Size:** Standard
**Generated:** 2026-04-07

---

## Durable Architectural Decisions

- SQLite single-file database (`ctr_fx.db`) for all persistence
- Desktop storage: `%LOCALAPPDATA%/CTR-FX-Remeasurement/`; Dev: `webapp/backend/`
- FastAPI + Vue 3 (Options API with Composition `setup()`)
- Sister project pattern: `C:/workarea/maturity_analysis_report/webapp/`
- COLUMN_MAPPINGS vectorized dict pattern for fx_processor
- Background job processing with job ID + status polling
- Dual-mode: desktop (`localhost:5001`) and web (`0.0.0.0:8000`)
- Exact decimal precision — exchange_rate stored as TEXT in SQLite, all arithmetic uses Python Decimal
- Exchange rate lookup: floor date query (most recent valid_from <= as-of date)
- Brand background `#009cde`, shared CSS from sister project

---

## Slices

### Slice 1 — App Shell + Navigation · AFK
**Goal:** User sees the app layout with sidebar, can navigate between 3 sections (Process CTR, Configuration, Audit History)
**Layers touched:**
- Schema: none
- Logic/API: FastAPI app skeleton (`app.py`), dual-mode server, static file serving, `/health` endpoint, CORS middleware, cleanup utility
- UI: `App.vue` (sidebar + view routing), `AppHeader.vue`, `AppFooter.vue`, `styles.css`, `main.js`, `vite.config.js`, `index.html`
- Tests: App loads in browser, sidebar navigation switches views, health endpoint responds
**Acceptance criteria:**
- App starts on `localhost:5001` (desktop) or `0.0.0.0:8000` (web)
- Sidebar shows 3 sections; clicking each switches the visible content area
- Header shows "CTR FX Remeasurement" title
- `/health` returns `{"status": "healthy", "mode": "desktop"|"web"}`
**Depends on:** none

### Slice 2 — Account Mapping Config · HITL
**Goal:** User can upload an account mapping file (Replace/Merge), see the count, download it as Excel, and clear all mappings
**Layers touched:**
- Schema: `account_mapping` table in SQLite (account_number PK, account_type, monetary, rate)
- Logic/API: `config_store.py` (DB init, load/save/reset, parse file with flexible column aliases, merge, export as styled Excel), API endpoints (`GET/POST/DELETE /config/account-mapping`, `GET /config/account-mapping/download`)
- UI: `AccountMapping.vue` (upload area with Replace/Merge toggle, Download button, Clear All button, count display), `ProcessCTR.vue` (shows mapping count in readiness checklist)
- Tests: Upload Replace clears + loads, Upload Merge adds/updates, Download produces valid Excel, Clear All empties, count updates in Process CTR view
**Acceptance criteria:**
- Upload accepts `.xlsx`, `.xls`, `.csv` with flexible column name matching (FR-008)
- Replace mode clears existing + loads from file (FR-025)
- Merge mode adds new entries, updates existing by Account Number (FR-025)
- Download exports styled `.xlsx` with correct columns (FR-026)
- Clear All removes all saved data (FR-026)
- Config persists across app restarts (FR-024)
**Depends on:** Slice 1

### Slice 3 — Exchange Rates Config · AFK
**Goal:** User can upload exchange rates (Replace/Merge), see the count, download as Excel, and clear all rates
**Layers touched:**
- Schema: `exchange_rates` table in SQLite (id PK, rate_type, from_currency, to_currency, valid_from, exchange_rate as TEXT), lookup index
- Logic/API: `config_store.py` (load/save/reset, parse file, merge by composite key {from_currency, to_currency, valid_from}, export, `get_exchange_rate()` floor lookup), API endpoints (`GET/POST/DELETE /config/exchange-rates`, `GET /config/exchange-rates/download`)
- UI: `ExchangeRates.vue` (upload area with Replace/Merge toggle, Download button, Clear All button, count display), `ProcessCTR.vue` (shows rates count in readiness checklist)
- Tests: Upload Replace/Merge, rate lookup returns correct rate by date, Download produces valid Excel, Clear All empties
**Acceptance criteria:**
- Upload accepts `.xlsx`, `.xls`, `.csv` with flexible column matching (FR-008)
- Duplicate detection uses composite key {FromCurrency, ToCurrency, ValidFrom} (FR-008)
- Currency codes normalized to uppercase (FR-030)
- Rate lookup: most recent valid_from <= as-of date (FR-034)
- Exchange rate stored as TEXT — no float rounding (FR-013)
**Depends on:** Slice 1

### Slice 4 — CTR Upload + FX Processing · HITL
**Goal:** User uploads a CTR file and downloads an Excel workbook with FX Gain/Loss calculated per GL account, one sheet per currency
**Layers touched:**
- Schema: none new (Pydantic models: `ProcessingRequest`, `ProcessingResponse`, `JobStatus`)
- Logic/API: `models/schemas.py` (Pydantic models), `ctr_reader.py` (parse CTR, validate 7 core columns, extract metadata rows 1-26, normalize currencies, coerce amounts), `fx_processor.py` (group by {Contract ID, Account Number, Account Name, Contract Currency}, aggregate, apply COLUMN_MAPPINGS, write multi-sheet Excel with styling), `app.py` (`POST /upload`, `GET /status/{job_id}`, `GET /download/{job_id}`, background task)
- UI: `ProcessCTR.vue` (file upload area, Process button disabled until both configs loaded), `ProcessingView.vue` (progress polling), `ResultsView.vue` (summary stats + download button), `ErrorView.vue` (error display + Try Again)
- Tests: End-to-end with `CTR 0422.xlsx` test data, unmapped accounts show N/A (FR-032), missing rates leave columns blank (FR-033), output columns match FR-007, accounting number format (FR-031)
**Acceptance criteria:**
- Process button disabled until both configs loaded (FR-016)
- Background processing with job ID + status polling (FR-016)
- Output: 13 columns per FR-007, sorted by Account Number (FR-009)
- One worksheet per unique Contract Currency (FR-006)
- FX (Gain) or Loss = Initial Measurement - Re-measured Balance (FR-007)
- Re-measured Balance = balance_cc * spot_rate (monetary) or initial_measurement (non-monetary) (FR-007)
- Exact decimal precision preserved (FR-013)
- Accounting number format on currency columns (FR-031)
- Unmapped accounts: include with N/A, log warning (FR-032)
- Missing rates: columns K/L/M blank, log warning (FR-033)
- Error messages: specific and actionable (FR-018)
**Depends on:** Slice 2, Slice 3

### Slice 5 — Configuration History · AFK
**Goal:** User can view a read-only audit trail of all config changes (uploads, clears) and clear history
**Layers touched:**
- Schema: `config_history` table in SQLite (id, timestamp, action, config_type, source_filename, details, snapshot_account_mapping, snapshot_exchange_rates)
- Logic/API: `config_store.py` (`save_history_entry()` — called on every config upload/clear, `list_history()`, `get_history_entry()`), API endpoints (`GET /history`, `GET /history/{entry_id}`, `DELETE /history`), wire `save_history_entry` into Slice 2 and 3 upload/clear flows
- UI: `HistoryView.vue` (read-only table: Timestamp, Action, Config, Details; limited to 50 entries; Clear History button)
- Tests: History entry created on upload, created on clear, list returns most-recent-first, clear history empties table
**Acceptance criteria:**
- Every config change (upload, clear) records a history entry (FR-027)
- Each entry includes timestamp, action, config type, source filename, details (FR-027)
- Full snapshot of both configs saved for Phase 2 rollback (FR-027)
- Display limited to 50 most recent entries (FR-028)
- Clear History deletes all entries (FR-028)
- Table is read-only — no edit/delete of individual rows (FR-028)
**Depends on:** Slice 2, Slice 3

### Slice 6 — Desktop Packaging · HITL
**Goal:** Application packaged as a single `.exe` via PyInstaller with persistent local storage
**Layers touched:**
- Schema: none
- Logic/API: `build_desktop.py` (PyInstaller build script), `CTR_Mapper.spec` (spec file), path resolution in `config_store.py` (`_get_app_data_dir()`), `app.py` (`get_frontend_path()` for PyInstaller)
- UI: Frontend built with `npm run build` → `frontend-dist/`
- Tests: `.exe` launches, opens browser, processes a file, data persists after restart
**Acceptance criteria:**
- Single `.exe` file (FR-015)
- Data stored in `%LOCALAPPDATA%/CTR-FX-Remeasurement/` (FR-024)
- No admin rights required (FR-024)
- Data survives `.exe` updates (FR-024)
- Auto-opens browser on launch (FR-017)
**Depends on:** Slice 1, 2, 3, 4, 5

---

## Implementation Order

1. Slice 1 — App Shell + Navigation (foundation for all UI)
2. Slice 2 — Account Mapping Config (first config type, establishes patterns)
3. Slice 3 — Exchange Rates Config (same pattern, adds rate lookup)
4. Slice 4 — CTR Upload + FX Processing (core feature, needs both configs)
5. Slice 5 — Configuration History (wires into config flows from slices 2-3)
6. Slice 6 — Desktop Packaging (needs everything working)

---

## Slices by Classification

**HITL (requires human review):**
- Slice 2 (Account Mapping — data integrity, config persistence)
- Slice 4 (FX Processing — financial calculations, core deliverable)
- Slice 6 (Desktop Packaging — deployment, user-facing)

**AFK (safe to implement autonomously):**
- Slice 1 (App Shell — pure UI scaffolding)
- Slice 3 (Exchange Rates — follows Slice 2 pattern)
- Slice 5 (Configuration History — read-only audit trail)

---

## Walkthrough Progress

**Last Updated:** 2026-04-07
**Current Slice:** 2. Account Mapping Config

| Slice | Teach | Build | Notes |
|-------|-------|-------|-------|
| 1. App Shell + Navigation | done | done | Backend skeleton, sidebar nav, placeholders, health endpoint verified |
| 2. Account Mapping Config | not started | not started | |
| 3. Exchange Rates Config | not started | not started | |
| 4. CTR Upload + FX Processing | not started | not started | |
| 5. Configuration History | not started | not started | |
| 6. Desktop Packaging | not started | not started | |
