"""Node 2: Select Next Company
Picks the next company in the queue for processing.
"""
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

# Ensure parent directory is in sys.path to allow standalone execution and imports
_parent_dir = str(Path(__file__).resolve().parent.parent)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from state import AutomationState


def select_company_node(state: AutomationState) -> Dict[str, Any]:
    """LangGraph node: Selects next target company from the queue."""
    companies = state.get("companies", [])
    index = state.get("current_index", 0)
    logs = list(state.get("logs", []))

    if index < len(companies):
        current = companies[index]
        logs.append(
            f"[{datetime.now().strftime('%H:%M:%S')}] [Node 2] Selected Company [{index + 1}/{len(companies)}]: "
            f"'{current['company_name']}' ({current['website_url']})"
        )
        return {
            "current_company": current,
            "scraped_content": {},
            "raw_evaluation": [],
            "verified_issues": [],
            "ranked_issues": [],
            "placeholders": {},
            "personalized_content": None,
            "pdf_path": None,
            "email_status": {},
            "logs": logs,
            "has_more": True
        }
    else:
        logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] [Node 2] All companies have been processed.")
        return {
            "current_company": None,
            "has_more": False,
            "logs": logs
        }
