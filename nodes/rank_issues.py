"""Node 7: Rank Verified Issues (Weakest -> Strongest)
Orders verified audit issues from most critical deficiency to strongest asset.
"""
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Ensure parent directory is in sys.path to allow standalone execution and imports
_parent_dir = str(Path(__file__).resolve().parent.parent)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from state import AutomationState, AuditIssue


def rank_issues_node(state: AutomationState) -> Dict[str, Any]:
    """LangGraph node: Ranks verified issues from weakest (lowest score) to strongest."""
    issues = list(state.get("verified_issues", []))
    logs = list(state.get("logs", []))

    logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] [Node 7] Ranking issues from weakest to strongest...")

    # Sort primarily by score ascending (lowest score = weakest first)
    # Secondary sort by verification_score descending (most reliable first)
    ranked = sorted(
        issues,
        key=lambda item: (item["score"], -item.get("verification_score", 0.0))
    )

    summary_ranks = [f"{item['category']}: {item['score']}/10" for item in ranked]
    logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Issues ranked: {' -> '.join(summary_ranks)}")

    return {
        "ranked_issues": ranked,
        "logs": logs
    }
