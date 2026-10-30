"""Node 3: Scrape Website (Multi-Page Requests + BeautifulSoup)
Crawls homepage and key subpages, extracting structured text, headers, and metadata.
"""
import time
import sys
from pathlib import Path
from urllib.parse import urljoin, urlparse
from datetime import datetime
from typing import Dict, Any, List, Set
import requests
from bs4 import BeautifulSoup

# Ensure parent directory is in sys.path to allow standalone execution and imports
_parent_dir = str(Path(__file__).resolve().parent.parent)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from config import MAX_PAGES_PER_SITE, REQUEST_TIMEOUT_SECONDS, USER_AGENT
from state import AutomationState


def clean_text(text: str) -> str:
    """Normalizes whitespace and removes excessive blank lines."""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return "\n".join(lines)


def is_internal_url(base_url: str, target_url: str) -> bool:
    """Checks if a URL belongs to the same domain."""
    base_domain = urlparse(base_url).netloc.lower()
    target_domain = urlparse(target_url).netloc.lower()
    return base_domain == target_domain or not target_domain


def scrape_single_page(url: str, session: requests.Session) -> Dict[str, Any]:
    """Scrapes a single web page and extracts structured DOM elements."""
    start_time = time.time()
    try:
        resp = session.get(url, timeout=REQUEST_TIMEOUT_SECONDS, allow_redirects=True)
        latency_ms = round((time.time() - start_time) * 1000, 2)
        status_code = resp.status_code

        if status_code != 200:
            return {
                "url": url,
                "status_code": status_code,
                "latency_ms": latency_ms,
                "error": f"HTTP {status_code}",
                "title": "",
                "meta_description": "",
                "has_viewport": False,
                "headings": [],
                "text": "",
                "internal_links": []
            }

        soup = BeautifulSoup(resp.text, "html.parser")

        # Title
        title = soup.title.string.strip() if soup.title and soup.title.string else ""

        # Meta description
        meta_desc = ""
        desc_tag = soup.find("meta", attrs={"name": "description"}) or soup.find("meta", attrs={"property": "og:description"})
        if desc_tag and desc_tag.get("content"):
            meta_desc = desc_tag["content"].strip()

        # Viewport check
        viewport_tag = soup.find("meta", attrs={"name": "viewport"})
        has_viewport = bool(viewport_tag)

        # Headings (H1, H2, H3)
        headings: List[str] = []
        for h in soup.find_all(["h1", "h2", "h3"]):
            txt = h.get_text(strip=True)
            if txt:
                headings.append(f"{h.name.upper()}: {txt}")

        # Remove scripts, styles, noscript
        for unwanted in soup(["script", "style", "noscript", "svg", "header", "footer", "nav"]):
            unwanted.extract()

        body_text = clean_text(soup.get_text())

        # Collect internal candidate links
        internal_links: List[str] = []
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if not href or href.startswith("#") or href.startswith("mailto:") or href.startswith("tel:"):
                continue
            full_url = urljoin(url, href)
            if is_internal_url(url, full_url) and full_url not in internal_links:
                # Prioritize high value subpages
                lower_href = href.lower()
                if any(kw in lower_href for kw in ["about", "service", "pricing", "product", "contact", "feature", "faq"]):
                    internal_links.insert(0, full_url)
                else:
                    internal_links.append(full_url)

        return {
            "url": url,
            "status_code": status_code,
            "latency_ms": latency_ms,
            "error": None,
            "title": title,
            "meta_description": meta_desc,
            "has_viewport": has_viewport,
            "headings": headings[:15],
            "text": body_text[:4000],  # Bound text length for Ollama token limit
            "internal_links": internal_links[:10]
        }

    except Exception as exc:
        latency_ms = round((time.time() - start_time) * 1000, 2)
        return {
            "url": url,
            "status_code": 0,
            "latency_ms": latency_ms,
            "error": str(exc),
            "title": "",
            "meta_description": "",
            "has_viewport": False,
            "headings": [],
            "text": "",
            "internal_links": []
        }


def scrape_website_node(state: AutomationState) -> Dict[str, Any]:
    """LangGraph node: Scrapes target company homepage and key subpages."""
    company = state.get("current_company")
    logs = list(state.get("logs", []))

    if not company:
        return {"logs": logs}

    base_url = company["website_url"]
    if not base_url.startswith(("http://", "https://")):
        base_url = "https://" + base_url

    logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] [Node 3] Scraping website: {base_url} (Max {MAX_PAGES_PER_SITE} pages)")

    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT})

    visited: Set[str] = set()
    pages_data: List[Dict[str, Any]] = []

    # Scrape homepage
    home_page = scrape_single_page(base_url, session)
    pages_data.append(home_page)
    visited.add(base_url)

    # Scrape up to (MAX_PAGES_PER_SITE - 1) internal pages
    subpage_queue = [u for u in home_page.get("internal_links", []) if u not in visited]
    for subpage_url in subpage_queue:
        if len(pages_data) >= MAX_PAGES_PER_SITE:
            break
        if subpage_url in visited:
            continue
        visited.add(subpage_url)
        sub_data = scrape_single_page(subpage_url, session)
        pages_data.append(sub_data)

    # Combine text and extract summary metrics
    combined_body = "\n\n--- PAGE BREAK ---\n\n".join([
        f"Page: {p['url']}\nTitle: {p['title']}\nMeta: {p['meta_description']}\nHeadings:\n" +
        "\n".join(p['headings']) + f"\nContent:\n{p['text']}"
        for p in pages_data if p.get("text")
    ])

    avg_latency = (
        round(sum(p['latency_ms'] for p in pages_data) / len(pages_data), 1)
        if pages_data else 0.0
    )

    scraped_payload = {
        "base_url": base_url,
        "page_count": len(pages_data),
        "pages": pages_data,
        "combined_text": combined_body,
        "avg_latency_ms": avg_latency,
        "homepage_title": home_page.get("title", ""),
        "homepage_meta": home_page.get("meta_description", ""),
        "has_viewport": home_page.get("has_viewport", False),
        "status_code": home_page.get("status_code", 0),
        "error": home_page.get("error")
    }

    logs.append(
        f"[{datetime.now().strftime('%H:%M:%S')}] Successfully scraped {len(pages_data)} page(s). "
        f"Avg Latency: {avg_latency}ms. Body size: {len(combined_body)} chars."
    )

    return {
        "scraped_content": scraped_payload,
        "logs": logs
    }
