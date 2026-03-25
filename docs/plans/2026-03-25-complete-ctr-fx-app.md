# CTR FX Remeasurement — Complete App Implementation Plan

**Goal:** Complete the full app per wireframe-v4.html — backend fixes, SQLite config store, upload/download endpoints, and all frontend screens.

**Wireframe:** `webapp/wireframe-v4.html` (8 screens)
**Spec:** `docs/technical-specification.md`
**Branch:** `ctr-fx-backend-review-complete`

---

## Phase 1: Backend Fixes (ctr_reader.py)

**Files:** `webapp/backend/services/ctr_reader.py`

### Task 1.1 — Currency code normalization

The CTR stores currencies as `"USD - UNITED STATES DOLLAR"`. Strip to code only.

Fix in `parse_ctr()` after the uppercase step:
```python
# After: df["Contract Currency"] = df["Contract Currency"].astype(str).str.strip().str.upper()
# Add:
df["Contract Currency"] = df["Contract Currency"].str.split(" - ").str[0].str.strip()
```

### Task 1.2 — Extract fiscal_year, fiscal_period, company_currency from data columns

Rows 1-26 don't contain these. Extract unique values from the data rows instead.

Add after `_coerce_numeric_amounts` call in `parse_ctr()`:
```python
# Extract fiscal metadata from data columns (not rows 1-26)
if metadata.get("fiscal_year") is None and "Fiscal Year" in df.columns:
    vals = df["Fiscal Year"].dropna().unique()
    if len(vals) == 1:
        metadata["fiscal_year"] = str(int(vals[0])) if str(vals[0]).replace('.0','').isdigit() else str(vals[0])
    elif len(vals) > 1:
        warnings.append(f"Multiple Fiscal Years in CTR: {sorted(vals.tolist())}. Using first.")
        metadata["fiscal_year"] = str(vals[0])

if metadata.get("fiscal_period") is None and "Fiscal Period" in df.columns:
    vals = df["Fiscal Period"].dropna().unique()
    if len(vals) == 1:
        metadata["fiscal_period"] = str(int(vals[0])) if str(vals[0]).replace('.0','').isdigit() else str(vals[0])
    elif len(vals) > 1:
        warnings.append(f"Multiple Fiscal Periods in CTR: {sorted(vals.tolist())}. Using first.")
        metadata["fiscal_period"] = str(vals[0])

if metadata.get("company_currency") is None and "Company Currency" in df.columns:
    vals = df["Company Currency"].dropna().unique()
    if len(vals) >= 1:
        # Normalize: "CAD - Canadian Dollar" → "CAD"
        metadata["company_currency"] = str(vals[0]).split(" - ")[0].strip().upper()
```

---

## Phase 2: Rewrite config_store.py (SQLite)

**File:** `webapp/backend/services/config_store.py` — full rewrite

### Schema
```sql
-- account_mapping: keyed by account_number
CREATE TABLE IF NOT EXISTS account_mapping (
    account_number TEXT PRIMARY KEY,
    account_type   TEXT NOT NULL,
    monetary       TEXT NOT NULL,
    rate           TEXT NOT NULL
);

-- exchange_rates: time-based, date-range lookup
CREATE TABLE IF NOT EXISTS exchange_rates (
    id            TEXT PRIMARY KEY,
    rate_type     TEXT,
    from_currency TEXT NOT NULL,
    to_currency   TEXT NOT NULL,
    valid_from    TEXT NOT NULL,
    exchange_rate REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_er_lookup ON exchange_rates (from_currency, to_currency, valid_from);

-- config_history: append-only audit log with snapshots
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

### Public API (keep same function names as current — app.py imports don't change)

```python
# Path resolution
_get_app_data_dir() -> Path          # same logic as current
_get_db() -> sqlite3.Connection      # opens ctr_fx.db, runs _init_db

# Account Mapping
load_account_mapping() -> list[dict]
save_account_mapping(rows: list[dict]) -> None
reset_account_mapping() -> None
parse_account_mapping_file(file_path) -> tuple[list[dict], list[str]]
merge_account_mapping(existing, incoming) -> list[dict]
export_account_mapping(output_path) -> str

# Exchange Rates
load_exchange_rates() -> list[dict]
save_exchange_rates(rows: list[dict]) -> None
reset_exchange_rates() -> None
parse_exchange_rates_file(file_path) -> tuple[list[dict], list[str]]
merge_exchange_rates(existing, incoming) -> list[dict]
export_exchange_rates(output_path) -> str
get_exchange_rate(from_ccy, to_ccy, as_of_date) -> float | None   # NEW — date-range lookup

# History
save_history_entry(action, config_type, mode, source_filename, details) -> str
list_history(limit=50) -> list[dict]
get_history_entry(entry_id) -> dict | None
rollback_to_entry(entry_id, config_type="both") -> dict
```

### Column aliases for file parsing

**Account mapping file:**
- account_number: "account number", "account_number", "acct number", "gl account"
- account_type: "account type", "account_type", "type", "acct type"
- monetary: "monetary", "monetary?", "is monetary"
- rate: "rate", "rate type", "rate method"

**Exchange rates file:**
- id: "objectid", "object_id", "id"  (optional — generate UUID if missing)
- rate_type: "ratetype", "rate_type", "rate type", "type"
- from_currency: "fromcurrency", "from_currency", "from currency", "from ccy"
- to_currency: "tocurrency", "to_currency", "to currency", "to ccy"
- valid_from: "validfrom", "valid_from", "valid from", "date", "effective date"
- exchange_rate: "exchangerate", "exchange_rate", "exchange rate", "rate", "fx rate"

---

## Phase 3: Backend — Upload/Download Endpoints (app.py)

**File:** `webapp/backend/app.py`

### Task 3.1 — POST /upload

```python
@app.post("/upload")
async def upload_ctr(
    file: UploadFile = File(...),
    input_header_start: int = Form(27),
    background_tasks: BackgroundTasks = ...,
):
    # 1. Validate file type + size (50MB)
    # 2. Save to temp UPLOAD_DIR
    # 3. parse_ctr() — return 400 on failure
    # 4. Check both configs loaded (account_mapping + exchange_rates) — return 400 if empty
    # 5. Create job_id, jobs[job_id] = JobStatus(...)
    # 6. background_tasks.add_task(_run_fx_processing, job_id, temp_path, ctr_result)
    # 7. Return {"job_id": job_id}
```

Background task `_run_fx_processing`:
```python
def _run_fx_processing(job_id, temp_path, ctr_result):
    jobs[job_id].status = "processing"
    mapping = load_account_mapping()           # list[dict] → convert to dict keyed by account_number
    rates = load_exchange_rates()              # list[dict]
    as_of_date = _period_to_date(ctr_result["metadata"])
    output_filename = build_output_filename(...)
    output_path = UPLOAD_DIR / output_filename
    result = process_fx(df, mapping_dict, rates_list, str(output_path), as_of_date, ...)
    jobs[job_id].status = "completed" if result["success"] else "failed"
    jobs[job_id].result = result
    jobs[job_id].completed_at = datetime.now()
```

Helper `_period_to_date(metadata)` → converts fiscal_year + fiscal_period to ISO date for rate lookup.

### Task 3.2 — GET /download/{job_id}

```python
@app.get("/download/{job_id}")
async def download_result(job_id: str):
    # 1. Check job exists + status == "completed"
    # 2. Get output_file path from job result
    # 3. Return FileResponse
```

### Task 3.3 — Fix get_upload_dir() duplication

Import `_get_app_data_dir` from `config_store` instead of copy-pasting the frozen/dev logic.

### Task 3.4 — Update schemas.py ProcessingResponse

Add CTR-specific fields:
```python
class ProcessingResponse(BaseModel):
    success: bool
    message: str
    job_id: Optional[str] = None
    input_rows: Optional[int] = None
    output_rows: Optional[int] = None
    sheets: Optional[list[str]] = None
    unmapped_accounts: Optional[list[str]] = None
    missing_rate_currencies: Optional[list[str]] = None
    warnings: Optional[list[str]] = None
    processing_time: Optional[float] = None
    error: Optional[str] = None
```

---

## Phase 4: Frontend — App Shell

**Files:** `webapp/frontend-vue/src/App.vue`, `webapp/frontend-vue/src/assets/styles.css`

Replace current centered card layout with wireframe's sidebar + topbar shell.

### Layout structure
```
┌─────────────────────────────────────────────┐
│  topbar: "CTR FX Remeasurement" | Desktop   │
├────────────┬────────────────────────────────┤
│  sidebar   │  <router-view / current view>  │
│  nav       │                                │
│            │                                │
└────────────┴────────────────────────────────┘
```

### Views (state machine via `currentView` ref)
- `'process'` → ProcessCTR.vue
- `'processing'` → ProcessingView.vue
- `'results'` → ResultsView.vue
- `'mapping'` → AccountMapping.vue
- `'rates'` → ExchangeRates.vue
- `'history'` → History.vue
- `'error'` → ErrorView.vue

### Sidebar nav items
```
Process
  ├── Process CTR

Config
  ├── Account Mapping  [badge: count]
  └── Exchange Rates   [badge: count]

Audit
  └── History
```

### CSS — replace styles.css with wireframe styles
Use the wireframe's CSS as base: sidebar layout, `.shell`, `.topbar`, `.card`, `.split`, `.upload-box`, `.modes`, `.readiness`, `.stats`, `.btn-*`, `.progress-bar`, `.steps`, `.error-box`.

Keep brand color `#009cde`.

---

## Phase 5: Frontend — ProcessCTR.vue

**File:** `webapp/frontend-vue/src/components/ProcessCTR.vue`

### States
1. **Empty** — upload box (dashed), readiness indicators, Process button disabled
2. **File selected** — upload box (blue border, "File ready"), Process button enabled if both configs loaded

### Readiness indicators
Two items side by side:
- Account Mapping: green dot + count, or yellow dot + "Not set"
- Exchange Rates: green dot + count, or yellow dot + "Not set"

Fetched from `GET /config/account-mapping` and `GET /config/exchange-rates` on mount.

### Upload behavior
- Drag-and-drop + click-to-browse
- Accept: `.xlsx`, `.xls`, `.csv`
- Max size: 50MB (client-side check before POST)
- On Process click: `POST /upload` (multipart) → receive `job_id` → emit `start-processing` event to App.vue

### Template sketch
```vue
<div class="content">
  <h2>Process CTR</h2>
  <p class="desc">Upload a CTR file...</p>

  <div class="upload-box" :class="{ 'has-file': selectedFile }" @drop="onDrop" @dragover.prevent>
    <template v-if="!selectedFile">
      <h4>Drop your CTR file here</h4>
      <p>or browse files · .xlsx .xls .csv</p>
    </template>
    <template v-else>
      <h4 style="color:#009cde">File ready</h4>
      <p><strong>{{ selectedFile.name }}</strong> · {{ fileSizeKb }} KB</p>
      <a @click="clearFile">Choose different file</a>
    </template>
  </div>

  <div class="readiness">
    <div class="readiness-item">
      <span class="dot" :class="mappingReady ? 'dot-ok' : 'dot-warn'"></span>
      Account Mapping
      <span>{{ mappingReady ? mappingCount + ' accts' : 'Not set' }}</span>
    </div>
    <div class="readiness-item">
      <span class="dot" :class="ratesReady ? 'dot-ok' : 'dot-warn'"></span>
      Exchange Rates
      <span>{{ ratesReady ? ratesCount + ' rate(s)' : 'Not set' }}</span>
    </div>
  </div>

  <div style="display:flex;justify-content:space-between">
    <button class="btn btn-sm" @click="clearFile" v-if="selectedFile">Clear</button>
    <span v-else></span>
    <button class="btn btn-blue" :disabled="!canProcess" @click="processFile">Process CTR</button>
  </div>
</div>
```

---

## Phase 6: Frontend — ProcessingView.vue

**File:** `webapp/frontend-vue/src/components/ProcessingView.vue`

Reuse existing `ProgressSection.vue` logic but render with wireframe step list.

### Steps (driven by job status polling)
1. File validated ✓
2. Metadata extracted (FY + Period from result)
3. Aggregating by GL account
4. Applying FX remeasurement
5. Writing output workbook

Map backend status → step:
- `pending` → step 1 done, step 2 active
- `processing` → steps 1-2 done, step 3 active
- `completed` → all done → emit `show-results`

```vue
<div style="text-align:center;max-width:360px">
  <h3>Processing {{ filename }}</h3>
  <div class="progress-bar"><div class="progress-fill" :style="{ width: progress + '%' }"></div></div>
  <p>{{ progressText }}</p>
  <ol class="steps">
    <li v-for="(step, i) in steps" :class="stepClass(i)">
      <span v-if="i < currentStep">✓</span>
      <span v-else-if="i === currentStep">●</span>
      <span v-else>{{ i + 1 }}.</span>
      {{ step }}
    </li>
  </ol>
</div>
```

---

## Phase 7: Frontend — ResultsView.vue

**File:** `webapp/frontend-vue/src/components/ResultsView.vue`

```vue
<div style="text-align:center;max-width:400px">
  <div style="font-size:48px">✓</div>
  <h2>Processing Complete</h2>
  <p class="desc">{{ filename }} — FY {{ fiscalYear }} · Period {{ fiscalPeriod }} · {{ processingTime }}s</p>

  <div class="stats">
    <div class="stat"><div class="val">{{ inputRows.toLocaleString() }}</div><div class="lbl">Input Rows</div></div>
    <div class="stat hl"><div class="val">{{ outputRows }}</div><div class="lbl">Output Rows</div></div>
    <div class="stat"><div class="val">{{ sheets.length }}</div><div class="lbl">Currencies</div></div>
  </div>

  <div style="display:flex;gap:8px;justify-content:center;margin-top:16px">
    <button class="btn btn-sm" @click="$emit('new-upload')">New Upload</button>
    <button class="btn btn-blue" @click="downloadOutput">Download Output</button>
  </div>
</div>
```

Download: `GET /download/{job_id}` → trigger browser download.

---

## Phase 8: Frontend — AccountMapping.vue

**File:** `webapp/frontend-vue/src/components/AccountMapping.vue`

Split layout: left = current mapping table, right = upload panel.

### Left card — current mapping
Table columns: Account Number, Account Type, Monetary?, Rate
Fetched from `GET /config/account-mapping` on mount.
Footer: "Clear All" (DELETE with confirm) + "Download .xlsx" (GET /config/account-mapping/download).

### Right card — upload
Upload box (drag-and-drop).
Replace / Merge toggle (`.modes`).
Upload button (disabled until file selected).
On upload: `POST /config/account-mapping` with `file` + `mode` → refresh left card.

---

## Phase 9: Frontend — ExchangeRates.vue

**File:** `webapp/frontend-vue/src/components/ExchangeRates.vue`

Same split layout as AccountMapping.

### Left card — current rates
Table columns: Rate Type, From Currency, To Currency, Valid From, Exchange Rate (right-aligned).
Fetched from `GET /config/exchange-rates` on mount.
Footer: "Clear All" + "Download .xlsx".

### Right card — upload
Same upload + Replace/Merge pattern.
Column hint text: "Cols: RateType, FromCurrency, ToCurrency, ValidFrom, ExchangeRate"

---

## Phase 10: Frontend — History.vue

**File:** `webapp/frontend-vue/src/components/History.vue`

Read-only table. Fetched from `GET /history`.

Columns: Timestamp, Action, Config, Details.
Note below table: "To rollback, navigate to the history folder and delete the most recent entry."

---

## Phase 11: Wire App.vue + update sidebar counts

App.vue responsibilities:
- Holds `currentView` state
- Passes `job_id` down to ProcessingView
- Listens for `start-processing` → switch to `'processing'`
- Listens for `show-results` → switch to `'results'`
- Listens for `new-upload` → switch to `'process'`
- Fetches `mappingCount` and `ratesCount` for sidebar badges (poll every 30s or on config change)
- Sidebar nav click → sets `currentView`

---

## Execution Order

```
Phase 1 (ctr_reader fixes)     → commit
Phase 2 (config_store SQLite)  → commit
Phase 3 (app.py endpoints)     → commit
Phase 4 (App.vue shell + CSS)  → commit
Phase 5 (ProcessCTR.vue)       → commit
Phase 6 (ProcessingView.vue)   → commit
Phase 7 (ResultsView.vue)      → commit
Phase 8 (AccountMapping.vue)   → commit
Phase 9 (ExchangeRates.vue)    → commit
Phase 10 (History.vue)         → commit
Phase 11 (Wire App.vue)        → commit + test end-to-end
```
