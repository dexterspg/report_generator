"""
CTR Reader — Shared CTR parsing layer

Parses any Nakisa Lease Administration Consolidated Transaction Report (CTR).
Owned by this module; individual processors (fx_processor, etc.) consume the
clean DataFrame and metadata it returns without re-implementing file I/O or
column validation.

Supports:
- Excel (.xlsx / .xls): metadata extracted from rows 1-26, headers at row 27
- CSV: header at row 1, no metadata (metadata fields returned as None with warning)

Configurable row positions via input_header_start (default 27).
"""

import pandas as pd
from typing import Any, Dict, List, Optional, Tuple


# Core CTR column set present in every Nakisa CTR export.
# Processors may require a subset of these; ctr_reader rejects the file only
# when one or more of these shared columns is missing entirely.
CORE_CTR_COLUMNS = [
    "Contract ID",
    "Account Number",
    "Account Name",
    "Contract Currency",
    "Amount in Contract Currency",
    "Amount in Company Currency",
    "Fiscal Year",
    "Fiscal Period",
    "Company",
    "Transaction Type",
]

# Metadata labels expected in rows 1-26 of Excel CTR exports.
# Each entry maps a search string (lowercased) to a result key.
_METADATA_LABELS: Dict[str, str] = {
    "fiscal year": "fiscal_year",
    "fiscal period": "fiscal_period",
    "accounting standard": "accounting_standard",
    "contract currency": "contract_currency",
    "company currency": "company_currency",
    "company": "company_code",
}

# Number of metadata rows before the header in an Excel CTR export (rows 1-26).
_EXCEL_METADATA_ROW_COUNT = 26


def _extract_metadata_from_excel(file_path: str) -> Tuple[Dict[str, Optional[str]], List[str]]:
    """
    Read rows 1-26 of an Excel CTR file and extract known metadata key/value pairs.

    Returns:
        metadata: dict with keys from _METADATA_LABELS values; None when not found
        warnings: list of human-readable warning strings
    """
    metadata: Dict[str, Optional[str]] = {v: None for v in _METADATA_LABELS.values()}
    warnings: List[str] = []

    try:
        # Read only the metadata rows; no header row, plain values
        raw = pd.read_excel(file_path, header=None, nrows=_EXCEL_METADATA_ROW_COUNT)
    except Exception as exc:
        warnings.append(f"Could not read metadata rows 1-26: {exc}")
        return metadata, warnings

    for _, row in raw.iterrows():
        # Look for a label in any cell and take the next non-null cell as its value
        for col_idx, cell in enumerate(row):
            if not isinstance(cell, str):
                continue
            cell_lower = cell.strip().lower()
            for label, key in _METADATA_LABELS.items():
                if label in cell_lower and metadata[key] is None:
                    # Search remaining cells in the same row for a value
                    for value_cell in row.iloc[col_idx + 1:]:
                        if pd.notna(value_cell) and str(value_cell).strip():
                            metadata[key] = str(value_cell).strip()
                            break

    return metadata, warnings



def _empty_metadata() -> Dict[str, Optional[str]]:
    """Return a metadata dict with all fields set to None."""
    return {v: None for v in _METADATA_LABELS.values()}


def _coerce_numeric_amounts(
    df: pd.DataFrame,
    amount_columns: List[str],
    warnings: List[str],
) -> pd.DataFrame:
    """
    Convert amount columns to float in-place, skipping rows where conversion
    fails and appending a per-row warning.

    Returns the DataFrame with invalid rows dropped and amount columns as float64.
    """
    rows_to_drop: List[int] = []

    for col in amount_columns:
        if col not in df.columns:
            continue
        original = df[col].copy()
        numeric = pd.to_numeric(df[col], errors="coerce")
        # Drop any row where the amount is NaN after coercion — covers both
        # originally-null cells and strings auto-converted by pandas (e.g. "N/A")
        bad_mask = numeric.isna()
        for idx in df.index[bad_mask]:
            raw_val = original.at[idx]
            if pd.isna(raw_val):
                warnings.append(
                    f"Row {idx}: missing value in column '{col}' — row skipped."
                )
            else:
                warnings.append(
                    f"Row {idx}: non-numeric value '{raw_val}' in column "
                    f"'{col}' — row skipped."
                )
            rows_to_drop.append(idx)
        df[col] = numeric

    if rows_to_drop:
        df = df.drop(index=rows_to_drop).reset_index(drop=True)

    return df


def parse_ctr(
    file_path: str,
    input_header_start: int = 27,
) -> Dict[str, Any]:
    """
    Parse a CTR file and return a result dict.

    Args:
        file_path: Absolute path to the CTR file (.xlsx, .xls, or .csv).
        input_header_start: 1-indexed row number of the header row.
                            Default 27 (Nakisa Excel standard).
                            For CSV files this parameter is ignored and
                            row 1 is always used as the header.

    Returns a dict with the following keys:

        success (bool): True if parsing succeeded and the file can be processed.
        message (str): Human-readable summary.
        df (pd.DataFrame | None): Clean DataFrame ready for a processor.
            None when success is False.
        metadata (dict): Extracted metadata from rows 1-26. All fields are None
            for CSV inputs.
        accounts (list[dict]): Unique {"account_number": ..., "account_name": ...}
            pairs extracted from the data.
        currencies (list[str]): Unique Contract Currency codes (normalised to
            uppercase).
        company_currency (str | None): Company currency extracted from metadata
            (None for CSV).
        warnings (list[str]): Non-fatal issues encountered during parsing.
        missing_columns (list[str]): Populated (and success set False) when core
            columns are absent.
    """
    warnings: List[str] = []
    file_lower = file_path.lower()

    is_csv = file_lower.endswith(".csv")
    is_excel = file_lower.endswith(".xlsx") or file_lower.endswith(".xls")

    if not is_csv and not is_excel:
        return {
            "success": False,
            "message": "Unsupported file type. Only .xlsx, .xls, and .csv are accepted.",
            "df": None,
            "metadata": _empty_metadata(),
            "accounts": [],
            "currencies": [],
            "company_currency": None,
            "warnings": warnings,
            "missing_columns": [],
        }

    # --- Metadata (Excel only) ---
    if is_excel:
        metadata, meta_warnings = _extract_metadata_from_excel(file_path)
        warnings.extend(meta_warnings)
    else:
        metadata = _empty_metadata()
        warnings.append(
            "CSV input detected: metadata (Fiscal Year, Fiscal Period, etc.) "
            "is not available for CSV files. Filename will use 'Unknown' placeholders."
        )

    # --- Read data rows ---
    try:
        if is_excel:
            # header=N is 0-indexed; input_header_start is 1-indexed
            df = pd.read_excel(file_path, header=input_header_start - 1)
        else:
            df = pd.read_csv(file_path, header=0)
    except Exception as exc:
        return {
            "success": False,
            "message": f"Could not read file: {exc}",
            "df": None,
            "metadata": metadata,
            "accounts": [],
            "currencies": [],
            "company_currency": metadata.get("company_currency"),
            "warnings": warnings,
            "missing_columns": [],
        }

    # Strip leading/trailing whitespace from column names
    df.columns = [str(c).strip() for c in df.columns]

    # --- Column validation ---
    missing_columns = [col for col in CORE_CTR_COLUMNS if col not in df.columns]
    if missing_columns:
        return {
            "success": False,
            "message": (
                f"Missing required column(s): {', '.join(missing_columns)}. "
                "Processing cannot proceed."
            ),
            "df": None,
            "metadata": metadata,
            "accounts": [],
            "currencies": [],
            "company_currency": metadata.get("company_currency"),
            "warnings": warnings,
            "missing_columns": missing_columns,
        }

    # --- Drop fully empty rows ---
    initial_count = len(df)
    df = df.dropna(how="all").reset_index(drop=True)
    dropped_empty = initial_count - len(df)
    if dropped_empty:
        warnings.append(f"{dropped_empty} fully empty row(s) skipped.")

    # --- Skip rows with missing Account Number or Contract Currency (FR-021) ---
    missing_key_mask = (
        df["Account Number"].isna() | (df["Account Number"].astype(str).str.strip() == "")
        | df["Contract Currency"].isna() | (df["Contract Currency"].astype(str).str.strip() == "")
    )
    if missing_key_mask.any():
        count = missing_key_mask.sum()
        warnings.append(
            f"{count} row(s) skipped: missing Account Number or Contract Currency."
        )
        df = df[~missing_key_mask].reset_index(drop=True)

    # --- Normalise Contract Currency to uppercase (EC-006) ---
    df["Contract Currency"] = df["Contract Currency"].astype(str).str.strip().str.upper()
    df["Contract Currency"] = df["Contract Currency"].str.split(" - ").str[0].str.strip()

    # --- Normalise Account Name: fill blanks with "—" (FR-011) ---
    df["Account Name"] = df["Account Name"].astype(str).str.strip()
    df["Account Name"] = df["Account Name"].replace({"": "—", "nan": "—"})

    # --- Coerce numeric amount columns; skip bad rows with warning (FR-022) ---
    df = _coerce_numeric_amounts(
        df,
        ["Amount in Contract Currency", "Amount in Company Currency"],
        warnings,
    )

    # --- Extract fiscal metadata from data columns (rows 1-26 do not contain these) ---
    if metadata.get("fiscal_year") is None and "Fiscal Year" in df.columns:
        vals = df["Fiscal Year"].dropna().unique()
        if len(vals) == 1:
            raw = str(vals[0])
            metadata["fiscal_year"] = str(int(float(raw))) if raw.replace('.', '', 1).isdigit() else raw
        elif len(vals) > 1:
            warnings.append(
                f"Multiple Fiscal Years found in CTR: {sorted(str(v) for v in vals)}. Using first."
            )
            raw = str(vals[0])
            metadata["fiscal_year"] = str(int(float(raw))) if raw.replace('.', '', 1).isdigit() else raw

    if metadata.get("fiscal_period") is None and "Fiscal Period" in df.columns:
        vals = df["Fiscal Period"].dropna().unique()
        if len(vals) == 1:
            raw = str(vals[0])
            metadata["fiscal_period"] = str(int(float(raw))) if raw.replace('.', '', 1).isdigit() else raw
        elif len(vals) > 1:
            warnings.append(
                f"Multiple Fiscal Periods found in CTR: {sorted(str(v) for v in vals)}. Using first."
            )
            raw = str(vals[0])
            metadata["fiscal_period"] = str(int(float(raw))) if raw.replace('.', '', 1).isdigit() else raw

    if metadata.get("company_currency") is None and "Company Currency" in df.columns:
        vals = df["Company Currency"].dropna().unique()
        if len(vals) >= 1:
            raw = str(vals[0]).strip()
            # Normalize: "CAD - Canadian Dollar" → "CAD"
            metadata["company_currency"] = raw.split(" - ")[0].strip().upper()

    # --- Detect conflicting Account Names for same Account Number (EC-004) ---
    name_check = (
        df[["Account Number", "Account Name"]]
        .drop_duplicates()
        .groupby("Account Number")["Account Name"]
        .nunique()
    )
    conflicting = name_check[name_check > 1].index.tolist()
    for acct_num in conflicting:
        names = df.loc[df["Account Number"] == acct_num, "Account Name"].unique().tolist()
        warnings.append(
            f"Account Number '{acct_num}' has conflicting Account Names "
            f"({', '.join(repr(n) for n in names)}). First occurrence will be used."
        )

    # --- Extract unique accounts ---
    # Preserve first-occurrence order for consistent UI display
    seen_accounts: Dict[str, str] = {}
    for _, row in df[["Account Number", "Account Name"]].iterrows():
        acct_num = str(row["Account Number"]).strip()
        if acct_num not in seen_accounts:
            seen_accounts[acct_num] = row["Account Name"]

    accounts = [
        {"account_number": num, "account_name": name}
        for num, name in seen_accounts.items()
    ]

    # --- Extract unique currencies (sorted for deterministic output) ---
    currencies = sorted(df["Contract Currency"].dropna().unique().tolist())

    if len(df) == 0:
        warnings.append("No data rows found after validation.")

    return {
        "success": True,
        "message": f"CTR parsed successfully. {len(df)} data row(s) ready for processing.",
        "df": df,
        "metadata": metadata,
        "accounts": accounts,
        "currencies": currencies,
        "company_currency": metadata.get("company_currency"),
        "warnings": warnings,
        "missing_columns": [],
    }
