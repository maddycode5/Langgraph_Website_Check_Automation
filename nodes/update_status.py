"""Node 12: Update Google Sheets / CSV (Status, Path, Timestamp)
Synchronizes audit status, output PDF file paths, and timestamps to persistent storage.
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


def update_local_csv(updated_companies: List[CompanyRecord]) -> None:
    """Writes updated company records back to local CSV."""
    if not updated_companies:
        return

    csv_path = Path(COMPANIES_CSV_PATH)
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "id", "company_name", "website_url", "contact_name",
        "contact_email", "industry", "status", "report_path", "notes", "updated_at"
    ]
    with open(csv_path, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for c in updated_companies:
            writer.writerow({
                "id": c.get("id", ""),
                "company_name": c.get("company_name", ""),
                "website_url": c.get("website_url", ""),
                "contact_name": c.get("contact_name", ""),
                "contact_email": c.get("contact_email", ""),
                "industry": c.get("industry", ""),
                "status": c.get("status", "Completed"),
                "report_path": c.get("report_path") or "",
                "notes": c.get("notes") or "",
                "updated_at": c.get("updated_at") or ""
            })


def update_google_sheet_if_available(company: CompanyRecord, row_idx: int) -> bool:
    """Updates row in Google Sheets if credentials are configured and file exists."""
    if not GOOGLE_SERVICE_ACCOUNT_JSON:
        return False

    json_path = Path(GOOGLE_SERVICE_ACCOUNT_JSON)
    if not json_path.is_file():
        return False

    try:
        import gspread

        # Modern gspread service_account authentication (no deprecated oauth2client needed)
        client = gspread.service_account(filename=str(json_path))
        sheet = client.open(GOOGLE_SHEET_NAME).sheet1

        # Update columns (assuming standard schema): status(7), report_path(8), notes(9), updated_at(10)
        sheet_row = row_idx + 2  # account for 1-based indexing and header row
        sheet.update_cell(sheet_row, 7, company.get("status", "Completed"))
        sheet.update_cell(sheet_row, 8, company.get("report_path", ""))
        sheet.update_cell(sheet_row, 9, company.get("notes", ""))
        sheet.update_cell(sheet_row, 10, company.get("updated_at", ""))
        return True
    except Exception:
        return False


def update_status_node(state: AutomationState) -> Dict[str, Any]:
    """LangGraph node: Updates CSV/Sheets, increments queue pointer, checks for remaining companies."""
    companies = list(state.get("companies", []))
    idx = state.get("current_index", 0)
    current_company = state.get("current_company")
    pdf_path = state.get("pdf_path")
    email_status = state.get("email_status", {})
    placeholders = state.get("placeholders", {})
    logs = list(state.get("logs", []))

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if current_company and idx < len(companies):
        status_text = "Completed" if email_status.get("sent") else "Completed (Email Skipped)"
        score_note = f"Score: {placeholders.get('overall_score_raw', 'N/A')}/10 | {email_status.get('reason', 'OK')}"

        updated_record: CompanyRecord = {
            "id": current_company["id"],
            "company_name": current_company["company_name"],
            "website_url": current_company["website_url"],
            "contact_name": current_company["contact_name"],
            "contact_email": current_company["contact_email"],
            "industry": current_company["industry"],
            "status": status_text,
            "report_path": pdf_path or "",
            "notes": score_note,
            "updated_at": timestamp
        }

        companies[idx] = updated_record
        update_local_csv(companies)
        update_google_sheet_if_available(updated_record, idx)

        logs.append(
            f"[{datetime.now().strftime('%H:%M:%S')}] [Node 12] Persistent storage updated for '{current_company['company_name']}': "
            f"Status={status_text}, Path={pdf_path}"
        )

    # Increment current_index to advance queue
    next_index = idx + 1
    has_more = next_index < len(companies)

    if has_more:
        logs.append(
            f"[{datetime.now().strftime('%H:%M:%S')}] Loop Check: {len(companies) - next_index} company/companies remaining in queue. "
            f"Cycling back to [Select Next Company]..."
        )
    else:
        logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Loop Check: Queue exhausted. All {len(companies)} companies audited. Proceeding to [END].")

    return {
        "companies": companies,
        "current_index": next_index,
        "has_more": has_more,
        "logs": logs
    }
