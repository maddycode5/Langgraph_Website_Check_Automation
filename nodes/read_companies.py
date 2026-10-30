"""Node 1: Read Google Sheets / CSV
Loads the target company queue for the audit pipeline.
"""
import csv
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

# Ensure parent directory is in sys.path to allow standalone execution and imports
_parent_dir = str(Path(__file__).resolve().parent.parent)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from config import COMPANIES_CSV_PATH, GOOGLE_SERVICE_ACCOUNT_JSON, GOOGLE_SHEET_NAME
from state import AutomationState, CompanyRecord


def read_from_google_sheets() -> List[CompanyRecord]:
    """Attempts to read companies from Google Sheets if configured."""
    if not GOOGLE_SERVICE_ACCOUNT_JSON:
        return []

    json_path = Path(GOOGLE_SERVICE_ACCOUNT_JSON)
    if not json_path.is_file():
        return []

    try:
        import gspread

        # Modern gspread service_account authentication (no deprecated oauth2client needed)
        client = gspread.service_account(filename=str(json_path))
        sheet = client.open(GOOGLE_SHEET_NAME).sheet1
        records = sheet.get_all_records()

        companies: List[CompanyRecord] = []
        for i, row in enumerate(records, start=1):
            companies.append(CompanyRecord(
                id=str(row.get("id") or i),
                company_name=str(row.get("company_name", "")).strip(),
                website_url=str(row.get("website_url", "")).strip(),
                contact_name=str(row.get("contact_name", "")).strip(),
                contact_email=str(row.get("contact_email", "")).strip(),
                industry=str(row.get("industry", "General")).strip(),
                status=str(row.get("status", "Pending")).strip(),
                report_path=str(row.get("report_path", "")).strip() or None,
                notes=str(row.get("notes", "")).strip() or None,
                updated_at=str(row.get("updated_at", "")).strip() or None
            ))
        return companies
    except Exception as e:
        # Fall back gracefully to CSV
        return []


def read_from_csv() -> List[CompanyRecord]:
    """Reads companies from local CSV file."""
    companies: List[CompanyRecord] = []
    if not COMPANIES_CSV_PATH.exists():
        return companies

    with open(COMPANIES_CSV_PATH, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=1):
            name = row.get("company_name", "").strip()
            url = row.get("website_url", "").strip()
            if not name or not url:
                continue

            companies.append(CompanyRecord(
                id=str(row.get("id") or i),
                company_name=name,
                website_url=url,
                contact_name=row.get("contact_name", "Decision Maker").strip(),
                contact_email=row.get("contact_email", "").strip(),
                industry=row.get("industry", "Technology").strip(),
                status=row.get("status", "Pending").strip(),
                report_path=row.get("report_path", "").strip() or None,
                notes=row.get("notes", "").strip() or None,
                updated_at=row.get("updated_at", "").strip() or None
            ))
    return companies


def read_companies_node(state: AutomationState) -> Dict[str, Any]:
    """LangGraph node: Reads companies from Google Sheets or CSV."""
    logs = list(state.get("logs", []))
    logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] [Node 1] Reading companies queue...")

    # First attempt Google Sheets, then CSV
    companies = read_from_google_sheets()
    source = "Google Sheets"

    if not companies:
        companies = read_from_csv()
        source = f"CSV ({COMPANIES_CSV_PATH.name})"

    logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Loaded {len(companies)} company record(s) from {source}.")

    # Reset current_index to 0
    return {
        "companies": companies,
        "current_index": 0,
        "logs": logs,
        "has_more": len(companies) > 0
    }
