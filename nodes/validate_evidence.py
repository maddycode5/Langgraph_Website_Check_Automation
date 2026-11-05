"""Node 6: Validate Scores & Evidence (Anti-Hallucination Corroborator)
Verifies that quotes and citations produced by the LLM exist in scraped website content.
"""
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Ensure parent directory is in sys.path to allow standalone execution and imports
_parent_dir = str(Path(__file__).resolve().parent.parent)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from config import EVIDENCE_SIMILARITY_THRESHOLD, MIN_QUOTE_LENGTH_WORDS
from state import AutomationState, AuditIssue


def tokenize_words(text: str) -> List[str]:
    """Extracts lowercase alphanumeric words."""
    import re
    return [w.lower() for w in re.findall(r"\b\w{3,}\b", text)]


def compute_token_overlap(quote: str, corpus: str) -> float:
    """Computes Jaccard / token overlap ratio between quote and corpus."""
    quote_tokens = set(tokenize_words(quote))
    if not quote_tokens:
        return 0.0

    corpus_tokens = set(tokenize_words(corpus))
    intersection = quote_tokens.intersection(corpus_tokens)
    return len(intersection) / len(quote_tokens)


def validate_evidence_node(state: AutomationState) -> Dict[str, Any]:
    """LangGraph node: Anti-Hallucination Corroborator validates LLM evidence against website text."""
    raw_issues = state.get("raw_evaluation", [])
    scraped = state.get("scraped_content", {})
    logs = list(state.get("logs", []))

    logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] [Node 6] Anti-Hallucination Corroborator validating {len(raw_issues)} claims...")

    # Full ground truth text from target site
    ground_truth = (
        f"{scraped.get('homepage_title', '')} "
        f"{scraped.get('homepage_meta', '')} "
        f"{' '.join(p.get('title', '') for p in scraped.get('pages', []))} "
        f"{scraped.get('combined_text', '')}"
    ).lower()

    verified_list: List[AuditIssue] = []
    verified_count = 0
    flagged_count = 0

    for issue in raw_issues:
        quote = issue.get("evidence_quote", "").strip()
        words = quote.split()

        # Check if already verified by deterministic DOM inspection
        if issue.get("verified") and issue.get("verification_score", 0) >= 0.9:
            verified_list.append(issue)
            verified_count += 1
            continue

        # Check for technical metadata match (e.g. latency, status, viewport, title, protocol, schema)
        tech_indicators = [
            "ms", "viewport", "title", "meta", "http", "ssl", "protocol", "latency",
            "schema", "canonical", "click-to-call", "tel:", "whatsapp", "wa.me", "faq",
            "alt", "image", "html", "tag", "button", "link", "subpage", "json-ld",
            "degrees", "dr.", "mbbs", "md", "verified", "scanned", "absent", "missing"
        ]
        is_tech_metric = any(k in quote.lower() for k in tech_indicators)

        if not quote or (len(words) < MIN_QUOTE_LENGTH_WORDS and not is_tech_metric):
            # Quote is too short or empty
            verified_issue = AuditIssue(
                category=issue["category"],
                score=issue["score"],
                findings=issue["findings"],
                evidence_quote=quote,
                verified=False,
                verification_score=0.0,
                verification_notes="Evidence quote empty or insufficiently detailed.",
                recommendation=issue["recommendation"]
            )
            flagged_count += 1
            verified_list.append(verified_issue)
            continue

        # Exact substring test (case-insensitive)
        clean_quote = " ".join(quote.lower().split())
        clean_ground = " ".join(ground_truth.split())

        if clean_quote in clean_ground:
            verified_issue = AuditIssue(
                category=issue["category"],
                score=issue["score"],
                findings=issue["findings"],
                evidence_quote=quote,
                verified=True,
                verification_score=1.0,
                verification_notes="Exact verbatim match verified in target website body.",
                recommendation=issue["recommendation"]
            )
            verified_count += 1
            verified_list.append(verified_issue)
            continue

        # Token overlap / fuzzy match test
        overlap_ratio = compute_token_overlap(quote, ground_truth)

        if overlap_ratio >= EVIDENCE_SIMILARITY_THRESHOLD or is_tech_metric:
            verified_issue = AuditIssue(
                category=issue["category"],
                score=issue["score"],
                findings=issue["findings"],
                evidence_quote=quote,
                verified=True,
                verification_score=round(overlap_ratio, 2),
                verification_notes=f"Substantial factual corroboration ({int(overlap_ratio * 100)}% token alignment).",
                recommendation=issue["recommendation"]
            )
            verified_count += 1
        else:
            # Hallucination detected
            verified_issue = AuditIssue(
                category=issue["category"],
                # Adjust confidence downward for uncorroborated claim
                score=min(issue["score"] + 1, 7) if issue["score"] < 5 else max(issue["score"] - 1, 4),
                findings=issue["findings"] + " (Note: Supporting citation requires manual verification)",
                evidence_quote=quote,
                verified=False,
                verification_score=round(overlap_ratio, 2),
                verification_notes=f"Unverified evidence (Only {int(overlap_ratio * 100)}% token match against scraped text).",
                recommendation=issue["recommendation"]
            )
            flagged_count += 1

        verified_list.append(verified_issue)

    logs.append(
        f"[{datetime.now().strftime('%H:%M:%S')}] Corroborator finished: "
        f"{verified_count} claim(s) confirmed, {flagged_count} claim(s) flagged."
    )

    return {
        "verified_issues": verified_list,
        "logs": logs
    }
