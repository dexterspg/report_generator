"""
Config Store — Configuration persistence layer

Manages two config files as shareable CSV/Excel artifacts:

1. Account Mapping (account_mapping.json internally)
   Columns: Account Number, Account Type, Monetary
   Keyed by Account Number — one row per GL account.

2. Exchange Rates (exchange_rates.json internally)
   Columns: Currency, Rate
   Keyed by Currency code — one row per currency pair.

Both configs support three upload modes:
  - "replace"  — clear existing, load new file
  - "merge"    — add new entries, update existing entries with same key
  - "new"      — first-time upload (same as replace when no config exists)

Both can be exported as Excel files for sharing between team members
(important for desktop mode where there is no shared server).

Public API
----------
load_account_mapping()   -> dict
save_account_mapping()   -> None
reset_account_mapping()  -> None
parse_account_mapping_file(file_path) -> dict
merge_account_mapping(existing, incoming) -> dict
export_account_mapping(output_path) -> str

load_exchange_rates()    -> dict
save_exchange_rates()    -> None
reset_exchange_rates()   -> None
parse_exchange_rates_file(file_path) -> dict
merge_exchange_rates(existing, incoming) -> dict
export_exchange_rates(output_path) -> str
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

_APP_DATA_DIR_NAME = "CTR-FX-Remeasurement"


def _get_app_data_dir() -> Path:
    """
    Resolve the root data directory for the application.

    - Desktop (PyInstaller .exe): %LOCALAPPDATA%/CTR-FX-Remeasurement/
      Per-user, no admin rights needed, survives .exe updates.
    - Dev (running as script): backend/ directory (same as before).
    """
    if getattr(sys, "frozen", False):
        # Use %LOCALAPPDATA% on Windows, ~/.local/share on Linux/Mac
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            base_path = Path(local_app_data) / _APP_DATA_DIR_NAME
        else:
            base_path = Path.home() / ".local" / "share" / _APP_DATA_DIR_NAME
        base_path.mkdir(parents=True, exist_ok=True)
    else:
        base_path = Path(__file__).parent.parent

    return base_path


def _get_config_dir() -> Path:
    """Resolve the config/ directory."""
    config_dir = _get_app_data_dir() / "config"
    config_dir.mkdir(exist_ok=True)
    return config_dir


_ACCOUNT_MAPPING_FILE = "account_mapping.json"
_EXCHANGE_RATES_FILE = "exchange_rates.json"

# Styling for exported Excel files
_HEADER_FONT = Font(name="Calibri", bold=True, size=11)
_HEADER_FILL = PatternFill(patternType="solid", fgColor="B3E5FC")
_HEADER_ALIGNMENT = Alignment(horizontal="center", vertical="center")


def _config_path(filename: str) -> Path:
    return _get_config_dir() / filename


# ---------------------------------------------------------------------------
# Account Mapping — internal JSON persistence
# ---------------------------------------------------------------------------

def load_account_mapping() -> Dict[str, Dict[str, Any]]:
    """
    Load saved account mapping from config/account_mapping.json.

    Returns:
        Dict keyed by account_number (str).
        Each value: {"account_type": "BS"|"P&L"|None, "monetary": "Yes"|"No"|None}
        Empty dict if file does not exist or cannot be read.
    """
    path = _config_path(_ACCOUNT_MAPPING_FILE)
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            print(f"config_store: unexpected format in {path} — returning empty mapping.")
            return {}
        return data
    except Exception as exc:
        print(f"config_store: could not read {path}: {exc}")
        return {}


def save_account_mapping(mapping: Dict[str, Dict[str, Any]]) -> None:
    """Persist account mapping to config/account_mapping.json."""
    path = _config_path(_ACCOUNT_MAPPING_FILE)
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(mapping, fh, indent=2, ensure_ascii=False)
    except Exception as exc:
        print(f"config_store: could not write {path}: {exc}")


def reset_account_mapping() -> None:
    """Delete config/account_mapping.json. No-op if file does not exist."""
    path = _config_path(_ACCOUNT_MAPPING_FILE)
    try:
        if path.exists():
            path.unlink()
    except Exception as exc:
        print(f"config_store: could not delete {path}: {exc}")


# ---------------------------------------------------------------------------
# Account Mapping — file parsing, merging, exporting
# ---------------------------------------------------------------------------

_ACCOUNT_MAPPING_COLUMNS = {
    "account_number": ["account number", "account_number", "accountnumber", "acct number", "acct_number", "gl account"],
    "account_type": ["account type", "account_type", "accounttype", "type", "acct type"],
    "monetary": ["monetary", "monetary?", "is_monetary", "is monetary"],
}


def _find_column(df_columns: List[str], aliases: List[str]) -> str:
    """Find a column in the DataFrame by checking known aliases (case-insensitive)."""
    df_cols_lower = {c.strip().lower(): c for c in df_columns}
    for alias in aliases:
        if alias.lower() in df_cols_lower:
            return df_cols_lower[alias.lower()]
    return None


def parse_account_mapping_file(file_path: str) -> Tuple[Dict[str, Dict[str, Any]], List[str]]:
    """
    Parse an uploaded account mapping file (CSV or Excel).

    Expected columns: Account Number, Account Type, Monetary
    Column names are matched case-insensitively with common aliases.

    Returns:
        (mapping_dict, warnings) where mapping_dict is keyed by account_number.
    """
    warnings: List[str] = []
    file_lower = file_path.lower()

    try:
        if file_lower.endswith(".csv"):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
    except Exception as exc:
        return {}, [f"Could not read file: {exc}"]

    df.columns = [str(c).strip() for c in df.columns]

    # Find columns by alias
    acct_col = _find_column(df.columns, _ACCOUNT_MAPPING_COLUMNS["account_number"])
    type_col = _find_column(df.columns, _ACCOUNT_MAPPING_COLUMNS["account_type"])
    monetary_col = _find_column(df.columns, _ACCOUNT_MAPPING_COLUMNS["monetary"])

    if acct_col is None:
        return {}, ["Account Number column not found. Expected one of: " +
                     ", ".join(_ACCOUNT_MAPPING_COLUMNS["account_number"])]

    if type_col is None:
        warnings.append("Account Type column not found — will be set to None for all entries.")
    if monetary_col is None:
        warnings.append("Monetary column not found — will be set to None for all entries.")

    mapping: Dict[str, Dict[str, Any]] = {}
    for _, row in df.iterrows():
        acct_num = str(row[acct_col]).strip()
        if not acct_num or acct_num == "nan":
            continue

        account_type = None
        if type_col and pd.notna(row.get(type_col)):
            account_type = str(row[type_col]).strip()

        monetary = None
        if monetary_col and pd.notna(row.get(monetary_col)):
            monetary = str(row[monetary_col]).strip()

        mapping[acct_num] = {
            "account_type": account_type,
            "monetary": monetary,
        }

    warnings.append(f"Parsed {len(mapping)} account(s) from file.")
    return mapping, warnings


def merge_account_mapping(
    existing: Dict[str, Dict[str, Any]],
    incoming: Dict[str, Dict[str, Any]],
) -> Dict[str, Dict[str, Any]]:
    """
    Merge incoming mapping into existing. New entries are added,
    existing entries are updated with incoming values.
    """
    merged = dict(existing)
    merged.update(incoming)
    return merged


def export_account_mapping(output_path: str) -> str:
    """
    Export current account mapping as an Excel file for sharing.

    Returns the output file path.
    """
    mapping = load_account_mapping()

    wb = Workbook()
    ws = wb.active
    ws.title = "Account Mapping"

    headers = ["Account Number", "Account Type", "Monetary"]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = _HEADER_FONT
        cell.fill = _HEADER_FILL
        cell.alignment = _HEADER_ALIGNMENT

    for acct_num, values in sorted(mapping.items()):
        ws.append([
            acct_num,
            values.get("account_type", ""),
            values.get("monetary", ""),
        ])

    wb.save(output_path)
    return output_path


# ---------------------------------------------------------------------------
# Exchange Rates — internal JSON persistence
# ---------------------------------------------------------------------------

def load_exchange_rates() -> Dict[str, float]:
    """
    Load saved exchange rates from config/exchange_rates.json.

    Returns:
        Dict keyed by currency code (str, uppercase) -> float rate.
        Empty dict if file does not exist or cannot be read.
    """
    path = _config_path(_EXCHANGE_RATES_FILE)
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            print(f"config_store: unexpected format in {path} — returning empty rates.")
            return {}
        result: Dict[str, float] = {}
        for currency, rate in data.items():
            try:
                result[str(currency).upper()] = float(rate)
            except (TypeError, ValueError):
                print(f"config_store: skipping non-numeric rate for '{currency}': {rate!r}")
        return result
    except Exception as exc:
        print(f"config_store: could not read {path}: {exc}")
        return {}


def save_exchange_rates(rates: Dict[str, float]) -> None:
    """Persist exchange rates to config/exchange_rates.json."""
    path = _config_path(_EXCHANGE_RATES_FILE)
    try:
        normalised = {str(k).upper(): float(v) for k, v in rates.items()}
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(normalised, fh, indent=2, ensure_ascii=False)
    except Exception as exc:
        print(f"config_store: could not write {path}: {exc}")


def reset_exchange_rates() -> None:
    """Delete config/exchange_rates.json. No-op if file does not exist."""
    path = _config_path(_EXCHANGE_RATES_FILE)
    try:
        if path.exists():
            path.unlink()
    except Exception as exc:
        print(f"config_store: could not delete {path}: {exc}")


# ---------------------------------------------------------------------------
# Exchange Rates — file parsing, merging, exporting
# ---------------------------------------------------------------------------

_EXCHANGE_RATES_COLUMNS = {
    "currency": ["currency", "currency_code", "currency code", "ccy", "from_currency", "from currency"],
    "rate": ["rate", "exchange_rate", "exchange rate", "spot_rate", "spot rate", "fx_rate", "fx rate"],
}


def parse_exchange_rates_file(file_path: str) -> Tuple[Dict[str, float], List[str]]:
    """
    Parse an uploaded exchange rates file (CSV or Excel).

    Expected columns: Currency, Rate
    Column names are matched case-insensitively with common aliases.

    Returns:
        (rates_dict, warnings) where rates_dict is keyed by currency code (uppercase).
    """
    warnings: List[str] = []
    file_lower = file_path.lower()

    try:
        if file_lower.endswith(".csv"):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
    except Exception as exc:
        return {}, [f"Could not read file: {exc}"]

    df.columns = [str(c).strip() for c in df.columns]

    ccy_col = _find_column(df.columns, _EXCHANGE_RATES_COLUMNS["currency"])
    rate_col = _find_column(df.columns, _EXCHANGE_RATES_COLUMNS["rate"])

    if ccy_col is None:
        return {}, ["Currency column not found. Expected one of: " +
                     ", ".join(_EXCHANGE_RATES_COLUMNS["currency"])]
    if rate_col is None:
        return {}, ["Rate column not found. Expected one of: " +
                     ", ".join(_EXCHANGE_RATES_COLUMNS["rate"])]

    rates: Dict[str, float] = {}
    for _, row in df.iterrows():
        currency = str(row[ccy_col]).strip().upper()
        if not currency or currency == "NAN":
            continue

        try:
            rate = float(row[rate_col])
        except (TypeError, ValueError):
            warnings.append(f"Skipping non-numeric rate for '{currency}': {row[rate_col]!r}")
            continue

        rates[currency] = rate

    warnings.append(f"Parsed {len(rates)} exchange rate(s) from file.")
    return rates, warnings


def merge_exchange_rates(
    existing: Dict[str, float],
    incoming: Dict[str, float],
) -> Dict[str, float]:
    """
    Merge incoming rates into existing. New currencies are added,
    existing currencies are updated with the incoming rate.
    """
    merged = dict(existing)
    merged.update(incoming)
    return merged


def export_exchange_rates(output_path: str) -> str:
    """
    Export current exchange rates as an Excel file for sharing.

    Returns the output file path.
    """
    rates = load_exchange_rates()

    wb = Workbook()
    ws = wb.active
    ws.title = "Exchange Rates"

    headers = ["Currency", "Rate"]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = _HEADER_FONT
        cell.fill = _HEADER_FILL
        cell.alignment = _HEADER_ALIGNMENT

    rate_format = '_-* #,##0.0000_-;-* #,##0.0000_-;_-* "-"??_-;_-@_-'
    for currency, rate in sorted(rates.items()):
        ws.append([currency, rate])
        ws.cell(row=ws.max_row, column=2).number_format = rate_format

    wb.save(output_path)
    return output_path


# ---------------------------------------------------------------------------
# History — local audit trail with config snapshots for rollback
# ---------------------------------------------------------------------------

_HISTORY_DIR = "history"


def _get_history_dir() -> Path:
    """Resolve the history/ directory (sibling to config/)."""
    config_dir = _get_config_dir()
    history_dir = config_dir.parent / _HISTORY_DIR
    history_dir.mkdir(exist_ok=True)
    return history_dir


def save_history_entry(
    action: str,
    config_type: str,
    mode: Optional[str] = None,
    source_filename: Optional[str] = None,
    account_mapping_snapshot: Optional[Dict] = None,
    exchange_rates_snapshot: Optional[Dict] = None,
    details: Optional[Dict] = None,
) -> str:
    """
    Save a history entry with a snapshot of the config state at that moment.

    Args:
        action: What happened — "upload", "reset", "process", "rollback"
        config_type: Which config — "account_mapping", "exchange_rates", "both"
        mode: Upload mode used — "replace", "merge", or None
        source_filename: Name of the uploaded file (if applicable)
        account_mapping_snapshot: Full account mapping at time of action (auto-loaded if None)
        exchange_rates_snapshot: Full exchange rates at time of action (auto-loaded if None)
        details: Any extra info (warnings, row counts, etc.)

    Returns:
        The history entry ID (filename stem).
    """
    timestamp = datetime.now()
    entry_id = timestamp.strftime("%Y%m%d_%H%M%S")

    if account_mapping_snapshot is None:
        account_mapping_snapshot = load_account_mapping()
    if exchange_rates_snapshot is None:
        exchange_rates_snapshot = load_exchange_rates()

    entry = {
        "id": entry_id,
        "timestamp": timestamp.isoformat(),
        "action": action,
        "config_type": config_type,
        "mode": mode,
        "source_filename": source_filename,
        "snapshots": {
            "account_mapping": account_mapping_snapshot,
            "exchange_rates": exchange_rates_snapshot,
        },
        "details": details or {},
    }

    path = _get_history_dir() / f"{entry_id}.json"
    counter = 1
    while path.exists():
        path = _get_history_dir() / f"{entry_id}_{counter}.json"
        entry["id"] = f"{entry_id}_{counter}"
        counter += 1

    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(entry, fh, indent=2, ensure_ascii=False)
    except Exception as exc:
        print(f"config_store: could not write history entry {path}: {exc}")

    return entry["id"]


def list_history(limit: int = 50) -> List[Dict[str, Any]]:
    """
    List history entries, most recent first.
    Returns summaries without full snapshots to keep responses lightweight.
    """
    history_dir = _get_history_dir()
    entries = []

    for path in sorted(history_dir.glob("*.json"), reverse=True):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                entry = json.load(fh)
            entries.append({
                "id": entry.get("id", path.stem),
                "timestamp": entry.get("timestamp"),
                "action": entry.get("action"),
                "config_type": entry.get("config_type"),
                "mode": entry.get("mode"),
                "source_filename": entry.get("source_filename"),
                "account_mapping_count": len(entry.get("snapshots", {}).get("account_mapping", {})),
                "exchange_rates_count": len(entry.get("snapshots", {}).get("exchange_rates", {})),
                "details": entry.get("details", {}),
            })
        except Exception as exc:
            print(f"config_store: could not read history entry {path}: {exc}")

        if len(entries) >= limit:
            break

    return entries


def get_history_entry(entry_id: str) -> Optional[Dict[str, Any]]:
    """Load a full history entry by ID (includes config snapshots)."""
    history_dir = _get_history_dir()
    path = history_dir / f"{entry_id}.json"
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as exc:
        print(f"config_store: could not read history entry {path}: {exc}")
        return None


def rollback_to_entry(entry_id: str, config_type: str = "both") -> Dict[str, Any]:
    """
    Restore configs from a history entry's snapshot.

    Args:
        entry_id: The history entry to rollback to.
        config_type: "account_mapping", "exchange_rates", or "both"

    Returns:
        Result dict with success status and what was restored.
    """
    entry = get_history_entry(entry_id)
    if entry is None:
        return {"success": False, "message": f"History entry '{entry_id}' not found."}

    snapshots = entry.get("snapshots", {})
    restored = []

    if config_type in ("account_mapping", "both"):
        mapping = snapshots.get("account_mapping", {})
        save_account_mapping(mapping)
        restored.append(f"account_mapping ({len(mapping)} accounts)")

    if config_type in ("exchange_rates", "both"):
        rates = snapshots.get("exchange_rates", {})
        save_exchange_rates(rates)
        restored.append(f"exchange_rates ({len(rates)} currencies)")

    # Record the rollback itself in history
    save_history_entry(
        action="rollback",
        config_type=config_type,
        details={
            "rolled_back_to": entry_id,
            "original_timestamp": entry.get("timestamp"),
        },
    )

    return {
        "success": True,
        "message": f"Rolled back to {entry_id}.",
        "restored": restored,
        "rolled_back_to_timestamp": entry.get("timestamp"),
    }
