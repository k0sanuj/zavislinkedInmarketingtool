"""
Service: Google Sheets Integration

Connects to Google Sheets API to read company names/URLs from a user's
spreadsheet. Supports selecting specific tabs and columns.
"""

import re
import logging
from typing import List, Optional, Tuple

import gspread
from google.oauth2.service_account import Credentials

from app.core.config import settings

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]


def _get_gspread_client() -> gspread.Client:
    """Authenticate with Google Sheets API using service account credentials."""
    creds = Credentials.from_service_account_file(
        settings.GOOGLE_CREDENTIALS_JSON, scopes=SCOPES
    )
    return gspread.authorize(creds)


def extract_sheet_id(url: str) -> str:
    """Extract the Google Sheet ID from a URL."""
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", url)
    if not match:
        raise ValueError(f"Could not extract sheet ID from URL: {url}")
    return match.group(1)


def get_sheet_tabs(sheet_url: str) -> List[str]:
    """Return the list of tab/worksheet names in a Google Sheet."""
    client = _get_gspread_client()
    sheet_id = extract_sheet_id(sheet_url)
    spreadsheet = client.open_by_key(sheet_id)
    return [ws.title for ws in spreadsheet.worksheets()]


def get_sheet_columns(sheet_url: str, tab_name: Optional[str] = None) -> List[str]:
    """Return column headers from the first row of a sheet tab."""
    client = _get_gspread_client()
    sheet_id = extract_sheet_id(sheet_url)
    spreadsheet = client.open_by_key(sheet_id)

    if tab_name:
        worksheet = spreadsheet.worksheet(tab_name)
    else:
        worksheet = spreadsheet.sheet1

    headers = worksheet.row_values(1)
    return headers


def read_column_values(
    sheet_url: str,
    column_name: str,
    tab_name: Optional[str] = None,
) -> Tuple[List[str], int]:
    """
    Read all values from a specific column in a Google Sheet.

    Returns:
        Tuple of (values list, total row count)
    """
    client = _get_gspread_client()
    sheet_id = extract_sheet_id(sheet_url)
    spreadsheet = client.open_by_key(sheet_id)

    if tab_name:
        worksheet = spreadsheet.worksheet(tab_name)
    else:
        worksheet = spreadsheet.sheet1

    headers = worksheet.row_values(1)
    if column_name not in headers:
        raise ValueError(
            f"Column '{column_name}' not found. Available columns: {headers}"
        )

    col_index = headers.index(column_name) + 1  # gspread is 1-indexed
    all_values = worksheet.col_values(col_index)

    # Skip header row, filter empty values
    values = [v.strip() for v in all_values[1:] if v.strip()]
    return values, len(values)


def read_csv_column(file_path: str, column_name: str) -> Tuple[List[str], int]:
    """Read values from a specific column in a CSV file."""
    import pandas as pd

    df = pd.read_csv(file_path)
    if column_name not in df.columns:
        raise ValueError(
            f"Column '{column_name}' not found. Available columns: {list(df.columns)}"
        )

    values = df[column_name].dropna().astype(str).str.strip().tolist()
    values = [v for v in values if v]
    return values, len(values)
