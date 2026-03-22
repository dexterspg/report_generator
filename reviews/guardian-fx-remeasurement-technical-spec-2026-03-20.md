# Quality Review: CTR FX Remeasurement Tool — Implementation Brief

## Review Type
Design

## Summary

This is a well-written implementation brief for a mini project that correctly identifies what to reuse from the sister CTR Mapper project and what to build new. The two-step upload flow is a smart adaptation of the sister project's single-step pattern, justified by the data dependency (unique accounts and currencies must be extracted before the user can configure mappings). The output specification is precise and the data flow diagram is clear. However, there are several gaps: one P0 requirement is missing from the design, the CSV metadata handling contradicts between the PRD and the spec, the `/upload` response schema is underspecified, and there are a few areas where the engineer will need to make decisions that should have been made in the design.

---

## Verdict

**Status:** REVISION_NEEDED
**Issue Type:** DESIGN_ISSUE
**Route To:** system-architect
**Iteration:** 1 of 2

---

## Critical (Must Fix)

### 1. FR-005 (Configurable header/data row positions) is missing from the design

The PRD explicitly includes FR-005 as a Phase 1 requirement: users should be able to configure the header start row (default 27) and data start row (default 28). The sister project already supports this via `input_header_start` and `input_data_start` Form parameters on the `/upload` endpoint. The implementation brief mentions these defaults in the "What's Reused" section (line 12) but never surfaces them in the new endpoint design, the `InputPanel.vue` component, or the `POST /upload` request spec. The engineer needs to know:

- Does `/upload` accept `input_header_start` and `input_data_start` as optional form fields (like the sister project)?
- Does the UI expose these as advanced/collapsible inputs, or are they hidden and defaulted?

**Action:** Add `input_header_start` and `input_data_start` as optional parameters on `POST /upload` with defaults of 27/28. Decide whether the UI exposes them (recommended: collapsible "Advanced" section in `UploadSection.vue`, same as sister project pattern).

### 2. FR-010 (Sort output by Account Number ascending) is not mentioned in the design

The PRD requires sorted output rows per worksheet. The implementation brief's output table and `fx_processor.py` description never mention sorting. The engineer may miss this.

**Action:** Add a note in the "Output Excel Structure" section or the `fx_processor.py` file description that output rows must be sorted by Account Number ascending within each worksheet before writing.

### 3. CSV metadata handling is contradictory

FR-024 in the PRD says: "For CSV files, the system shall auto-detect the header row or assume row 1 as headers (no metadata rows)." This means CSV files have NO rows 1-26 metadata. But the implementation brief's `ctr_reader.py` description (line 58) says it handles both Excel and CSV with "extract metadata from rows 1-26." The engineer will hit an immediate conflict when implementing CSV support.

**Action:** Clarify in `ctr_reader.py` description that metadata extraction (rows 1-26) applies only to Excel files. For CSV files, headers are at row 1 (or auto-detected), data starts at row 2, and metadata fields (fiscal year, period, company currency) must either be inferred from the data columns or left blank with a warning to the user. This affects the `/upload` response — `company_currency` and `metadata` may be null/partial for CSV uploads.

---

## Major (Should Fix)

### 4. `/upload` response schema is underspecified

The brief says `/upload` returns `{ job_id, accounts: [...], currencies: [...], company_currency: "MXN", metadata: {...} }` but does not define the shape of objects in `accounts[]` or `metadata{}`. The engineer needs to know:

- Is `accounts` a list of `{ account_number: str, account_name: str }` objects, or just account numbers?
- What fields are in `metadata`? The PRD lists fiscal year, fiscal period, accounting standard, contract currency, company currency, company code — are all of these returned?

**Action:** Define the response schema explicitly, ideally as a Pydantic model in the `schemas.py` section. For example:
```
UploadResponse:
  job_id: str
  accounts: list[{ account_number: str, account_name: str }]
  currencies: list[str]
  company_currency: str | null
  metadata: { fiscal_year: str, fiscal_period: str, accounting_standard: str, company_code: str }
```

### 5. FR-015 (Output file naming pattern) is not addressed

The PRD specifies: `CTR_FX_Remeasurement_{FiscalYear}_{FiscalPeriod}_{Timestamp}.xlsx`. The implementation brief's `/download/{job_id}` section doesn't specify the download filename. The sister project uses `poliza_ledger_{timestamp}.zip` — the new tool needs its own pattern. The fiscal year and period come from the metadata extracted in Step 1, so they need to be persisted in the job state for use at download time.

**Action:** Specify the download filename pattern and note that `fiscal_year` and `fiscal_period` from the upload step must be stored in the job state for use in the download response's `filename` parameter.

### 6. FR-019 (Specific, actionable error messages) — error contract not defined

The PRD lists four specific error categories (missing columns, insufficient rows, currency parsing errors, invalid numeric values with row/column reference). The implementation brief mentions `ErrorSection.vue` is "reused as-is" but doesn't define what error payload the backend returns. The sister project returns a simple `error: str` in `JobStatus`. The new tool needs structured error responses for the engineer to implement FR-019.

**Action:** Define an error response shape, e.g.:
```
error: { type: str, message: str, details: list[{ row: int, column: str, value: str, reason: str }] }
```
Or at minimum, note that `JobStatus.error` should be replaced with a structured error object for this project.

### 7. No mention of FR-011 (duplicate/missing Account Name handling)

FR-011 says: "If a name is missing, it shall be left blank or default to dash." The brief says "Account Name: CTR grouping key (first occurrence)" in the output table but doesn't specify what happens when Account Name is null/empty in the source data, or when the same Account Number has different Account Names across rows.

**Action:** Add a note in the "Unmapped Account Handling" section or create a parallel "Data Quality Handling" section that addresses: (a) missing Account Name defaults to "--", (b) conflicting Account Names for the same Account Number uses first occurrence and logs a warning.

---

## Minor (Consider)

### 8. Account mapping persistence across sessions

The brief describes account mapping as a per-session inline table. For a client like Abbott who runs this tool every period, they will re-enter the same 7 account mappings every time. Consider noting this as a Phase 2 enhancement (localStorage save/restore or CSV import fallback) so the engineer doesn't over-build it now but architects the data flow to be extensible.

### 9. The `/process/{job_id}` endpoint should validate that the job exists and is in the right state

The brief doesn't mention what happens if someone calls `/process/{job_id}` with a non-existent job ID or a job that's already processing/completed. The sister project doesn't have this two-step flow so there's no pattern to copy. A quick note about expected HTTP error codes (404 for missing job, 409 for already-processing) would help.

### 10. Template header/data start parameters from the sister project

The sister project's `ProcessingRequest` has `template_header_start` and `template_data_start` (output formatting parameters). These are irrelevant for the FX tool since FR-013 mandates "headers in row 1, data from row 2." The brief should explicitly state these are NOT carried over, to prevent the engineer from copying them.

### 11. FR-014 (Numeric precision) not explicitly addressed

The brief doesn't mention decimal precision handling. Pandas floats and openpyxl default formatting should handle this naturally, but a note about number formatting (at least 2 decimal places, matching the sister project's `CELL_NUMBER_FORMAT` pattern) would prevent the engineer from shipping raw float output.

---

## Well Done

- **Two-step flow rationale is excellent.** The brief clearly explains WHY the sister project's single-step upload doesn't work here (Step 2 depends on data extracted in Step 1) and provides a clean alternative with the `/upload` + `/process/{job_id}` split.
- **Inline table for account mapping is the right call.** For 5-30 accounts, a file upload would be friction. The auto-populated table with dropdowns is a smart UX decision that the PRD left as "TBD."
- **Exchange rate input design is pragmatic.** Auto-detecting currencies from the CTR and presenting "1 [Currency] = [___] [Company Currency]" is clean and avoids a separate file upload for 2-5 currency pairs.
- **Fallback behavior is well-defined.** The partial output behavior (columns 1-2, 5-7 populated even without mapping; warning banners for unmapped accounts) is a good graceful degradation pattern.
- **Clear "What's Reused" vs "What's New" separation.** This makes it easy for the engineer to know what to clone and what to build from scratch.
- **Single .xlsx output (no ZIP) is the right simplification** for Phase 1 where the output is one workbook with currency sheets rather than one file per company code.
- **The data flow diagram is clear and complete** — it traces the full request/response lifecycle from upload through processing to download.

---

## Specific Feedback for Revision

For the system-architect revising this document:

1. **Add FR-005 support**: Add `input_header_start` (default 27) and `input_data_start` (default 28) as optional parameters on `POST /upload`. Note whether the UI exposes them (recommend: collapsible "Advanced" section in `UploadSection.vue`).

2. **Add FR-010 sorting note**: In the "Output Excel Structure" section, add: "Rows within each worksheet are sorted by Account Number ascending (FR-010)."

3. **Fix CSV metadata contradiction**: In the `ctr_reader.py` file description, clarify that metadata extraction from rows 1-26 is Excel-only. For CSV, headers are row 1, data starts row 2, and metadata fields (company_currency, fiscal_year, etc.) are either inferred from data columns or returned as null with a user-facing warning.

4. **Define `/upload` response schema**: Add a Pydantic model or explicit field-level definition for the upload response, including the shape of `accounts[]` and `metadata{}`.

5. **Specify download filename pattern**: Add `CTR_FX_Remeasurement_{FiscalYear}_{FiscalPeriod}_{Timestamp}.xlsx` and note that fiscal year/period from the upload step must be persisted in job state.

6. **Define error response structure**: Replace the simple `error: str` with a structured error object that supports FR-019's four error categories.

7. **Add data quality handling notes**: Address FR-011 (missing/conflicting Account Names) explicitly.

8. **Explicitly drop `template_header_start` / `template_data_start`**: Note these sister project parameters are not carried over since output format is fixed.

---

## Artifacts Reviewed
- `C:/workarea/maturity_analysis_report/docs/technical-specification.md`
- `C:/workarea/maturity_analysis_report/docs/product-requirements.md`
- `C:/workarea/maturity_analysis_report/webapp/backend/app.py`
- `C:/workarea/maturity_analysis_report/webapp/backend/services/excel_processor.py`
- `C:/workarea/maturity_analysis_report/webapp/backend/services/formula_mapper.py`
- `C:/workarea/maturity_analysis_report/webapp/backend/models/schemas.py`
