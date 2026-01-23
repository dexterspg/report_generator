# Maturity Analysis Report - Mapping Logic Documentation

## Overview

This document describes the mapping logic from the Java `MaturityAnalysisReport.java` class to be implemented in Python. The maturity analysis report shows **when lease payments are due** over time, grouped into year buckets (Year 1-5 and Thereafter).

### Purpose (ASC 842/IFRS 16 Compliance)
- **Regulatory Compliance**: Required disclosure for financial statements
- **Cash Flow Planning**: Shows future payment obligations
- **Financial Transparency**: Investors can see lease commitments

---

## Source Data: Consolidated Financial Schedules.xlsx

### File Structure
- **Header Row**: Row 8 (0-indexed: row 7)
- **Data Start Row**: Row 9 (0-indexed: row 8)

### Key Source Columns

| Column Name | Data Type | Description | Usage |
|-------------|-----------|-------------|-------|
| `System` | String | Source system identifier | Filtering |
| `Lease Area` | String | Lease area classification | Filtering |
| `Business Unit` | String | Business unit code | Filtering |
| `Company Code` | String | Company identifier | Filtering, Exchange rates |
| `Trading Partner` | String | Trading partner code | Display |
| `Contract ID` | String | Unique contract identifier | Aggregation key |
| `Contract Name` | String | Contract description | Display |
| `Lease Component ID` | String | Lease component identifier | Hierarchy navigation |
| `Activation Group ID` | String | Activation group identifier | Aggregation key (combined with Contract ID) |
| `Activation Group Status` | String | Status (Active, Lease End, etc.) | Filtering |
| `Unit ID` | String | Unit identifier | Hierarchy navigation |
| `Unit Cost Center (Main)` | String | Cost center | Display |
| `Unit Profit Center (Main)` | String | Profit center | Display |
| `Activation Date` | Date | Lease start date | Term calculation |
| `End Date` | Date | Lease end date | Term calculation, Skip logic |
| `Contract Currency` | String | Original currency | Currency conversion |
| `Company Currency` | String | Local currency | Exchange rate calculation |
| `Period` | Integer | Period number within schedule | Row identification |
| `Period Start Date` | Date | Period start | Filtering |
| `Period End Date` | Date | Period end | **Critical for time bucketing** |
| `Payment` | Float | `minimumLeasePaymentPerUnit` equivalent | **Main value for year buckets** |
| `Interest Paid` | Float | `postingMonthEndInterestPaid` equivalent | Interest calculation |
| `Principal Liability Closing Balance` | Float | Total principal liability | Balance snapshot |
| `ST Principal Liability Closing Balance` | Float | Short-term principal | Period-end snapshot |
| `Principal Liability LT Closing Balance` | Float | Long-term principal (LT = reportLTPrincipalLiabilityClosingBalance) | Period-end snapshot |

---

## Java Class Logic Breakdown

### 1. Entity Hierarchy (Data Flow)

```
DT_Contract (Top Level)
    └── DT_ContractLeaseComponent
        └── DT_ActivationGroup
            └── DT_Unit
                └── DT_Schedule
                    └── DT_ScheduleLineItem (Financial Data)
```

**Python Equivalent**: In the Excel file, each row represents a flattened combination of this hierarchy. The unique key is:
```python
aggregation_key = f"{contract_id}{activation_group_id}"
```

### 2. Report Parameters (User Inputs)

The Java class receives these as `reportArgs`:

| Parameter | Java Name | Description | Example |
|-----------|-----------|-------------|---------|
| Report Period End Year | `yearEnd` | Year of report date | 2024 |
| Report Period End Month | `periodEnd` | Month of report date | 12 |
| Target Currency | `targetCurrency` | Currency for aggregation | "USD" |
| Currency Type | `currencyType` | Rate type (30=Month-end, etc.) | "30" |
| Company Filter | `selectedCompanies` | Companies to include | ["1000", "2000"] |
| Lease Area Filter | `selectedLeaseArea` | Lease areas to include | ["0001"] |
| AG Status Filter | `agStatuses` | Activation group statuses | ["Active", "Lease End"] |

### 3. Time Period Bucketing Algorithm

This is the **core logic** of the maturity analysis:

```python
def calculate_period_bucket(payment_date, report_year_end, report_period_end):
    """
    Determine which year bucket a payment belongs to.

    Args:
        payment_date: Date when payment is due
        report_year_end: Year of the report date (e.g., 2024)
        report_period_end: Month of the report date (e.g., 12 for December)

    Returns:
        str: Bucket name ('skip', 'year1', 'year2', 'year3', 'year4', 'year5', 'thereafter')
    """
    payment_year = payment_date.year
    payment_month = payment_date.month

    # Calculate period count (number of 12-month periods from report date)
    period_count = ((payment_year - report_year_end) * 12 + (payment_month - report_period_end)) / 12.0

    if period_count <= 0:
        return 'skip'  # Payment is before or at report date
    elif period_count > 0 and period_count <= 1:
        return 'year1'
    elif period_count > 1 and period_count <= 2:
        return 'year2'
    elif period_count > 2 and period_count <= 3:
        return 'year3'
    elif period_count > 3 and period_count <= 4:
        return 'year4'
    elif period_count > 4 and period_count <= 5:
        return 'year5'
    else:  # period_count > 5
        return 'thereafter'
```

**Example Calculations**:
```
Report Date: December 31, 2024 (yearEnd=2024, periodEnd=12)

Payment Date: March 15, 2025
  period_count = ((2025 - 2024) * 12 + (3 - 12)) / 12.0 = (12 - 9) / 12 = 0.25
  Result: year1 (0 < 0.25 <= 1)

Payment Date: January 15, 2026
  period_count = ((2026 - 2024) * 12 + (1 - 12)) / 12.0 = (24 - 11) / 12 = 1.08
  Result: year2 (1 < 1.08 <= 2)

Payment Date: June 15, 2030
  period_count = ((2030 - 2024) * 12 + (6 - 12)) / 12.0 = (72 - 6) / 12 = 5.5
  Result: thereafter (5.5 > 5)
```

### 4. Principal Balance Extraction Logic

Principal balances are extracted **only at the report period end**:

```python
def extract_principal_balances(row, report_year_end, report_period_end):
    """
    Extract principal balances only if the row matches the report period end.

    In Java: Lines 293-314 of MaturityAnalysisReport.java
    """
    posting_end_date = parse_date(row['Period End Date'])

    if (posting_end_date.year == report_year_end and
        posting_end_date.month == report_period_end):
        return {
            'st_principal': row.get('ST Principal Liability Closing Balance', 0.0),
            'lt_principal': row.get('Principal Liability LT Closing Balance', 0.0)
        }
    return None
```

### 5. Interest Calculation Logic

Interest is summed for **all periods after the report date**:

```python
def extract_interest(row, report_year_end, report_period_end):
    """
    Extract interest paid for future periods.
    Interest is stored as negative in DB, so we use abs().

    In Java: Lines 316-326 of MaturityAnalysisReport.java
    """
    posting_end_date = parse_date(row['Period End Date'])

    if (posting_end_date.year > report_year_end or
        (posting_end_date.year == report_year_end and
         posting_end_date.month > report_period_end)):
        # Interest is stored as negative, convert to positive
        return abs(row.get('Interest Paid', 0.0))
    return 0.0
```

### 6. Currency Conversion

```python
def convert_currency(amount, exchange_rate):
    """
    Convert amount from contract currency to target currency.

    In Java: Applied when exchangeRate != null (Lines 303-313, 338-388)
    """
    if exchange_rate is not None and amount is not None:
        return amount * exchange_rate
    return None
```

---

## Output Report Structure

### Section 1: Asset Class Summary (Aggregated by Asset Class)

| Output Column | Source | Formula |
|---------------|--------|---------|
| Asset Class | Derived from `Unit Internal Asset Class` | Group by key |
| Year 1 | `Payment` | Sum where period_count ∈ (0, 1] |
| Year 2 | `Payment` | Sum where period_count ∈ (1, 2] |
| Year 3 | `Payment` | Sum where period_count ∈ (2, 3] |
| Year 4 | `Payment` | Sum where period_count ∈ (3, 4] |
| Year 5 | `Payment` | Sum where period_count ∈ (4, 5] |
| Thereafter | `Payment` | Sum where period_count > 5 |
| Total | Calculated | Year1 + Year2 + Year3 + Year4 + Year5 + Thereafter |
| Interest Paid | `Interest Paid` | Sum(abs(value)) for future periods |
| Total Principal (Method 1) | Calculated | Total - Interest Paid |
| ST Principal Balance | `ST Principal Liability Closing Balance` | Sum at period end only |
| LT Principal Balance | `Principal Liability LT Closing Balance` | Sum at period end only |
| Total Principal (Method 2) | Calculated | ST Principal + LT Principal |

### Section 2: Contract Listing (Detailed by Contract + Activation Group)

**Contract Info Columns:**
| Output Column | Source Column |
|---------------|---------------|
| Contract ID | `Contract ID` |
| External Contract ID | `External Reference number` or `Contract ID` |
| Contract Name | `Contract Name` |
| Company Code | `Company Code` |
| Profit Center | `Unit Profit Center (Main)` |
| Cost Center | `Unit Cost Center (Main)` |
| Business Unit | `Business Unit` |
| Trading Partner | `Trading Partner` |
| Activation Group ID | `Activation Group ID` |
| AG Status | `Activation Group Status` |
| Start Date | `Activation Date` |
| End Date | `End Date` |
| Contract Currency | `Contract Currency` |
| Target Currency | (User input) |
| Asset Class | `Unit Internal Asset Class` |

**Financial Columns (Contract Currency):**
- Same year buckets as Asset Class Summary, but aggregated by Contract+AG

**Financial Columns (Target Currency):**
- Same calculations converted using exchange rate

---

## Aggregation Maps (Python Implementation)

```python
from collections import defaultdict

class MaturityAnalysisAggregator:
    def __init__(self):
        # Asset Class Level (converted to target currency)
        self.agg_year1 = defaultdict(float)
        self.agg_year2 = defaultdict(float)
        self.agg_year3 = defaultdict(float)
        self.agg_year4 = defaultdict(float)
        self.agg_year5 = defaultdict(float)
        self.agg_thereafter = defaultdict(float)
        self.agg_interest_paid = defaultdict(float)
        self.agg_st_principal = defaultdict(float)
        self.agg_lt_principal = defaultdict(float)

        # Contract Level (contract currency)
        self.agg_year1_by_contract = defaultdict(float)
        self.agg_year2_by_contract = defaultdict(float)
        self.agg_year3_by_contract = defaultdict(float)
        self.agg_year4_by_contract = defaultdict(float)
        self.agg_year5_by_contract = defaultdict(float)
        self.agg_thereafter_by_contract = defaultdict(float)
        self.agg_interest_paid_by_contract = defaultdict(float)
        self.agg_st_principal_by_contract = defaultdict(float)
        self.agg_lt_principal_by_contract = defaultdict(float)

        # Contract Level (target currency)
        self.agg_year1_by_contract_target = defaultdict(float)
        self.agg_year2_by_contract_target = defaultdict(float)
        self.agg_year3_by_contract_target = defaultdict(float)
        self.agg_year4_by_contract_target = defaultdict(float)
        self.agg_year5_by_contract_target = defaultdict(float)
        self.agg_thereafter_by_contract_target = defaultdict(float)
        self.agg_interest_paid_by_contract_target = defaultdict(float)
        self.agg_st_principal_by_contract_target = defaultdict(float)
        self.agg_lt_principal_by_contract_target = defaultdict(float)

        # Track unique asset classes and contracts
        self.asset_classes = set()
        self.contract_info = {}  # contract_key -> info dict
```

---

## Complete Processing Logic Flow

```python
def process_maturity_analysis(df, report_year_end, report_period_end,
                               target_currency, exchange_rates=None):
    """
    Main processing function for maturity analysis.

    Args:
        df: pandas DataFrame from Consolidated Financial Schedules.xlsx
        report_year_end: int, e.g., 2024
        report_period_end: int, e.g., 12 for December
        target_currency: str, e.g., "USD"
        exchange_rates: dict, {contract_currency: rate_to_target}
    """
    aggregator = MaturityAnalysisAggregator()

    for idx, row in df.iterrows():
        # Step 1: Create aggregation keys
        contract_id = row['Contract ID']
        ag_id = row['Activation Group ID']
        contract_key = f"{contract_id}{ag_id}"
        asset_class = row.get('Unit Internal Asset Class', 'Unknown')

        # Step 2: Store contract info (first occurrence)
        if contract_key not in aggregator.contract_info:
            aggregator.contract_info[contract_key] = {
                'contract_id': contract_id,
                'contract_name': row['Contract Name'],
                'company_code': row['Company Code'],
                'profit_center': row.get('Unit Profit Center (Main)'),
                'cost_center': row.get('Unit Cost Center (Main)'),
                'business_unit': row['Business Unit'],
                'trading_partner': row.get('Trading Partner'),
                'activation_group_id': ag_id,
                'ag_status': row['Activation Group Status'],
                'start_date': row['Activation Date'],
                'end_date': row['End Date'],
                'contract_currency': row['Contract Currency'],
                'target_currency': target_currency,
                'asset_class': asset_class
            }

        # Step 3: Get exchange rate
        contract_currency = row['Contract Currency']
        exchange_rate = exchange_rates.get(contract_currency, 1.0) if exchange_rates else 1.0

        # Step 4: Parse payment date (use Period End Date for bucketing)
        payment_date = parse_date(row['Period End Date'])

        # Step 5: Determine time bucket
        bucket = calculate_period_bucket(payment_date, report_year_end, report_period_end)

        # Step 6: Get payment amount
        payment = row.get('Payment', 0.0) or 0.0

        # Step 7: Aggregate payments by bucket
        if bucket != 'skip':
            # Contract currency aggregation
            bucket_map_contract = {
                'year1': aggregator.agg_year1_by_contract,
                'year2': aggregator.agg_year2_by_contract,
                'year3': aggregator.agg_year3_by_contract,
                'year4': aggregator.agg_year4_by_contract,
                'year5': aggregator.agg_year5_by_contract,
                'thereafter': aggregator.agg_thereafter_by_contract
            }
            bucket_map_contract[bucket][contract_key] += payment

            # Target currency aggregation (Asset Class + Total)
            converted = payment * exchange_rate
            bucket_map_asset = {
                'year1': aggregator.agg_year1,
                'year2': aggregator.agg_year2,
                'year3': aggregator.agg_year3,
                'year4': aggregator.agg_year4,
                'year5': aggregator.agg_year5,
                'thereafter': aggregator.agg_thereafter
            }
            bucket_map_asset[bucket][asset_class] += converted
            bucket_map_asset[bucket]['total'] += converted

            # Target currency by contract
            bucket_map_contract_target = {
                'year1': aggregator.agg_year1_by_contract_target,
                'year2': aggregator.agg_year2_by_contract_target,
                'year3': aggregator.agg_year3_by_contract_target,
                'year4': aggregator.agg_year4_by_contract_target,
                'year5': aggregator.agg_year5_by_contract_target,
                'thereafter': aggregator.agg_thereafter_by_contract_target
            }
            bucket_map_contract_target[bucket][contract_key] += converted

            aggregator.asset_classes.add(asset_class)

        # Step 8: Extract principal balances at period end
        balances = extract_principal_balances(row, report_year_end, report_period_end)
        if balances:
            st = balances['st_principal']
            lt = balances['lt_principal']

            aggregator.agg_st_principal_by_contract[contract_key] += st
            aggregator.agg_lt_principal_by_contract[contract_key] += lt

            aggregator.agg_st_principal[asset_class] += st * exchange_rate
            aggregator.agg_lt_principal[asset_class] += lt * exchange_rate
            aggregator.agg_st_principal['total'] += st * exchange_rate
            aggregator.agg_lt_principal['total'] += lt * exchange_rate

            aggregator.agg_st_principal_by_contract_target[contract_key] += st * exchange_rate
            aggregator.agg_lt_principal_by_contract_target[contract_key] += lt * exchange_rate

        # Step 9: Extract interest for future periods
        interest = extract_interest(row, report_year_end, report_period_end)
        if interest > 0:
            aggregator.agg_interest_paid_by_contract[contract_key] += interest
            aggregator.agg_interest_paid[asset_class] += interest * exchange_rate
            aggregator.agg_interest_paid['total'] += interest * exchange_rate
            aggregator.agg_interest_paid_by_contract_target[contract_key] += interest * exchange_rate

    return aggregator
```

---

## Calculated Fields (Derived in Output)

### Total Payments
```python
def calc_total(year1, year2, year3, year4, year5, thereafter):
    return (year1 or 0) + (year2 or 0) + (year3 or 0) + (year4 or 0) + (year5 or 0) + (thereafter or 0)
```

### Total Principal (Method 1 - from payments minus interest)
```python
def calc_total_principal_method1(total_payments, interest_paid):
    return total_payments - (interest_paid or 0)
```

### Total Principal (Method 2 - from balance snapshot)
```python
def calc_total_principal_method2(st_principal, lt_principal):
    return (st_principal or 0) + (lt_principal or 0)
```

### Lease Term Calculation
```python
from dateutil.relativedelta import relativedelta

def calc_lease_term(start_date, end_date):
    """Calculate lease term in months and days"""
    rd = relativedelta(end_date + timedelta(days=1), start_date)
    months = rd.years * 12 + rd.months
    days = rd.days
    return months, days
```

---

## Column Mapping Summary

### Source to Output Mapping

| Java Field | Excel Column | Python Variable |
|------------|--------------|-----------------|
| `contractId` | Contract ID | `contract_id` |
| `externalContractId` | External Reference number | `external_contract_id` |
| `contractName` | Contract Name | `contract_name` |
| `companyCode` | Company Code | `company_code` |
| `profitCenter` | Unit Profit Center (Main) | `profit_center` |
| `costCenter` | Unit Cost Center (Main) | `cost_center` |
| `businessUnit` | Business Unit | `business_unit` |
| `tradingPartner` | Trading Partner | `trading_partner` |
| `activationGroupId` | Activation Group ID | `activation_group_id` |
| `agStatus` | Activation Group Status | `ag_status` |
| `startDate` | Activation Date | `start_date` |
| `endDate` | End Date | `end_date` |
| `contractCurrency` | Contract Currency | `contract_currency` |
| `assetClass` | Unit Internal Asset Class | `asset_class` |
| `minimumLeasePaymentPerUnit` | Payment | `payment` |
| `postingMonthEndInterestPaid` | Interest Paid | `interest_paid` |
| `reportSTPrincipalLiabilityClosingBalance` | ST Principal Liability Closing Balance | `st_principal` |
| `reportLTPrincipalLiabilityClosingBalance` | Principal Liability LT Closing Balance | `lt_principal` |
| `postingEndDate` | Period End Date | `posting_end_date` |
| `paymentDate` | Period End Date (same column) | `payment_date` |

---

## Filtering Logic

### Skip Conditions (from Java)

1. **AG Status Filter**: Skip if activation group status not in selected statuses
   ```python
   if row['Activation Group Status'] not in selected_ag_statuses:
       continue
   ```

2. **Period End After Activation End**: Skip if report period is after lease end
   ```python
   ag_end_date = parse_date(row['End Date'])
   if (report_year_end > ag_end_date.year or
       (report_year_end == ag_end_date.year and report_period_end > ag_end_date.month)):
       continue
   ```

3. **Payment Before Report Date**: Already handled by `calculate_period_bucket` returning 'skip'

---

## Next Steps for Implementation

1. **Create `maturity_analysis_processor.py`** in `webapp/backend/services/`
2. **Implement the core functions**:
   - `calculate_period_bucket()`
   - `extract_principal_balances()`
   - `extract_interest()`
   - `process_maturity_analysis()`
3. **Add Excel output generation** using openpyxl (similar to existing `excel_processor.py`)
4. **Add unit tests** for the time bucketing logic
5. **Integrate with FastAPI** endpoints

---

## Reference: Java Code Locations

| Logic | Java File | Lines |
|-------|-----------|-------|
| Time bucketing | MaturityAnalysisReport.java | 329-389 |
| Principal extraction | MaturityAnalysisReport.java | 293-314 |
| Interest extraction | MaturityAnalysisReport.java | 316-326 |
| Aggregation | MaturityAnalysisReport.java | 121-151 (maps), 298-388 (logic) |
| Excel generation | MaturityAnalysisReport.java | 401-570 |
| Column headers | MaturityAnalysisReport.java | 573-688 |
