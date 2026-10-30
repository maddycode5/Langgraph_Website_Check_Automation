"""Node 8: Load Client-Specific Placeholders
Gathers company profile, contact data, and audit parameters into dynamic placeholders.
"""
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Ensure parent directory is in sys.path to allow standalone execution and imports
_parent_dir = str(Path(__file__).resolve().parent.parent)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from config import AGENCY_NAME, AUDITOR_NAME, AUDITOR_CONTACT
from state import AutomationState


def load_placeholders_node(state: AutomationState) -> Dict[str, Any]:
    """LangGraph node: Computes and injects client-specific placeholders."""
    company = state.get("current_company", {})
    ranked = state.get("ranked_issues", [])
    logs = list(state.get("logs", []))

    logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] [Node 8] Loading client-specific placeholders...")

    scores = [issue["score"] for issue in ranked]
    overall_avg = round(sum(scores) / len(scores), 1) if scores else 0.0

    weakest = ranked[0] if ranked else {"category": "Technical Optimization", "score": 0}
    strongest = ranked[-1] if ranked else {"category": "Baseline Availability", "score": 10}

    now = datetime.now()
    audit_date = now.strftime("%B %d, %Y")
    valid_until = now.replace(month=(now.month % 12) + 1).strftime("%B %d, %Y")

    placeholders = {
        "company_name": company.get("company_name", "Valued Client"),
        "contact_name": company.get("contact_name", "Decision Maker"),
        "contact_email": company.get("contact_email", ""),
        "website_url": company.get("website_url", ""),
        "industry": company.get("industry", "Technology"),
        "audit_date": audit_date,
        "valid_until": valid_until,
        "overall_score": f"{overall_avg} / 10",
        "overall_score_raw": str(overall_avg),
        "weakest_area": weakest["category"],
        "weakest_score": str(weakest["score"]),
        "strongest_area": strongest["category"],
        "strongest_score": str(strongest["score"]),
        "agency_name": AGENCY_NAME,
        "auditor_name": AUDITOR_NAME,
        "auditor_contact": AUDITOR_CONTACT,
        "report_title": f"Digital Performance & Conversion Audit — {company.get('company_name', '')}"
    }

    logs.append(
        f"[{datetime.now().strftime('%H:%M:%S')}] Placeholders loaded for {placeholders['company_name']} "
        f"(Overall: {overall_avg}/10, Primary Bottleneck: {placeholders['weakest_area']})."
    )

    return {
        "placeholders": placeholders,
        "logs": logs
    }
