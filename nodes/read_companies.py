"""Node 1: Read Google Sheets / CSV
Loads the target company queue for the audit pipeline.
"""
import csv
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List
from urllib.parse import urlparse

# Ensure parent directory is in sys.path to allow standalone execution and imports
_parent_dir = str(Path(__file__).resolve().parent.parent)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from config import COMPANIES_CSV_PATH, GOOGLE_SERVICE_ACCOUNT_JSON, GOOGLE_SHEET_NAME
from state import AutomationState, CompanyRecord


def derive_name_from_url(url: str) -> str:
    """Extracts a readable company name from a URL when company_name is not provided."""
    try:
        parsed = urlparse(url if url.startswith("http") else "https://" + url)
        domain = parsed.netloc or parsed.path
        # Strip www. and TLD (e.g. www.acme.co.in → Acme)
        domain = domain.replace("www.", "").split(".")[0]
        return domain.replace("-", " ").replace("_", " ").title()
    except Exception:
        return url


def read_from_google_sheets() -> List[CompanyRecord]:
    """Attempts to read companies from Google Sheets if configured."""
    if not GOOGLE_SERVICE_ACCOUNT_JSON:
        print("[!] [Node 1] GOOGLE_SERVICE_ACCOUNT_JSON is not configured in .env")
        return []

    json_path = Path(GOOGLE_SERVICE_ACCOUNT_JSON)
    if not json_path.is_file():
        print(f"[!] [Node 1] Service account JSON file not found at: {json_path}")
        return []

    try:
        import gspread

        print(f"[*] [Node 1] Connecting to Google Sheet '{GOOGLE_SHEET_NAME}' using {json_path.name}...")
        # Modern gspread service_account authentication (no deprecated oauth2client needed)
        client = gspread.service_account(filename=str(json_path))
        sheet = client.open(GOOGLE_SHEET_NAME).sheet1
        records = sheet.get_all_records()

        companies: List[CompanyRecord] = []
        for i, row in enumerate(records, start=1):
            url = str(row.get("website_url", "") or "").strip()
            if not url:
                continue
            name = str(row.get("company_name", "") or "").strip() or derive_name_from_url(url)
            companies.append(CompanyRecord(
                id=str(row.get("id") or i),
                company_name=name,
                website_url=url,
                contact_name=str(row.get("contact_name", "") or "Decision Maker").strip(),
                contact_email=str(row.get("contact_email", "") or "").strip(),
                industry=str(row.get("industry", "") or "Technology").strip(),
                status=str(row.get("status", "") or "Pending").strip(),
                report_path=str(row.get("report_path", "") or "").strip() or None,
                notes=str(row.get("notes", "") or "").strip() or None,
                updated_at=str(row.get("updated_at", "") or "").strip() or None
            ))
        print(f"[OK] [Node 1] Successfully loaded {len(companies)} companies from Google Sheets!")
        return companies
    except Exception as e:
        print(f"[!] [Node 1] Failed to read from Google Sheets: {e}")
        return []


def read_from_csv() -> List[CompanyRecord]:
    """Reads companies from local CSV file."""
    companies: List[CompanyRecord] = []
    if not COMPANIES_CSV_PATH.exists():
        return companies

    with open(COMPANIES_CSV_PATH, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=1):
            url = str(row.get("website_url") or "").strip()
            if not url:
                continue
            name = str(row.get("company_name") or "").strip() or derive_name_from_url(url)

            companies.append(CompanyRecord(
                id=str(row.get("id") or i),
                company_name=name,
                website_url=url,
                contact_name=str(row.get("contact_name") or "Decision Maker").strip(),
                contact_email=str(row.get("contact_email") or "").strip(),
                industry=str(row.get("industry") or "Technology").strip(),
                status=str(row.get("status") or "Pending").strip(),
                report_path=str(row.get("report_path") or "").strip() or None,
                notes=str(row.get("notes") or "").strip() or None,
                updated_at=str(row.get("updated_at") or "").strip() or None
            ))
    return companies


def read_companies_node(state: AutomationState) -> Dict[str, Any]:
    """LangGraph node: Reads companies from Google Sheets or CSV."""
    logs = list(state.get("logs", []))
    logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] [Node 1] Reading companies queue...")

    # First attempt Google Sheets, then CSV
    companies = read_from_google_sheets()
    source = f"Google Sheets ({GOOGLE_SHEET_NAME})"

    if not companies:
        print(f"[*] [Node 1] Falling back to local CSV ({COMPANIES_CSV_PATH.name})...")
        companies = read_from_csv()
        source = f"CSV ({COMPANIES_CSV_PATH.name})"

    log_msg = f"[{datetime.now().strftime('%H:%M:%S')}] Loaded {len(companies)} company record(s) from {source}."
    logs.append(log_msg)
    print(f"[OK] [Node 1] {log_msg}")

    # Reset current_index to 0
    return {
        "companies": companies,
        "current_index": 0,
        "logs": logs,
        "has_more": len(companies) > 0
    }
