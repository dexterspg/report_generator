# Proof of Concept: CTR FX Remeasurement Tool

**Ticket:** LAE-44136 (Abbott Laboratories)
**Version:** 2.0
**Date:** 2026-03-23
**Author:** Implementation Team
**Status:** Draft

---

## 1. Executive Summary

Multi-currency clients such as Abbott Laboratories currently perform FX remeasurement manually in Excel every fiscal period — a high-risk, error-prone process that directly affects financial statements under IFRS 16 and GAAP. This PoC validates that the core calculation engine can be automated reliably: parse a Nakisa CTR, aggregate closing balances, apply period-end exchange rates, and produce the correct FX (Gain) or Loss per GL account.

If the PoC passes, the result is a standalone desktop tool that eliminates the manual pivot process entirely. Abbott's implementation team will validate the output against their existing verified P1 worksheet — if values match, the Go decision is made to build the full application.

---

## 2. Problem Statement

**The problem:** Multi-currency lease clients must calculate FX remeasurement every fiscal period to comply with IFRS 16 / GAAP. This is done entirely in Excel through a four-step manual process:

1. Export the CTR from Nakisa Lease Administration
2. Manually pivot the CTR to aggregate closing balances by GL account and currency
3. Manually apply period-end exchange rates
4. Manually calculate FX gain/loss per account

**Who is affected:** Abbott Laboratories finance team; any Nakisa client with multi-currency lease portfolios.

**Current state:** Fully manual. Every fiscal period, a finance team member spends significant time performing the pivot and calculation in Excel with no automated checks.

**Impact of not solving:** Calculation errors go undetected until financial close review. Manual rework is required each period. Risk of misstatement on financial reports filed under IFRS 16 / GAAP.

---

## 3. Proposed Solution

A standalone desktop application that automates the end-to-end FX remeasurement process:

1. Accepts a Nakisa CTR Excel export as input
2. Reads account type (BS/P&L) and monetary flag from a client-supplied mapping file
3. Reads period-end spot rates from a client-supplied exchange rates file
4. Produces an output workbook with one worksheet per currency showing the FX (Gain) or Loss per GL account — the primary deliverable

**Key capabilities:**
- Automated CTR parsing with column validation
- Closing balance aggregation by account and contract currency
- FX calculation: Re-measured Balance = Balance in Contract Currency × Period-End Spot Rate
- Multi-sheet output organized by currency
- Unmapped accounts flagged clearly rather than silently dropped

---

## 4. Goals & Objectives

| Goal | Measurable Outcome |
|------|--------------------|
| Validate calculation correctness | FX (Gain) or Loss values match Abbott's manually verified "3. CTR Pivot P1" worksheet for `CTR_0422.xlsx` |
| Validate aggregation logic | Closing balance sums per `{Account, Currency}` group reconcile row-by-row against the source CTR |
| Validate non-monetary handling | Non-monetary accounts produce FX = 0 in output |
| Validate output structure | One sheet per unique Contract Currency, named by currency code |
| Validate performance | Processing completes in under 10 seconds for `CTR_0422.xlsx` |

---

## 5. Scope

**In scope:**
- CTR parsing: metadata rows 1–26, headers row 27, data from row 28
- Column validation: detect and reject files missing required columns
- Closing balance aggregation grouped by `{Account Number, Account Name, Contract Currency}`
- Account mapping input: account type (BS/P&L) and monetary flag (Yes/No)
- Exchange rate input: period-end spot rates per currency
- FX calculation and multi-sheet output
- Validation against Abbott's P1 manual pivot for `CTR_0422.xlsx`

**Out of scope for PoC:**
- Desktop `.exe` packaging (PyInstaller)
- Web-based UI (Vue.js frontend)
- Configuration history and rollback
- Prior period FX carryforward
- P&L account exclusion
- Multi-company output

**Assumptions:**
- CTR column names follow the Nakisa standard format
- Abbott will supply the account mapping and P1 exchange rates
- Abbott's "3. CTR Pivot P1" worksheet is the authoritative expected output

---

## 6. Required Resources

| Resource | Details |
|----------|---------|
| People | 1 implementation engineer (build + test); Abbott finance contact (data supply + sign-off) |
| Tools / Systems | Python 3.x, pandas, openpyxl; access to `CTR_0422.xlsx` |
| Data | `CTR_0422.xlsx`, account mapping file, P1 exchange rates file, Abbott's manual pivot worksheet |
| Budget | Minimal — existing tooling and licenses; no new spend required |
| Time | Estimated 3–5 days to build and validate |

---

## 7. Success Criteria

The PoC is considered **passed** when all of the following are met:

| # | Criterion | How Verified |
|---|-----------|-------------|
| SC-01 | FX (Gain) or Loss values match Abbott's "3. CTR Pivot P1" worksheet | Side-by-side comparison by Abbott implementation team |
| SC-02 | Closing balance aggregation correctly sums all CTR rows per `{Account, Currency}` | Row-by-row reconciliation against source CTR |
| SC-03 | Non-monetary accounts show FX (Gain) or Loss = 0 | Output inspection |
| SC-04 | Output workbook contains one sheet per unique Contract Currency, named by currency code | File inspection |
| SC-05 | Accounts missing from the mapping produce "N/A" in type/monetary columns and blank in FX columns | Output inspection with partial mapping file |
| SC-06 | Processing completes in under 10 seconds for `CTR_0422.xlsx` | Timed run |

The PoC is considered **failed** if:
- FX values do not match Abbott's manual pivot after mapping and rate files are confirmed correct
- CTR structure is inconsistent enough that parsing cannot be reliably automated
- Abbott's account mapping cannot be supplied in time to run the validation

---

## 8. Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| CTR column names differ from Nakisa standard | Low | High | Confirm column names against `CTR_0422.xlsx` before PoC run |
| Abbott's account mapping is incomplete | Medium | Medium | Flag unmapped accounts in output; Abbott fills in gaps before sign-off |
| Exchange rates for P1 not yet available | Low | High | Use P1 rates from Abbott's existing manual worksheet |
| Metadata row count varies by export settings | Low | Medium | Configurable `input_header_start` parameter (default: row 27) |
| Non-standard currency codes in CTR | Low | Low | Normalize to uppercase; non-standard codes produce a warning, not a failure |

---

## 9. Timeline & Milestones

| Milestone | Target Date |
|-----------|------------|
| Abbott supplies CTR, mapping, and rates files | 2026-03-25 |
| PoC build complete (parser + calculator + output) | 2026-03-27 |
| Internal validation run | 2026-03-28 |
| Abbott review and sign-off | 2026-03-31 |
| Go / No-Go decision | 2026-04-01 |

---

## 10. Stakeholders

| Name / Role | Responsibility |
|-------------|---------------|
| Abbott Finance Contact | Supplies input files; validates output against manual pivot; provides sign-off |
| Implementation Engineer | Builds and runs the PoC; documents results |
| Implementation Manager | Go/No-Go decision maker |
| Abbott Project Sponsor | Informed of outcome; approves next phase if Go |

---

## 11. Technical Reference

### Processing Pipeline

```
CTR File (.xlsx)
      │
      ▼
 ctr_reader.py
  - Extract metadata (rows 1–26)
  - Read headers (row 27)
  - Validate 9 required columns
  - Normalize currencies to uppercase
  - Coerce numeric amounts; skip/warn bad rows
      │
      ▼
 fx_processor.py
  - Group by {Account Number, Account Name, Contract Currency}
  - Aggregate balance_cc and initial_measurement
  - Apply account type + monetary flag from mapping
  - Apply spot rate from exchange rates config
  - Re-measured Balance = balance_cc × spot_rate (monetary)
                        = initial_measurement (non-monetary)
  - FX (Gain)/Loss = Re-measured Balance − Initial Measurement
  - Write one worksheet per currency (sorted by Account Number)
      │
      ▼
 CTR_FX_Remeasurement_{FY}_{FP}_{Timestamp}.xlsx
```

### Key Formula

| Account Type | Re-measured Balance | FX (Gain) or Loss |
|---|---|---|
| Monetary | Balance in Contract Currency × Period-End Spot Rate | Re-measured Balance − Initial Measurement |
| Non-Monetary | Initial Measurement (unchanged — historical rate preserved) | 0 |
| Unmapped | Blank | Blank |

### Example Calculation

| Input | Value |
|---|---|
| Balance in Contract Currency | 10,000 USD |
| Initial Measurement (Company Currency) | 130,000 MXN |
| Period-End Spot Rate | 14.0 |
| **Re-measured Balance** | **140,000 MXN** |
| **FX (Gain) or Loss** | **10,000 MXN** |

---

## 12. Recommendation

**Go — pending Abbott sign-off**

The problem is well-defined, the calculation logic is deterministic, and the expected output (Abbott's manual pivot) is already available for validation. The implementation risk is low. If the PoC run confirms that calculated FX values match Abbott's manual worksheet, the decision is to proceed immediately to building the full desktop application (FastAPI backend + Vue 3 frontend + PyInstaller packaging).

---

**Document Status:** Draft
**Last Updated:** 2026-03-23
