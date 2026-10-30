"""Node 4: Load Reference PDF (PyMuPDF - criteria_reference.pdf)
Extracts evaluation criteria and benchmark standards from criteria_reference.pdf.
"""
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

# Ensure parent directory is in sys.path to allow standalone execution and imports
_parent_dir = str(Path(__file__).resolve().parent.parent)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from config import CRITERIA_PDF_PATH
from state import AutomationState
from setup_criteria_pdf import generate_criteria_pdf


def load_reference_pdf_node(state: AutomationState) -> Dict[str, Any]:
    """LangGraph node: Uses PyMuPDF (fitz) to load and parse criteria_reference.pdf."""
    logs = list(state.get("logs", []))
    logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] [Node 4] Loading criteria reference PDF: {CRITERIA_PDF_PATH.name}")

    # Ensure criteria_reference.pdf exists
    if not CRITERIA_PDF_PATH.exists():
        logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Reference PDF not found. Auto-generating standardized rubric PDF...")
        generate_criteria_pdf(CRITERIA_PDF_PATH)

    pdf_text = ""
    try:
        import fitz  # PyMuPDF

        doc = fitz.open(str(CRITERIA_PDF_PATH))
        pages_content = []
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            text = page.get_text()
            if text.strip():
                pages_content.append(f"--- CRITERIA PAGE {page_idx + 1} ---\n{text.strip()}")
        doc.close()

        pdf_text = "\n\n".join(pages_content)
        logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Successfully parsed {len(pages_content)} page(s) via PyMuPDF ({len(pdf_text)} characters).")

    except ImportError:
        logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] WARNING: PyMuPDF (fitz) not installed. Using built-in rubric standards.")
        pdf_text = (
            "WEBSITE AUDIT EVALUATION CRITERIA:\n"
            "1. Technical SEO & Metadata (Title, Meta description, H1 hierarchy, Canonical)\n"
            "2. Speed, Performance & Mobile Responsiveness (Latency < 600ms, Viewport meta)\n"
            "3. Content Clarity & Value Proposition (Hero 5-second clarity, benefits vs features)\n"
            "4. Conversion Architecture & UX (Prominent CTA, low form friction, clean navigation)\n"
            "5. Trust Signals, Security & Compliance (SSL/HTTPS, social proof, contact details)"
        )
    except Exception as exc:
        logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Error reading PDF via PyMuPDF: {exc}. Using fallback rubric text.")
        pdf_text = "5-Pillar Website Audit Standards: SEO, Performance, Content Clarity, UX/Conversion, Trust & Security."

    return {
        "criteria_reference_text": pdf_text,
        "logs": logs
    }
