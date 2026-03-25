"""
FX Processor — FX Remeasurement transformation layer

Consumes the clean DataFrame from ctr_reader.parse_ctr(), applies the
group-aggregate-map-rate pipeline, and writes a multi-sheet Excel workbook
(one sheet per unique Contract Currency).

Uses a COLUMN_MAPPINGS dict of {column_name: callable} for building the
output DataFrame — same pattern as the original formula_mapper.py for
vectorized, efficient pandas operations.

Output columns (FR-008):
  1  Contract ID
  2  Account Number
  3  Account Name
  4  Account Type                 (from account mapping; "N/A" if unmapped)
  5  Monetary?                    (from account mapping; "N/A" if unmapped)
  6  Account Currency             (= Contract Currency / worksheet name)
  7  Balance in Contract Currency (SUM Amount in Contract Currency)
  8  Initial Measurement Company Currency Balance (SUM Amount in Company Currency)
  9  Rate                         (from account mapping; "Period End" | "Historical" | blank if unmapped)
 10  Period-End Spot Exchange Rate (from exchange rates; blank if unmapped)
 11  Re-measured Balance          (col7 * col10 for monetary; col8 for non-monetary; blank if unmapped)
 12  FX (Gain) or Loss            (col11 - col8; blank if unmapped)
"""

import os
from datetime import datetime
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill


# ---------------------------------------------------------------------------
# Output column order (FR-008)
# ---------------------------------------------------------------------------

OUTPUT_COLUMNS = [
    "Contract ID",
    "Account Number",
    "Account Name",
    "Account Type",
    "Monetary?",
    "Account Currency",
    "Balance in Contract Currency",
    "Initial Measurement Company Currency Balance",
    "Rate",
    "Period-End Spot Exchange Rate",
    "Re-measured Balance",
    "FX (Gain) or Loss",
]

# ---------------------------------------------------------------------------
# Number formatting (FR-014) — 2+ decimal places, accounting style
# ---------------------------------------------------------------------------

CELL_NUMBER_FORMAT = '_-* #,##0.00_-;-* #,##0.00_-;_-* "-"??_-;_-@_-'
RATE_NUMBER_FORMAT = '_-* #,##0.0000_-;-* #,##0.0000_-;_-* "-"??_-;_-@_-'

# Columns that get number formatting (0-indexed positions within OUTPUT_COLUMNS)
_NUMERIC_FORMAT_MAP = {
    6: CELL_NUMBER_FORMAT,   # Balance in Contract Currency
    7: CELL_NUMBER_FORMAT,   # Initial Measurement Company Currency Balance
    9: RATE_NUMBER_FORMAT,   # Period-End Spot Exchange Rate (4 decimals like TC)
    10: CELL_NUMBER_FORMAT,  # Re-measured Balance
    11: CELL_NUMBER_FORMAT,  # FX (Gain) or Loss
}

# ---------------------------------------------------------------------------
# Header styling — matches sister project's apply_header_styling()
# ---------------------------------------------------------------------------

_HEADER_FONT = Font(name="Calibri", bold=True, size=11)
_HEADER_FILL = PatternFill(patternType="solid", fgColor="B3E5FC")
_HEADER_ALIGNMENT = Alignment(horizontal="center", vertical="center")


def _apply_header_styling(worksheet) -> None:
    for cell in worksheet[1]:
        cell.font = _HEADER_FONT
        cell.fill = _HEADER_FILL
        cell.alignment = _HEADER_ALIGNMENT


# ---------------------------------------------------------------------------
# Column mapping functions — vectorized, same pattern as formula_mapper.py
#
# Each function takes (grouped_df, account_mapping, exchange_rates) and
# returns a pd.Series for that column.
# ---------------------------------------------------------------------------

def _col_contract_id(df, mapping, rates):
    return df["Contract ID"]


def _col_account_number(df, mapping, rates):
    return df["Account Number"]


def _col_account_name(df, mapping, rates):
    return df["Account Name"]


def _col_account_type(df, mapping, rates):
    return df["Account Number"].map(
        lambda acct: mapping.get(str(acct), {}).get("account_type") or "N/A"
    )


def _col_monetary(df, mapping, rates):
    return df["Account Number"].map(
        lambda acct: mapping.get(str(acct), {}).get("monetary") or "N/A"
    )


def _col_account_currency(df, mapping, rates):
    return df["Contract Currency"]


def _col_balance_cc(df, mapping, rates):
    return df["balance_cc"]


def _col_initial_measurement(df, mapping, rates):
    return df["initial_measurement"]


def _col_rate(df, mapping, rates):
    """Rate from account mapping ('Period End' | 'Historical'); None if unmapped."""
    return df["Account Number"].map(
        lambda acct: mapping.get(str(acct), {}).get("rate")
    )


def _col_spot_rate(df, mapping, rates):
    """Period-end spot exchange rate from user-supplied rates; None if missing."""
    return df["Contract Currency"].map(
        lambda ccy: rates.get(str(ccy).upper())
    )


def _col_remeasured_balance(df, mapping, rates):
    """col6 * col9 for monetary; col7 for non-monetary; None if unmapped or no rate."""
    monetary = _col_monetary(df, mapping, rates)
    spot_rate = _col_spot_rate(df, mapping, rates)
    is_unmapped = monetary == "N/A"
    is_monetary = monetary.str.strip().str.lower() == "yes"
    has_rate = spot_rate.notna()

    return np.where(
        is_unmapped,
        None,
        np.where(
            ~has_rate,
            None,
            np.where(
                is_monetary,
                df["balance_cc"] * spot_rate,
                df["initial_measurement"],
            ),
        ),
    )


def _col_fx_gain_loss(df, mapping, rates):
    """col10 - col7; None if unmapped or no rate."""
    remeasured = pd.to_numeric(
        _col_remeasured_balance(df, mapping, rates), errors="coerce"
    )
    return np.where(
        pd.isna(remeasured),
        None,
        remeasured - df["initial_measurement"],
    )


# ---------------------------------------------------------------------------
# Column mappings dict — column name → callable
# Same pattern as FORMULA_MAPPINGS in the original formula_mapper.py
# ---------------------------------------------------------------------------

COLUMN_MAPPINGS = {
    "Contract ID": _col_contract_id,
    "Account Number": _col_account_number,
    "Account Name": _col_account_name,
    "Account Type": _col_account_type,
    "Monetary?": _col_monetary,
    "Account Currency": _col_account_currency,
    "Balance in Contract Currency": _col_balance_cc,
    "Initial Measurement Company Currency Balance": _col_initial_measurement,
    "Rate": _col_rate,
    "Period-End Spot Exchange Rate": _col_spot_rate,
    "Re-measured Balance": _col_remeasured_balance,
    "FX (Gain) or Loss": _col_fx_gain_loss,
}


# ---------------------------------------------------------------------------
# Main processing function
# ---------------------------------------------------------------------------

def process_fx(
    df: pd.DataFrame,
    account_mapping: Dict[str, Dict[str, Optional[str]]],
    exchange_rates: Dict[str, float],
    output_file_path: str,
    fiscal_year: Optional[str] = None,
    fiscal_period: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run the FX Remeasurement pipeline and write the output workbook.

    Args:
        df: Clean DataFrame from ctr_reader.parse_ctr().
        account_mapping: Dict keyed by account_number (str).
            Each value is {"account_type": "BS"|"P&L"|None, "monetary": "Yes"|"No"|None}
        exchange_rates: Dict keyed by currency code (uppercase str) -> float rate.
        output_file_path: Absolute path where the .xlsx file will be written.
        fiscal_year: From CTR metadata.
        fiscal_period: From CTR metadata.

    Returns a result dict with success, message, metadata, and warnings.
    """
    warnings: List[str] = []

    try:
        input_rows = len(df)

        # Normalise exchange_rates keys to uppercase
        rates_upper = {k.upper(): v for k, v in exchange_rates.items()}

        # --- Step 1: Group and aggregate (FR-006) ---
        grouped = (
            df.groupby(
                ["Contract ID", "Account Number", "Account Name", "Contract Currency"],
                as_index=False,
                sort=False,
            )
            .agg(
                balance_cc=("Amount in Contract Currency", "sum"),
                initial_measurement=("Amount in Company Currency", "sum"),
            )
        )

        # Resolve conflicting Account Names: keep first occurrence
        first_names: Dict[str, str] = {}
        for _, row in df[["Account Number", "Account Name"]].iterrows():
            num = str(row["Account Number"])
            if num not in first_names:
                first_names[num] = row["Account Name"]

        grouped["Account Name"] = grouped["Account Number"].map(
            lambda acct: first_names.get(str(acct), "—")
        )

        # --- Step 2: Build output DataFrame using column mappings ---
        output_df = pd.DataFrame()
        for col_name, col_func in COLUMN_MAPPINGS.items():
            output_df[col_name] = col_func(grouped, account_mapping, rates_upper)

        # --- Collect warnings ---
        unmapped_accounts = sorted(
            output_df.loc[
                output_df["Account Type"] == "N/A", "Account Number"
            ].unique().tolist()
        )
        if unmapped_accounts:
            warnings.append(
                f"Unmapped account(s) — columns 3-4 and 8-11 will be blank/N/A: "
                f"{', '.join(str(a) for a in unmapped_accounts)}"
            )

        missing_rate_currencies = sorted(
            output_df.loc[
                (output_df["Account Type"] != "N/A")
                & output_df["Period-End Spot Exchange Rate"].isna(),
                "Account Currency",
            ].unique().tolist()
        )
        if missing_rate_currencies:
            warnings.append(
                f"No exchange rate supplied for currency/currencies: "
                f"{', '.join(missing_rate_currencies)}. "
                "Columns 9-11 will be blank for affected rows."
            )

        # --- Step 3: Write multi-sheet workbook (FR-007, FR-012, FR-013) ---
        wb = Workbook()
        if "Sheet" in wb.sheetnames:
            wb.remove(wb["Sheet"])

        currencies = sorted(output_df["Account Currency"].dropna().unique().tolist())
        total_output_rows = 0
        sheets_created: List[str] = []

        col_index_map = {col: idx for idx, col in enumerate(OUTPUT_COLUMNS)}

        for currency in currencies:
            currency_df = output_df[output_df["Account Currency"] == currency].copy()
            currency_df = currency_df.sort_values(
                by="Account Number", ascending=True
            ).reset_index(drop=True)

            ws = wb.create_sheet(title=currency)
            sheets_created.append(currency)

            # Write header row
            ws.append(OUTPUT_COLUMNS)
            _apply_header_styling(ws)

            # Write data rows
            for _, row in currency_df.iterrows():
                data_row = [row[col] for col in OUTPUT_COLUMNS]
                ws.append(data_row)

                excel_row = ws.max_row
                for col_idx, fmt in _NUMERIC_FORMAT_MAP.items():
                    cell = ws.cell(row=excel_row, column=col_idx + 1)
                    if cell.value is not None:
                        cell.number_format = fmt

                total_output_rows += 1

        wb.save(output_file_path)

        return {
            "success": True,
            "message": "FX Remeasurement processed successfully.",
            "output_file": output_file_path,
            "input_rows": input_rows,
            "output_rows": total_output_rows,
            "sheets": sheets_created,
            "unmapped_accounts": unmapped_accounts,
            "missing_rate_currencies": missing_rate_currencies,
            "warnings": warnings,
            "fiscal_year": fiscal_year,
            "fiscal_period": fiscal_period,
            "error": None,
        }

    except Exception as exc:
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "message": f"Processing error: {exc}",
            "output_file": output_file_path,
            "input_rows": 0,
            "output_rows": 0,
            "sheets": [],
            "unmapped_accounts": [],
            "missing_rate_currencies": [],
            "warnings": warnings,
            "fiscal_year": fiscal_year,
            "fiscal_period": fiscal_period,
            "error": str(exc),
        }


def build_output_filename(
    fiscal_year: Optional[str],
    fiscal_period: Optional[str],
) -> str:
    """
    Build the output filename per FR-015.

    Pattern: CTR_FX_Remeasurement_{FiscalYear}_{FiscalPeriod}_{Timestamp}.xlsx
    Falls back to 'Unknown' for missing fiscal year or period (CSV inputs).
    """
    fy = fiscal_year if fiscal_year else "Unknown"
    fp = fiscal_period if fiscal_period else "Unknown"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"CTR_FX_Remeasurement_{fy}_{fp}_{ts}.xlsx"
