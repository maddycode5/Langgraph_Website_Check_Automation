"""Node 4: Load Reference Rules / Criteria (Google Doc / PDF Fallback)
Backward-compatibility proxy that forwards to nodes.load_reference_rules.
"""
import sys
from pathlib import Path

# Ensure parent directory is in sys.path
_parent_dir = str(Path(__file__).resolve().parent.parent)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from nodes.load_reference_rules import (
    load_reference_rules_node,
    load_reference_pdf_node,
    extract_google_doc_id,
    fetch_google_doc_text,
    load_fallback_rubric,
    load_cached_rules,
    save_cached_rules
)

__all__ = [
    "load_reference_rules_node",
    "load_reference_pdf_node",
    "extract_google_doc_id",
    "fetch_google_doc_text",
    "load_fallback_rubric",
    "load_cached_rules",
    "save_cached_rules"
]
