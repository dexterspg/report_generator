# Maturity Analysis Report - Column Mapping

## Overview

This document maps columns from the source data (`Consolidated Financial Schedules.xlsx`) to the output report (`maturity_analysis_report.xlsx`) using logic derived from `MaturityAnalysisReport.java`.

**Source File**: `Consolidated Financial Schedules.xlsx`
- Header Row: 8 (0-indexed: 7)
- Data Start Row: 9 (0-indexed: 8)

**Output File**: `maturity_analysis_report.xlsx`
- Header Row: 31 (0-indexed: 30)
- Data Start Row: 32 (0-indexed: 31)

---

## Output Report Structure

The output has **51 columns** organized into:
- **Columns 1-24**: Contract/AG metadata
- **Columns 25-37**: Financial values in **Contract Currency**
- **Columns 38-51**: Financial values in **Target Currency** (same structure, currency converted)

**Time Buckets**: Year 1-6 + Thereafter (7 buckets total)

---

## Section 1: Contract/AG Metadata (Columns 1-24)

| # | Output Column | Source Column | Transformation |
|---|---------------|---------------|----------------|
| 1 | Erp System ID | `System` | Direct copy |
| 2 | Contract ID | `Contract ID` | Direct copy |
| 3 | Internal Contract Reference | `Internal Reference Number` | Direct copy |
| 4 | External Contract Reference | `External Reference number` | Direct copy |
| 5 | Contract Name | `Contract Name` | Direct copy |
| 6 | Company Code | `Company Code` | Direct copy |
| 7 | Business Unit | `Business Unit` | Direct copy |
| 8 | Trading Partner ID | `Trading Partner` | Direct copy |
| 9 | Trading Partner Name | (Not in source) | Leave blank |
| 10 | Profit Center | `Unit Profit Center (Main)` | Direct copy |
| 11 | Cost Center | `Unit Cost Center (Main)` | Direct copy |
| 12 | Responsible Cost Center | (Not in source) | Leave blank |
| 13 | Activation Group ID | `Activation Group ID` | Direct copy |
| 14 | Lease Classification | (Derived) | Default: "FINANCE" |
| 15 | Activation Group Status | `Activation Group Status` | Direct copy |
| 16 | Accounting Start Date | `Activation Date` | Direct copy |
| 17 | Likely Expiration Date | `End Date` | Direct copy |
| 18 | Accounting Term In Months | `Activation Date`, `End Date` | Calculated: months between dates |
| 19 | Accounting Term In Days | `Activation Date`, `End Date` | Calculated: remaining days |
| 20 | Contract Currency | `Contract Currency` | Direct copy |
| 21 | Target Currency | (User input or same as Contract) | Report parameter, default to Contract Currency |
| 22 | Exchange Rate To LC | (Lookup/Default) | Default: 1.0 |
| 23 | Exchange Rate To GC/RC | (Lookup/Default) | Default: 1.0 |
| 24 | Asset Class | `Unit Internal Asset Class` | Direct copy |

---

## Section 2: Financial Values - Contract Currency (Columns 25-37)

| # | Output Column | Source Column | Transformation Logic |
|---|---------------|---------------|---------------------|
| 25 | Year 1 | `Payment` | Sum where `0 < period_count <= 1` |
| 26 | Year 2 | `Payment` | Sum where `1 < period_count <= 2` |
| 27 | Year 3 | `Payment` | Sum where `2 < period_count <= 3` |
| 28 | Year 4 | `Payment` | Sum where `3 < period_count <= 4` |
| 29 | Year 5 | `Payment` | Sum where `4 < period_count <= 5` |
| 30 | Year 6 | `Payment` | Sum where `5 < period_count <= 6` |
| 31 | Thereafter | `Payment` | Sum where `period_count > 6` |
| 32 | Total | (Calculated) | `Year1 + Year2 + Year3 + Year4 + Year5 + Year6 + Thereafter` |
| 33 | Less: Finance Charges | `Interest Paid` | Sum of `abs(Interest Paid)` for future periods, output as **negative** |
| 34 | Total Principal Liability | (Calculated) | `Total + Less: Finance Charges` |
| 35 | ST Principal Closing Balance | `ST Principal Liability Closing Balance` | Value at report period end only |
| 36 | LT Principal Closing Balance | `Principal Liability LT Closing Balance` | Value at report period end only |
| 37 | Total Principal Liability | (Calculated) | `ST Principal + LT Principal` |

---

## Section 3: Financial Values - Target Currency (Columns 38-51)

| # | Output Column | Transformation |
|---|---------------|----------------|
| 38 | Asset Class | Direct copy from column 24 |
| 39 | Year 1 | `Year1_Contract * Exchange_Rate` |
| 40 | Year 2 | `Year2_Contract * Exchange_Rate` |
| 41 | Year 3 | `Year3_Contract * Exchange_Rate` |
| 42 | Year 4 | `Year4_Contract * Exchange_Rate` |
| 43 | Year 5 | `Year5_Contract * Exchange_Rate` |
| 44 | Year 6 | `Year6_Contract * Exchange_Rate` |
| 45 | Thereafter | `Thereafter_Contract * Exchange_Rate` |
| 46 | Total | `Total_Contract * Exchange_Rate` |
| 47 | Less: Finance Charges | `FinanceCharges_Contract * Exchange_Rate` |
| 48 | Total Principal Liability | `Total + Finance Charges` (Target Currency) |
| 49 | ST Principal Closing Balance | `ST_Principal_Contract * Exchange_Rate` |
| 50 | LT Principal Closing Balance | `LT_Principal_Contract * Exchange_Rate` |
| 51 | Total Principal Liability | `ST + LT` (Target Currency) |

---

## Time Bucketing Formula

The **Report Date** (user-provided year + month) is the reference point for bucketing:

```python
def calculate_period_bucket(payment_date, report_year, report_month):
    """
    Determine which year bucket a payment belongs to.

    The report date (year + month) is the reference point.
    Year 1 starts from the month AFTER the report date:
    - Year 1 = months 1-12 after report date
    - Year 2 = months 13-24 after report date
    - ... and so on
    - Thereafter = beyond 72 months (6 years)

    Args:
        payment_date: Date when payment is due (Period End Date)
        report_year: Report year (e.g., 2024)
        report_month: Report month (1-12)

    Returns:
        str: Bucket name ('skip', 'year1'-'year6', 'thereafter')
    """
    # Calculate months difference from report date to payment date
    months_diff = ((payment_date.year - report_year) * 12 +
                   (payment_date.month - report_month))

    if months_diff <= 0:
        return 'skip'      # Payment is at or before report date - ignore
    elif months_diff <= 12:
        return 'year1'     # Months 1-12 after report date
    elif months_diff <= 24:
        return 'year2'     # Months 13-24 after report date
    elif months_diff <= 36:
        return 'year3'     # Months 25-36
    elif months_diff <= 48:
        return 'year4'     # Months 37-48
    elif months_diff <= 60:
        return 'year5'     # Months 49-60
    elif months_diff <= 72:
        return 'year6'     # Months 61-72
    else:
        return 'thereafter' # Beyond 72 months
```

### Example

If Report Date is **December 2022** (report_year=2022, report_month=12):

| Period End Date | Months After Report Date | Bucket |
|-----------------|-------------------------|--------|
| Dec 2022 | 0 | skip |
| Jan 2023 | 1 | year1 |
| Dec 2023 | 12 | year1 |
| Jan 2024 | 13 | year2 |
| Dec 2024 | 24 | year2 |
| Jan 2025 | 25 | year3 |
| Dec 2028 | 72 | year6 |
| Jan 2029 | 73 | thereafter |

### Filtering

Contracts/AGs where ALL Period End Dates are at or before the report date are **excluded** from the output (they have no future payments to report).

---

## Aggregation Key

Each output row represents one **Contract + Activation Group** combination:

```python
aggregation_key = f"{contract_id}_{activation_group_id}"
```

---

## Principal Balance Extraction

Only extract when `Period End Date` matches report period end:

```python
if period_end_date.year == report_year and period_end_date.month == report_month:
    st_principal = row['ST Principal Liability Closing Balance']
    lt_principal = row['Principal Liability LT Closing Balance']
```

---

## Interest (Finance Charges) Extraction

Sum for all periods AFTER report date, output as negative:

```python
if period_end_date > report_date:
    finance_charges += abs(row['Interest Paid'])
# Output: -finance_charges (negative value)
```

---

## Term Calculation

```python
from dateutil.relativedelta import relativedelta
from datetime import timedelta

def calculate_term(start_date, end_date):
    """Calculate lease term in months and remaining days"""
    if pd.isna(start_date) or pd.isna(end_date):
        return 0, 0
    rd = relativedelta(end_date + timedelta(days=1), start_date)
    months = rd.years * 12 + rd.months
    days = rd.days
    return months, days
```

---

## Data Flow Summary

```
Consolidated Financial Schedules.xlsx (multiple rows per contract/AG/period)
    │
    ├── Group by: Contract ID + Activation Group ID
    │
    ├── For each group:
    │   ├── Extract metadata from first row
    │   ├── Aggregate: Payments → Year 1-6 + Thereafter buckets
    │   ├── Aggregate: Interest Paid → Less: Finance Charges (negative)
    │   ├── Snapshot: Principal balances at period end
    │   └── Calculate: Totals, Term in months/days
    │
    ▼
maturity_analysis_report.xlsx (one row per contract/AG)
```

---

## Source Column Reference

| Source Column | Used For |
|---------------|----------|
| System | Erp System ID |
| Contract ID | Contract ID, Aggregation key |
| Internal Reference Number | Internal Contract Reference |
| External Reference number | External Contract Reference |
| Contract Name | Contract Name |
| Company Code | Company Code |
| Business Unit | Business Unit |
| Trading Partner | Trading Partner ID |
| Unit Profit Center (Main) | Profit Center |
| Unit Cost Center (Main) | Cost Center |
| Activation Group ID | Activation Group ID, Aggregation key |
| Activation Group Status | Activation Group Status |
| Activation Date | Accounting Start Date, Term calculation |
| End Date | Likely Expiration Date, Term calculation |
| Contract Currency | Contract Currency |
| Unit Internal Asset Class | Asset Class |
| Period End Date | Time bucket determination, Period filtering |
| Payment | Year 1-6, Thereafter buckets |
| Interest Paid | Less: Finance Charges |
| ST Principal Liability Closing Balance | ST Principal Closing Balance |
| Principal Liability LT Closing Balance | LT Principal Closing Balance |
