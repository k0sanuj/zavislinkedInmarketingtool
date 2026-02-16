"""
Quick test: verify Google Sheets credentials are working.

Usage:
    python test_google_setup.py "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit"
"""

import sys
import os
import json


def check_credentials_file():
    """Check if credentials.json exists and looks valid."""
    cred_path = os.path.join(os.path.dirname(__file__), "credentials.json")

    if not os.path.exists(cred_path):
        print("[FAIL] credentials.json not found in backend/ folder")
        print("       Download it from Google Cloud Console > Service Accounts > Keys")
        return None

    try:
        with open(cred_path) as f:
            data = json.load(f)
    except json.JSONDecodeError:
        print("[FAIL] credentials.json is not valid JSON")
        return None

    required_fields = ["type", "project_id", "client_email"]
    for field in required_fields:
        if field not in data:
            print(f"[FAIL] credentials.json is missing '{field}' — are you sure this is a service account key?")
            return None

    print(f"[OK]   credentials.json found")
    print(f"       Project: {data['project_id']}")
    print(f"       Service account email: {data['client_email']}")
    print()
    print(f"  >>> IMPORTANT: Share your Google Sheet with this email: <<<")
    print(f"      {data['client_email']}")
    print()
    return data["client_email"]


def test_sheet_access(sheet_url):
    """Try to read the sheet."""
    try:
        import gspread
        from google.oauth2.service_account import Credentials
    except ImportError:
        print("[FAIL] Required packages not installed. Run:")
        print("       pip install gspread google-auth")
        return

    cred_path = os.path.join(os.path.dirname(__file__), "credentials.json")
    creds = Credentials.from_service_account_file(
        cred_path,
        scopes=[
            "https://www.googleapis.com/auth/spreadsheets.readonly",
            "https://www.googleapis.com/auth/drive.readonly",
        ],
    )
    client = gspread.authorize(creds)

    # Extract sheet ID
    import re
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", sheet_url)
    if not match:
        print(f"[FAIL] Could not extract sheet ID from URL: {sheet_url}")
        return

    sheet_id = match.group(1)
    print(f"[OK]   Sheet ID: {sheet_id}")

    try:
        spreadsheet = client.open_by_key(sheet_id)
        print(f"[OK]   Successfully opened sheet: '{spreadsheet.title}'")
    except gspread.exceptions.SpreadsheetNotFound:
        print(f"[FAIL] Sheet not found. Did you share it with the service account email?")
        return
    except gspread.exceptions.APIError as e:
        print(f"[FAIL] API error: {e}")
        print("       Make sure Google Sheets API is enabled in your GCP project")
        return

    # List tabs
    tabs = [ws.title for ws in spreadsheet.worksheets()]
    print(f"[OK]   Tabs found: {tabs}")

    # Read first tab headers
    ws = spreadsheet.sheet1
    headers = ws.row_values(1)
    print(f"[OK]   Columns in first tab: {headers}")

    # Count rows
    all_values = ws.get_all_values()
    print(f"[OK]   Total rows (including header): {len(all_values)}")

    print()
    print("  >>> Google Sheets setup is WORKING! <<<")


if __name__ == "__main__":
    print("=" * 60)
    print("  Google Sheets Setup Checker")
    print("=" * 60)
    print()

    email = check_credentials_file()
    if not email:
        sys.exit(1)

    if len(sys.argv) > 1:
        sheet_url = sys.argv[1]
        print(f"Testing access to sheet: {sheet_url}")
        print()
        test_sheet_access(sheet_url)
    else:
        print("To test sheet access, run:")
        print('  python test_google_setup.py "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit"')
        print()
        print("But first, make sure you share the sheet with the service account email above!")
