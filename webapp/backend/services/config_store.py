"""
Config Store — Configuration persistence layer (SQLite backend)

All configuration is stored in a single SQLite database file: ctr_fx.db

  Desktop (.exe): %LOCALAPPDATA%/CTR-FX-Remeasurement/ctr_fx.db
  Dev (script):   webapp/backend/ctr_fx.db

Three tables:

1. account_mapping
   Columns: account_number (PK), account_type, monetary, rate
   Keyed by account_number — one row per GL account.

2. exchange_rates
   Columns: id (PK), rate_type, from_currency, to_currency, valid_from, exchange_rate
   Supports multiple rates per currency pair across time periods.
   Rate lookup: most recent valid_from on or before the query date.

3. config_history
   Append-only audit trail. Each row captures full JSON snapshots of both
   live tables at the moment of the action for rollback support.

Both configs support two upload modes:
  - "replace" — DELETE all + INSERT new rows
  - "merge"   — INSERT OR REPLACE (incoming wins on same key)

Both can be exported as styled Excel files for sharing between desktop users.

Public API
----------
load_account_mapping() -> list[dict]
save_account_mapping(rows: list[dict]) -> None
reset_account_mapping() -> None
parse_account_mapping_file(file_path: str) -> tuple[list[dict], list[str]]
merge_account_mapping(existing: list[dict], incoming: list[dict]) -> list[dict]
export_account_mapping(output_path: str) -> str

load_exchange_rates() -> list[dict]
save_exchange_rates(rows: list[dict]) -> None
reset_exchange_rates() -> None
parse_exchange_rates_file(file_path: str) -> tuple[list[dict], list[str]]
merge_exchange_rates(existing: list[dict], incoming: list[dict]) -> list[dict]
export_exchange_rates(output_path: str) -> str
get_exchange_rate(from_ccy: str, to_ccy: str, as_of_date: str) -> float | None

save_history_entry(action, config_type, mode=None, source_filename=None, details=None) -> str
list_history(limit=50) -> list[dict]
get_history_entry(entry_id: str) -> dict | None
rollback_to_entry(entry_id: str, config_type="both") -> dict
"""

import json
import os
import sqlite3
import sys
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

_APP_DATA_DIR_NAME = "CTR-FX-Remeasurement"

# Styling for exported Excel files
_HEADER_FONT = Font(name="Calibri", bold=True, size=11)
_HEADER_FILL = PatternFill(patternType="solid", fgColor="B3E5FC")
_HEADER_ALIGNMENT = Alignment(horizontal="center", vertical="center")


def _get_app_data_dir() -> Path:
    """
    Resolve the root data directory for the application.

    - Desktop (PyInstaller .exe): %LOCALAPPDATA%/CTR-FX-Remeasurement/
      Per-user, no admin rights needed, survives .exe updates.
    - Dev (running as script): backend/ directory.
    """
    if getattr(sys, "frozen", False):
        local_app_data = os.environ.get("LOCALAPPDATA")
        if local_app_data:
            base_path = Path(local_app_data) / _APP_DATA_DIR_NAME
        else:
            base_path = Path.home() / ".local" / "share" / _APP_DATA_DIR_NAME
        base_path.mkdir(parents=True, exist_ok=True)
    else:
        base_path = Path(__file__).parent.parent

    return base_path


def _get_db_path() -> Path:
    return _get_app_data_dir() / "ctr_fx.db"


# ---------------------------------------------------------------------------
# Database initialisation
# ---------------------------------------------------------------------------

def _init_db(conn: sqlite3.Connection) -> None:
    """Create tables and indexes if they do not exist."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS account_mapping (
            account_number TEXT PRIMARY KEY,
            account_type   TEXT NOT NULL,
            monetary       TEXT NOT NULL,
            rate           TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS exchange_rates (
            id            TEXT PRIMARY KEY,
            rate_type     TEXT,
            from_currency TEXT NOT NULL,
            to_currency   TEXT NOT NULL,
            valid_from    TEXT NOT NULL,
            exchange_rate REAL NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_er_lookup
            ON exchange_rates (from_currency, to_currency, valid_from);

        CREATE TABLE IF NOT EXISTS config_history (
            id                       TEXT PRIMARY KEY,
            timestamp                TEXT NOT NULL,
            action                   TEXT NOT NULL,
            config_type              TEXT NOT NULL,
            source_filename          TEXT,
            details                  TEXT,
            snapshot_account_mapping TEXT,
            snapshot_exchange_rates  TEXT
        );
    """)


def _get_db() -> sqlite3.Connection:
    """
    Open ctr_fx.db, initialise schema, set row_factory, and return the
    connection.  Use as a context manager so the connection auto-commits
    (or rolls back on exception) and is closed when the block exits.

        with _get_db() as conn:
            conn.execute(...)
    """
    conn = sqlite3.connect(str(_get_db_path()))
    conn.row_factory = sqlite3.Row
    _init_db(conn)
    return conn


# ---------------------------------------------------------------------------
# Account Mapping — SQLite persistence
# ---------------------------------------------------------------------------

def load_account_mapping() -> List[Dict[str, Any]]:
    """
    Load all rows from the account_mapping table.

    Returns:
        list of dicts with keys: account_number, account_type, monetary, rate.
        Empty list if the table is empty.
    """
    try:
        with _get_db() as conn:
            cursor = conn.execute(
                "SELECT account_number, account_type, monetary, rate "
                "FROM account_mapping ORDER BY account_number"
            )
            return [dict(row) for row in cursor.fetchall()]
    except Exception as exc:
        print(f"config_store: could not load account_mapping: {exc}")
        return []


def save_account_mapping(rows: List[Dict[str, Any]]) -> None:
    """
    Replace all account_mapping rows.

    Performs DELETE all + bulk INSERT in a single transaction.
    """
    try:
        with _get_db() as conn:
            conn.execute("DELETE FROM account_mapping")
            conn.executemany(
                "INSERT INTO account_mapping (account_number, account_type, monetary, rate) "
                "VALUES (:account_number, :account_type, :monetary, :rate)",
                rows,
            )
    except Exception as exc:
        print(f"config_store: could not save account_mapping: {exc}")


def reset_account_mapping() -> None:
    """Delete all rows from account_mapping."""
    try:
        with _get_db() as conn:
            conn.execute("DELETE FROM account_mapping")
    except Exception as exc:
        print(f"config_store: could not reset account_mapping: {exc}")


# ---------------------------------------------------------------------------
# Account Mapping — file parsing, merging, exporting
# ---------------------------------------------------------------------------

_ACCOUNT_MAPPING_COLUMNS = {
    "account_number": [
        "account number", "account_number", "accountnumber",
        "acct number", "acct_number", "gl account",
    ],
    "account_type": [
        "account type", "account_type", "accounttype", "type", "acct type",
    ],
    "monetary": [
        "monetary", "monetary?", "is monetary", "is_monetary",
    ],
    "rate": [
        "rate", "rate type", "rate_type", "rate method",
    ],
}


def _find_column(df_columns: List[str], aliases: List[str]) -> Optional[str]:
    """Return the first DataFrame column name that matches any alias (case-insensitive)."""
    df_cols_lower = {c.strip().lower(): c for c in df_columns}
    for alias in aliases:
        if alias.lower() in df_cols_lower:
            return df_cols_lower[alias.lower()]
    return None


def parse_account_mapping_file(
    file_path: str,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Parse an uploaded account mapping file (CSV or Excel).

    Expected columns: Account Number, Account Type, Monetary, Rate
    Column names are matched case-insensitively with common aliases.

    Returns:
        (rows, warnings) where rows is a list of dicts with keys
        account_number, account_type, monetary, rate.
    """
    warnings: List[str] = []

    try:
        if file_path.lower().endswith(".csv"):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
    except Exception as exc:
        return [], [f"Could not read file: {exc}"]

    df.columns = [str(c).strip() for c in df.columns]

    acct_col = _find_column(df.columns.tolist(), _ACCOUNT_MAPPING_COLUMNS["account_number"])
    type_col = _find_column(df.columns.tolist(), _ACCOUNT_MAPPING_COLUMNS["account_type"])
    monetary_col = _find_column(df.columns.tolist(), _ACCOUNT_MAPPING_COLUMNS["monetary"])
    rate_col = _find_column(df.columns.tolist(), _ACCOUNT_MAPPING_COLUMNS["rate"])

    if acct_col is None:
        return [], [
            "Account Number column not found. Expected one of: "
            + ", ".join(_ACCOUNT_MAPPING_COLUMNS["account_number"])
        ]

    if type_col is None:
        warnings.append("Account Type column not found — will be set to empty string for all entries.")
    if monetary_col is None:
        warnings.append("Monetary column not found — will be set to empty string for all entries.")
    if rate_col is None:
        warnings.append("Rate column not found — will be set to empty string for all entries.")

    rows: List[Dict[str, Any]] = []
    for _, row in df.iterrows():
        acct_num = str(row[acct_col]).strip()
        if not acct_num or acct_num == "nan":
            continue

        account_type = ""
        if type_col and pd.notna(row.get(type_col)):
            account_type = str(row[type_col]).strip()

        monetary = ""
        if monetary_col and pd.notna(row.get(monetary_col)):
            monetary = str(row[monetary_col]).strip()

        rate = ""
        if rate_col and pd.notna(row.get(rate_col)):
            rate = str(row[rate_col]).strip()

        rows.append({
            "account_number": acct_num,
            "account_type": account_type,
            "monetary": monetary,
            "rate": rate,
        })

    warnings.append(f"Parsed {len(rows)} account(s) from file.")
    return rows, warnings


def merge_account_mapping(
    existing: List[Dict[str, Any]],
    incoming: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Merge incoming rows into existing. Incoming wins on same account_number.

    Returns merged list (no duplicates by account_number).
    """
    merged: Dict[str, Dict[str, Any]] = {r["account_number"]: r for r in existing}
    for row in incoming:
        merged[row["account_number"]] = row
    return list(merged.values())


def export_account_mapping(output_path: str) -> str:
    """
    Export current account mapping as a styled Excel file for sharing.

    Returns the output file path.
    """
    rows = load_account_mapping()

    wb = Workbook()
    ws = wb.active
    ws.title = "Account Mapping"

    headers = ["Account Number", "Account Type", "Monetary", "Rate"]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = _HEADER_FONT
        cell.fill = _HEADER_FILL
        cell.alignment = _HEADER_ALIGNMENT

    for row in rows:
        ws.append([
            row.get("account_number", ""),
            row.get("account_type", ""),
            row.get("monetary", ""),
            row.get("rate", ""),
        ])

    wb.save(output_path)
    return output_path


# ---------------------------------------------------------------------------
# Exchange Rates — SQLite persistence
# ---------------------------------------------------------------------------

_EXCHANGE_RATES_COLUMNS = {
    "id": [
        "objectid", "object_id", "id",
    ],
    "rate_type": [
        "ratetype", "rate_type", "rate type", "type",
    ],
    "from_currency": [
        "fromcurrency", "from_currency", "from currency", "from ccy",
    ],
    "to_currency": [
        "tocurrency", "to_currency", "to currency", "to ccy",
    ],
    "valid_from": [
        "validfrom", "valid_from", "valid from", "date", "effective date",
    ],
    "exchange_rate": [
        "exchangerate", "exchange_rate", "exchange rate", "rate", "fx rate",
    ],
}


def load_exchange_rates() -> List[Dict[str, Any]]:
    """
    Load all rows from the exchange_rates table.

    Returns:
        list of dicts with keys: id, rate_type, from_currency, to_currency,
        valid_from, exchange_rate.
        Empty list if the table is empty.
    """
    try:
        with _get_db() as conn:
            cursor = conn.execute(
                "SELECT id, rate_type, from_currency, to_currency, valid_from, exchange_rate "
                "FROM exchange_rates ORDER BY from_currency, to_currency, valid_from"
            )
            return [dict(row) for row in cursor.fetchall()]
    except Exception as exc:
        print(f"config_store: could not load exchange_rates: {exc}")
        return []


def save_exchange_rates(rows: List[Dict[str, Any]]) -> None:
    """
    Replace all exchange_rates rows.

    Performs DELETE all + bulk INSERT in a single transaction.
    """
    try:
        with _get_db() as conn:
            conn.execute("DELETE FROM exchange_rates")
            conn.executemany(
                "INSERT INTO exchange_rates "
                "(id, rate_type, from_currency, to_currency, valid_from, exchange_rate) "
                "VALUES (:id, :rate_type, :from_currency, :to_currency, :valid_from, :exchange_rate)",
                rows,
            )
    except Exception as exc:
        print(f"config_store: could not save exchange_rates: {exc}")


def reset_exchange_rates() -> None:
    """Delete all rows from exchange_rates."""
    try:
        with _get_db() as conn:
            conn.execute("DELETE FROM exchange_rates")
    except Exception as exc:
        print(f"config_store: could not reset exchange_rates: {exc}")


def get_exchange_rate(
    from_ccy: str,
    to_ccy: str,
    as_of_date: str,
) -> Optional[float]:
    """
    Find the most recent exchange rate for a currency pair on or before as_of_date.

    Args:
        from_ccy:    Contract currency code (e.g. "EUR").
        to_ccy:      Company currency code (e.g. "USD").
        as_of_date:  ISO date string "YYYY-MM-DD".

    Returns:
        The exchange_rate float, or None if no matching row is found.
    """
    try:
        with _get_db() as conn:
            cursor = conn.execute(
                "SELECT exchange_rate FROM exchange_rates "
                "WHERE from_currency = ? AND to_currency = ? "
                "  AND valid_from <= ? "
                "ORDER BY valid_from DESC LIMIT 1",
                (from_ccy.upper(), to_ccy.upper(), as_of_date),
            )
            row = cursor.fetchone()
            return float(row["exchange_rate"]) if row else None
    except Exception as exc:
        print(f"config_store: could not look up exchange rate: {exc}")
        return None


# ---------------------------------------------------------------------------
# Exchange Rates — file parsing, merging, exporting
# ---------------------------------------------------------------------------

def parse_exchange_rates_file(
    file_path: str,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Parse an uploaded exchange rates file (CSV or Excel).

    Expected columns: id/ObjectId, RateType, FromCurrency, ToCurrency,
    ValidFrom, ExchangeRate.  Column names matched case-insensitively.

    - Currency codes are normalised to uppercase.
    - valid_from is parsed to ISO date string YYYY-MM-DD.
    - id is generated (uuid4) when the column is absent.

    Returns:
        (rows, warnings) where rows is a list of dicts with keys
        id, rate_type, from_currency, to_currency, valid_from, exchange_rate.
    """
    warnings: List[str] = []

    try:
        if file_path.lower().endswith(".csv"):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path)
    except Exception as exc:
        return [], [f"Could not read file: {exc}"]

    df.columns = [str(c).strip() for c in df.columns]
    col_list = df.columns.tolist()

    id_col = _find_column(col_list, _EXCHANGE_RATES_COLUMNS["id"])
    rate_type_col = _find_column(col_list, _EXCHANGE_RATES_COLUMNS["rate_type"])
    from_col = _find_column(col_list, _EXCHANGE_RATES_COLUMNS["from_currency"])
    to_col = _find_column(col_list, _EXCHANGE_RATES_COLUMNS["to_currency"])
    valid_from_col = _find_column(col_list, _EXCHANGE_RATES_COLUMNS["valid_from"])
    rate_col = _find_column(col_list, _EXCHANGE_RATES_COLUMNS["exchange_rate"])

    if from_col is None:
        return [], [
            "FromCurrency column not found. Expected one of: "
            + ", ".join(_EXCHANGE_RATES_COLUMNS["from_currency"])
        ]
    if to_col is None:
        return [], [
            "ToCurrency column not found. Expected one of: "
            + ", ".join(_EXCHANGE_RATES_COLUMNS["to_currency"])
        ]
    if valid_from_col is None:
        return [], [
            "ValidFrom column not found. Expected one of: "
            + ", ".join(_EXCHANGE_RATES_COLUMNS["valid_from"])
        ]
    if rate_col is None:
        return [], [
            "ExchangeRate column not found. Expected one of: "
            + ", ".join(_EXCHANGE_RATES_COLUMNS["exchange_rate"])
        ]

    if id_col is None:
        warnings.append("ID/ObjectId column not found — generating UUIDs for all rows.")

    rows: List[Dict[str, Any]] = []
    for _, row in df.iterrows():
        from_ccy = str(row[from_col]).strip().upper()
        to_ccy = str(row[to_col]).strip().upper()

        if not from_ccy or from_ccy == "NAN":
            continue
        if not to_ccy or to_ccy == "NAN":
            continue

        # Parse valid_from to ISO date string
        raw_date = row[valid_from_col]
        try:
            if isinstance(raw_date, str):
                valid_from = pd.to_datetime(raw_date).strftime("%Y-%m-%d")
            else:
                valid_from = pd.Timestamp(raw_date).strftime("%Y-%m-%d")
        except Exception:
            warnings.append(
                f"Skipping row — could not parse date '{raw_date}' for {from_ccy}/{to_ccy}."
            )
            continue

        # Parse exchange_rate
        try:
            exchange_rate = float(row[rate_col])
        except (TypeError, ValueError):
            warnings.append(
                f"Skipping non-numeric rate for {from_ccy}/{to_ccy} on {valid_from}: "
                f"{row[rate_col]!r}"
            )
            continue

        # Resolve ID
        if id_col and pd.notna(row.get(id_col)):
            row_id = str(row[id_col]).strip()
        else:
            row_id = str(uuid.uuid4())

        # Rate type (optional)
        rate_type = None
        if rate_type_col and pd.notna(row.get(rate_type_col)):
            rate_type = str(row[rate_type_col]).strip()

        rows.append({
            "id": row_id,
            "rate_type": rate_type,
            "from_currency": from_ccy,
            "to_currency": to_ccy,
            "valid_from": valid_from,
            "exchange_rate": exchange_rate,
        })

    warnings.append(f"Parsed {len(rows)} exchange rate(s) from file.")
    return rows, warnings


def merge_exchange_rates(
    existing: List[Dict[str, Any]],
    incoming: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Merge incoming rows into existing. Incoming wins on same id.

    Returns merged list (no duplicates by id).
    """
    merged: Dict[str, Dict[str, Any]] = {r["id"]: r for r in existing}
    for row in incoming:
        merged[row["id"]] = row
    return list(merged.values())


def export_exchange_rates(output_path: str) -> str:
    """
    Export current exchange rates as a styled Excel file for sharing.

    Returns the output file path.
    """
    rows = load_exchange_rates()

    wb = Workbook()
    ws = wb.active
    ws.title = "Exchange Rates"

    headers = ["ObjectId", "RateType", "FromCurrency", "ToCurrency", "ValidFrom", "ExchangeRate"]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = _HEADER_FONT
        cell.fill = _HEADER_FILL
        cell.alignment = _HEADER_ALIGNMENT

    rate_format = '_-* #,##0.0000_-;-* #,##0.0000_-;_-* "-"??_-;_-@_-'
    for row in rows:
        ws.append([
            row.get("id", ""),
            row.get("rate_type", ""),
            row.get("from_currency", ""),
            row.get("to_currency", ""),
            row.get("valid_from", ""),
            row.get("exchange_rate", ""),
        ])
        ws.cell(row=ws.max_row, column=6).number_format = rate_format

    wb.save(output_path)
    return output_path


# ---------------------------------------------------------------------------
# History — append-only audit trail with config snapshots for rollback
# ---------------------------------------------------------------------------

def save_history_entry(
    action: str,
    config_type: str,
    mode: Optional[str] = None,
    source_filename: Optional[str] = None,
    details: Optional[Any] = None,
) -> str:
    """
    Insert a new history row with a snapshot of both live tables at this moment.

    Args:
        action:          "upload", "reset", "rollback"
        config_type:     "account_mapping", "exchange_rates", "both"
        mode:            Upload mode used — "replace", "merge", or None
        source_filename: Name of the uploaded file (if applicable)
        details:         Any extra info (dict, str, etc.) serialised to JSON

    Returns:
        The new history entry's UUID id string.
    """
    entry_id = str(uuid.uuid4())
    timestamp = datetime.now().isoformat()

    # Capture live snapshots
    snapshot_am = json.dumps(load_account_mapping(), ensure_ascii=False)
    snapshot_er = json.dumps(load_exchange_rates(), ensure_ascii=False)

    # Serialise details — accept dict, str, or None
    if details is None:
        details_str = None
    elif isinstance(details, str):
        details_str = details
    else:
        details_str = json.dumps(details, ensure_ascii=False)

    # Fold mode into details when present so it is not silently dropped
    # (the schema has no dedicated mode column)
    if mode is not None:
        try:
            details_obj = json.loads(details_str) if details_str else {}
            if isinstance(details_obj, dict):
                details_obj.setdefault("mode", mode)
                details_str = json.dumps(details_obj, ensure_ascii=False)
        except Exception:
            pass

    try:
        with _get_db() as conn:
            conn.execute(
                "INSERT INTO config_history "
                "(id, timestamp, action, config_type, source_filename, details, "
                " snapshot_account_mapping, snapshot_exchange_rates) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    entry_id,
                    timestamp,
                    action,
                    config_type,
                    source_filename,
                    details_str,
                    snapshot_am,
                    snapshot_er,
                ),
            )
    except Exception as exc:
        print(f"config_store: could not save history entry: {exc}")

    return entry_id


def list_history(limit: int = 50) -> List[Dict[str, Any]]:
    """
    List history entries, most recent first.

    Returns summaries without snapshot columns to keep responses lightweight.
    """
    try:
        with _get_db() as conn:
            cursor = conn.execute(
                "SELECT id, timestamp, action, config_type, source_filename, details, "
                "       snapshot_account_mapping, snapshot_exchange_rates "
                "FROM config_history "
                "ORDER BY timestamp DESC "
                "LIMIT ?",
                (limit,),
            )
            entries = []
            for row in cursor.fetchall():
                # Deserialise details back to its original type when possible
                raw_details = row["details"]
                try:
                    details_val = json.loads(raw_details) if raw_details else None
                except Exception:
                    details_val = raw_details

                # Count rows in snapshots for the summary
                try:
                    am_count = len(json.loads(row["snapshot_account_mapping"] or "[]"))
                except Exception:
                    am_count = 0
                try:
                    er_count = len(json.loads(row["snapshot_exchange_rates"] or "[]"))
                except Exception:
                    er_count = 0

                entries.append({
                    "id": row["id"],
                    "timestamp": row["timestamp"],
                    "action": row["action"],
                    "config_type": row["config_type"],
                    "source_filename": row["source_filename"],
                    "details": details_val,
                    "account_mapping_count": am_count,
                    "exchange_rates_count": er_count,
                })
            return entries
    except Exception as exc:
        print(f"config_store: could not list history: {exc}")
        return []


def get_history_entry(entry_id: str) -> Optional[Dict[str, Any]]:
    """
    Load a full history entry by ID, including config snapshots.

    Snapshots are returned as Python objects (lists of dicts), not raw JSON.
    """
    try:
        with _get_db() as conn:
            cursor = conn.execute(
                "SELECT id, timestamp, action, config_type, source_filename, details, "
                "       snapshot_account_mapping, snapshot_exchange_rates "
                "FROM config_history WHERE id = ?",
                (entry_id,),
            )
            row = cursor.fetchone()
        if row is None:
            return None

        raw_details = row["details"]
        try:
            details_val = json.loads(raw_details) if raw_details else None
        except Exception:
            details_val = raw_details

        try:
            am_snapshot = json.loads(row["snapshot_account_mapping"] or "[]")
        except Exception:
            am_snapshot = []
        try:
            er_snapshot = json.loads(row["snapshot_exchange_rates"] or "[]")
        except Exception:
            er_snapshot = []

        return {
            "id": row["id"],
            "timestamp": row["timestamp"],
            "action": row["action"],
            "config_type": row["config_type"],
            "source_filename": row["source_filename"],
            "details": details_val,
            "snapshots": {
                "account_mapping": am_snapshot,
                "exchange_rates": er_snapshot,
            },
        }
    except Exception as exc:
        print(f"config_store: could not get history entry '{entry_id}': {exc}")
        return None


def rollback_to_entry(
    entry_id: str,
    config_type: str = "both",
) -> Dict[str, Any]:
    """
    Restore configs from a history entry's snapshot.

    Args:
        entry_id:    The history entry to roll back to.
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
        am_rows = snapshots.get("account_mapping", [])
        save_account_mapping(am_rows)
        restored.append(f"account_mapping ({len(am_rows)} accounts)")

    if config_type in ("exchange_rates", "both"):
        er_rows = snapshots.get("exchange_rates", [])
        save_exchange_rates(er_rows)
        restored.append(f"exchange_rates ({len(er_rows)} rates)")

    # Record the rollback itself so the audit trail is complete
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
