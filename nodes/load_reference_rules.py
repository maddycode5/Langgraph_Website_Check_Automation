"""Node 4: Load Reference Rules (Dynamic Google Doc / Real-Time Sync)
Extracts and synchronizes evaluation criteria and benchmark standards from a live Google Doc.
Monitors for document updates so changes made in the Google Doc are immediately reflected.
Provides automatic offline caching and graceful fallback to local PDF / rubric.
"""
import os
import re
import sys
import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
import requests

# Ensure parent directory is in sys.path to allow standalone execution and imports
_parent_dir = str(Path(__file__).resolve().parent.parent)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from config import (
    GOOGLE_DOC_RULES_URL,
    CRITERIA_PDF_PATH,
    CRITERIA_RULES_CACHE_PATH,
    CRITERIA_RULES_META_PATH,
    GOOGLE_SERVICE_ACCOUNT_JSON,
    USER_AGENT,
    REQUEST_TIMEOUT_SECONDS
)
from state import AutomationState


def extract_google_doc_id(url_or_id: str) -> Optional[str]:
    """Extracts the Google Doc ID from standard URLs, share links, or raw IDs."""
    if not url_or_id or not isinstance(url_or_id, str):
        return None
    url_or_id = url_or_id.strip()

    # Case 1: Published doc URL (/document/d/e/<id>/pub) - handled separately
    if "/document/d/e/" in url_or_id:
        return None

    # Case 2: Standard doc URL (including multi-account /u/0/d/ or /a/domain/d/)
    match = re.search(r"/document/(?:u/\d+/|a/[^/]+/)?d/([a-zA-Z0-9_-]+)", url_or_id)
    if match:
        return match.group(1)

    # General /d/<id> match if present in docs/drive url
    if "docs.google.com" in url_or_id or "drive.google.com" in url_or_id:
        match = re.search(r"/d/([a-zA-Z0-9_-]{20,})", url_or_id)
        if match:
            return match.group(1)

    # Case 3: Google Drive file URL (/file/d/<id>)
    match = re.search(r"/file/d/([a-zA-Z0-9_-]+)", url_or_id)
    if match:
        return match.group(1)

    # Case 4: Query parameter ?id=<id>
    match = re.search(r"[?&]id=([a-zA-Z0-9_-]+)", url_or_id)
    if match:
        return match.group(1)

    # Case 5: Direct Doc ID string (typically 25+ base64url characters)
    if re.fullmatch(r"[a-zA-Z0-9_-]{25,}", url_or_id):
        return url_or_id

    return None


def is_published_google_doc(url: str) -> bool:
    """Checks if the URL is a Google Doc published to the web (/pub)."""
    return bool(url and "/document/d/e/" in url)


def fetch_from_published_doc(url: str, timeout: int = 15) -> str:
    """Extracts text content from a Google Doc published to the web."""
    headers = {"User-Agent": USER_AGENT}
    resp = requests.get(url, headers=headers, timeout=timeout)
    resp.raise_for_status()

    from bs4 import BeautifulSoup
    soup = BeautifulSoup(resp.text, "html.parser")
    for tag in soup(["script", "style", "noscript", "header", "footer"]):
        tag.decompose()

    contents_div = soup.find("div", {"id": "contents"}) or soup.find("div", {"id": "doc"})
    if contents_div:
        text = contents_div.get_text(separator="\n")
    else:
        text = soup.get_text(separator="\n")

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


def fetch_from_service_account(doc_id: str) -> str:
    """Uses Google Drive API with Service Account credentials for private documents."""
    if not GOOGLE_SERVICE_ACCOUNT_JSON:
        raise ValueError("GOOGLE_SERVICE_ACCOUNT_JSON not set.")

    creds_path = Path(GOOGLE_SERVICE_ACCOUNT_JSON)
    if not creds_path.is_file():
        raise FileNotFoundError(f"Service account file not found: {creds_path}")

    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    scopes = [
        "https://www.googleapis.com/auth/drive.readonly",
        "https://www.googleapis.com/auth/documents.readonly"
    ]
    creds = service_account.Credentials.from_service_account_file(str(creds_path), scopes=scopes)
    service = build("drive", "v3", credentials=creds)

    # Export document as plain text
    content = service.files().export(fileId=doc_id, mimeType="text/plain").execute()
    if isinstance(content, bytes):
        return content.decode("utf-8").lstrip("\ufeff")
    return str(content).lstrip("\ufeff")


def fetch_google_doc_text(doc_url_or_id: str, timeout: int = 15) -> Tuple[str, str]:
    """Fetches the latest plain text of a Google Doc from its link or ID.

    Returns:
        (rules_text, identifier)
    """
    clean_url = doc_url_or_id.strip()

    # 1. Published to web link
    if is_published_google_doc(clean_url):
        text = fetch_from_published_doc(clean_url, timeout=timeout)
        if not text.strip():
            raise ValueError("Fetched published Google Doc was empty.")
        return text.strip(), clean_url

    # 2. Extract Document ID for standard Google Docs
    doc_id = extract_google_doc_id(clean_url)
    if not doc_id:
        raise ValueError(
            f"Could not parse a valid Google Doc ID from provided URL: '{clean_url}'. "
            "Expected format: https://docs.google.com/document/d/<DOCUMENT_ID>/edit"
        )

    export_url = f"https://docs.google.com/document/d/{doc_id}/export?format=txt"
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/plain,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
    }

    resp = requests.get(export_url, headers=headers, timeout=timeout, allow_redirects=True)

    # Detect redirect to Google Accounts sign-in (private doc)
    is_login_redirect = (
        "accounts.google.com" in resp.url
        or "ServiceLogin" in resp.url
        or ("<html" in resp.text[:200].lower() and "Sign in" in resp.text[:500])
    )

    if is_login_redirect or resp.status_code in (401, 403):
        # Attempt fallback to Service Account if configured
        if GOOGLE_SERVICE_ACCOUNT_JSON and Path(GOOGLE_SERVICE_ACCOUNT_JSON).is_file():
            sa_text = fetch_from_service_account(doc_id)
            return sa_text.strip(), doc_id
        else:
            raise PermissionError(
                f"Google Doc '{doc_id}' is private and not accessible without authentication. "
                "Please configure 'Anyone with the link can view' on Google Docs, "
                "or supply GOOGLE_SERVICE_ACCOUNT_JSON in .env."
            )

    resp.raise_for_status()

    # Clean UTF-8 Byte Order Mark (BOM) and strip
    text = resp.text.lstrip("\ufeff").strip()
    if not text:
        raise ValueError("Google Doc was retrieved but contained no readable text.")

    return text, doc_id


def load_cached_rules() -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """Loads previously cached criteria rules and metadata from disk."""
    if not CRITERIA_RULES_CACHE_PATH.exists():
        return None, None

    try:
        with open(CRITERIA_RULES_CACHE_PATH, "r", encoding="utf-8") as f:
            text = f.read()

        meta = None
        if CRITERIA_RULES_META_PATH.exists():
            with open(CRITERIA_RULES_META_PATH, "r", encoding="utf-8") as f:
                meta = json.load(f)

        return text, meta
    except Exception:
        return None, None


def save_cached_rules(text: str, doc_url: str, doc_id: str) -> Tuple[Dict[str, Any], bool]:
    """Saves rules to cache and detects whether content has changed (dynamic update).

    Returns:
        (meta_dict, is_changed)
    """
    CRITERIA_RULES_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    new_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()

    _, prev_meta = load_cached_rules()
    prev_hash = prev_meta.get("sha256") if prev_meta else None
    prev_version = prev_meta.get("version", 0) if prev_meta else 0

    is_changed = (new_hash != prev_hash)
    version = prev_version + 1 if is_changed else prev_version

    meta = {
        "doc_url": doc_url,
        "doc_id": doc_id,
        "sha256": new_hash,
        "version": max(version, 1),
        "char_count": len(text),
        "line_count": len(text.splitlines()),
        "last_fetched": datetime.now().isoformat(),
        "last_updated": datetime.now().isoformat() if is_changed else (prev_meta.get("last_updated") if prev_meta else datetime.now().isoformat())
    }

    # Write cache text and metadata
    try:
        with open(CRITERIA_RULES_CACHE_PATH, "w", encoding="utf-8") as f:
            f.write(text)
        with open(CRITERIA_RULES_META_PATH, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)
    except Exception:
        pass

    return meta, is_changed


def load_fallback_rubric() -> str:
    """Loads fallback rubric from PDF if available, otherwise returns built-in benchmark."""
    if CRITERIA_PDF_PATH.exists():
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(str(CRITERIA_PDF_PATH))
            pages = []
            for page_idx in range(len(doc)):
                t = doc[page_idx].get_text().strip()
                if t:
                    pages.append(f"--- BENCHMARK RUBRIC (Page {page_idx + 1}) ---\n{t}")
            doc.close()
            if pages:
                return "\n\n".join(pages)
        except Exception:
            pass

    # Built-in Standard 5-Pillar Rubric
    return (
        "WEBSITE AUDIT EVALUATION CRITERIA & BENCHMARK RUBRIC:\n"
        "1. Technical SEO & Metadata (Title 40-60 chars, Meta description, H1 hierarchy, Canonical)\n"
        "2. Speed, Performance & Mobile Responsiveness (Latency < 600ms, Viewport meta tag)\n"
        "3. Content Clarity & Value Proposition (Hero 5-second clarity, benefits vs features)\n"
        "4. Conversion Architecture & UX (Prominent CTA, low form friction, clean navigation)\n"
        "5. Trust Signals, Security & Compliance (SSL/HTTPS, verified social proof, contact info)"
    )


def load_reference_rules_node(state: AutomationState) -> Dict[str, Any]:
    """LangGraph Node 4: Loads and synchronizes evaluation criteria from Google Doc.
    
    Checks the configured Google Doc URL on every execution:
    - If changes are detected in the Google Doc, fresh rules are applied immediately.
    - If unchanged, verifies active version.
    - If offline / error, falls back to local cache or reference PDF.
    """
    logs = list(state.get("logs", []))
    now_str = datetime.now().strftime("%H:%M:%S")

    # Determine Google Doc URL (State override -> Config / Environment)
    doc_url = state.get("google_doc_url") or GOOGLE_DOC_RULES_URL
    rules_text = ""
    rules_source = "Built-in Standard Rubric"
    rules_hash = state.get("rules_hash")
    rules_updated_at = state.get("rules_updated_at")

    if doc_url:
        logs.append(f"[{now_str}] [Node 4] Synchronizing criteria rules from Google Doc: {doc_url[:50]}...")
        try:
            live_text, doc_identifier = fetch_google_doc_text(doc_url, timeout=REQUEST_TIMEOUT_SECONDS)
            meta, is_changed = save_cached_rules(live_text, doc_url, doc_identifier)

            rules_text = live_text
            rules_source = f"Google Doc (live v{meta['version']})"
            rules_hash = meta["sha256"]
            rules_updated_at = meta["last_updated"]

            if is_changed:
                logs.append(
                    f"[{now_str}] [Node 4] Google Doc rules UPDATED! Detected remote document changes "
                    f"(v{meta['version']}, SHA: {rules_hash[:8]}..., {len(rules_text)} chars). Applied fresh rules."
                )
            else:
                logs.append(
                    f"[{now_str}] [Node 4] Google Doc rules verified: Up-to-date "
                    f"(v{meta['version']}, SHA: {rules_hash[:8]}..., {len(rules_text)} chars)."
                )

        except Exception as exc:
            logs.append(f"[{now_str}] [Node 4] Warning: Live Google Doc fetch failed ({exc}). Checking local cache...")
            cached_text, cached_meta = load_cached_rules()
            if cached_text:
                rules_text = cached_text
                version_str = f" v{cached_meta['version']}" if cached_meta else ""
                rules_source = f"Google Doc (cached{version_str})"
                rules_hash = cached_meta.get("sha256") if cached_meta else None
                rules_updated_at = cached_meta.get("last_updated") if cached_meta else None
                logs.append(
                    f"[{now_str}] [Node 4] Restored {len(cached_text)} chars of rules from local cache "
                    f"(cached on {rules_updated_at or 'previous run'})."
                )
            else:
                logs.append(f"[{now_str}] [Node 4] No local Google Doc cache found. Falling back to local PDF / rubric...")
                rules_text = load_fallback_rubric()
                rules_source = "Local PDF / Rubric Fallback"
    else:
        # No Google Doc URL configured
        cached_text, cached_meta = load_cached_rules()
        if cached_text:
            rules_text = cached_text
            rules_source = "Google Doc (cached)"
            rules_hash = cached_meta.get("sha256") if cached_meta else None
            rules_updated_at = cached_meta.get("last_updated") if cached_meta else None
            logs.append(
                f"[{now_str}] [Node 4] No GOOGLE_DOC_RULES_URL provided. Using previously cached rules "
                f"({len(cached_text)} chars, last updated: {rules_updated_at})."
            )
        else:
            logs.append(
                f"[{now_str}] [Node 4] Note: GOOGLE_DOC_RULES_URL not configured. "
                "Using local benchmark reference (PDF / rubric). "
                "To link live Google Doc, set GOOGLE_DOC_RULES_URL in .env or pass --doc-url."
            )
            rules_text = load_fallback_rubric()
            rules_source = "Local PDF / Rubric Fallback"

    return {
        "criteria_reference_text": rules_text,
        "rules_source": rules_source,
        "rules_hash": rules_hash,
        "rules_updated_at": rules_updated_at,
        "logs": logs
    }


# Backwards-compatibility alias for existing imports
load_reference_pdf_node = load_reference_rules_node


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Test Google Doc Rules Synchronizer")
    parser.add_argument("--url", type=str, default=GOOGLE_DOC_RULES_URL or None, help="Google Doc URL to test")
    args = parser.parse_args()

    test_state = AutomationState(
        companies=[],
        current_index=0,
        current_company=None,
        scraped_content={},
        criteria_reference_text="",
        google_doc_url=args.url,
        rules_source=None,
        rules_hash=None,
        rules_updated_at=None,
        raw_evaluation=[],
        verified_issues=[],
        ranked_issues=[],
        placeholders={},
        personalized_content=None,
        pdf_path=None,
        email_status={},
        logs=[],
        has_more=False
    )
    result = load_reference_rules_node(test_state)
    print("\n--- TEST EXECUTION RESULT ---")
    print(f"Source:  {result.get('rules_source')}")
    print(f"Hash:    {result.get('rules_hash')}")
    print(f"Updated: {result.get('rules_updated_at')}")
    print(f"Length:  {len(result.get('criteria_reference_text', ''))} characters")
    print("\nLogs:")
    for l in result.get("logs", []):
        print(" ", l)
    print("\nContent Preview (First 300 chars):")
    print(result.get("criteria_reference_text", "")[:300])
