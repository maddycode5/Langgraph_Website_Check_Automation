"""Node 5: LLM Evaluates Website (Ollama: llama3.2:1b)
Uses local Ollama llama3.2:1b to assess website content against reference rubric.
"""
import json
import re
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List
import requests

# Ensure parent directory is in sys.path to allow standalone execution and imports
_parent_dir = str(Path(__file__).resolve().parent.parent)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from config import OLLAMA_BASE_URL, OLLAMA_MODEL, OLLAMA_TIMEOUT_SECONDS
from state import AutomationState, AuditIssue


def query_ollama_direct(prompt: str) -> str:
    """Invokes Ollama API directly via HTTP request."""
    endpoint = f"{OLLAMA_BASE_URL.rstrip('/')}/api/generate"
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.2,
            "top_p": 0.9
        }
    }
    response = requests.post(endpoint, json=payload, timeout=OLLAMA_TIMEOUT_SECONDS)
    response.raise_for_status()
    data = response.json()
    return data.get("response", "")


def extract_json_array(text: str) -> List[Dict[str, Any]]:
    """Extracts JSON array from LLM response text."""
    # Match markdown json block
    match = re.search(r"```(?:json)?\s*(\[\s*\{.*?\}\s*\])\s*```", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass

    # Match raw bracket array
    match = re.search(r"(\[\s*\{.*\}\s*\])", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except Exception:
            pass

    return []


def fallback_heuristic_evaluation(scraped_content: Dict[str, Any]) -> List[AuditIssue]:
    """Provides objective heuristic scores and extracted quotes if Ollama is unreachable."""
    title = scraped_content.get("homepage_title", "")
    meta = scraped_content.get("homepage_meta", "")
    has_viewport = scraped_content.get("has_viewport", False)
    latency = scraped_content.get("avg_latency_ms", 0)
    body = scraped_content.get("combined_text", "")

    # Extract first sentence for evidence quote
    first_lines = [l.strip() for l in body.splitlines() if len(l.strip()) > 20]
    sample_quote = first_lines[0] if first_lines else "No sample text found"

    # SEO Score
    seo_score = 8 if (title and meta and 30 <= len(title) <= 65) else (5 if title else 2)
    seo_evidence = f"Title tag: '{title[:45]}...'" if title else "Title tag is missing"

    # Performance Score
    perf_score = 9 if latency < 400 else (7 if latency < 1000 else 4)
    perf_evidence = f"Average server latency measured at {latency}ms across pages"

    # Content Clarity Score
    clarity_score = 7 if len(body) > 300 else 4
    clarity_evidence = sample_quote[:120]

    # UX / Conversion Score
    ux_score = 7 if has_viewport else 4
    ux_evidence = "Viewport meta tag present for mobile responsiveness" if has_viewport else "Viewport meta tag missing"

    # Trust Score
    trust_score = 8 if "https://" in scraped_content.get("base_url", "") else 3
    trust_evidence = f"Base URL protocol: {scraped_content.get('base_url', '')}"

    return [
        AuditIssue(
            category="Technical SEO & Metadata",
            score=seo_score,
            findings="Evaluation of search indexing meta tags and heading structure.",
            evidence_quote=seo_evidence,
            verified=False,
            verification_score=0.0,
            verification_notes="",
            recommendation="Optimize meta title (40-60 chars) and meta description with core commercial keywords."
        ),
        AuditIssue(
            category="Speed & Performance",
            score=perf_score,
            findings="Server response time and asset delivery speed across scanned pages.",
            evidence_quote=perf_evidence,
            verified=False,
            verification_score=0.0,
            verification_notes="",
            recommendation="Enable HTTP/2, edge caching, and media compression to keep latency below 500ms."
        ),
        AuditIssue(
            category="Content Clarity & UVP",
            score=clarity_score,
            findings="Hero headline clarity and target audience value articulation.",
            evidence_quote=clarity_evidence,
            verified=False,
            verification_score=0.0,
            verification_notes="",
            recommendation="Refactor the primary hero headline into a clear 5-second customer outcome proposition."
        ),
        AuditIssue(
            category="Conversion & UX",
            score=ux_score,
            findings="Call-to-action prominence and mobile layout configuration.",
            evidence_quote=ux_evidence,
            verified=False,
            verification_score=0.0,
            verification_notes="",
            recommendation="Place a high-contrast primary CTA above the fold and simplify contact forms."
        ),
        AuditIssue(
            category="Trust & Security",
            score=trust_score,
            findings="SSL certificate status, contact details, and compliance signals.",
            evidence_quote=trust_evidence,
            verified=False,
            verification_score=0.0,
            verification_notes="",
            recommendation="Showcase verifiable social proof, security badges, and clear terms of service."
        )
    ]


def evaluate_website_node(state: AutomationState) -> Dict[str, Any]:
    """LangGraph node: Prompts Ollama llama3.2:1b to evaluate the website against reference criteria."""
    company = state.get("current_company")
    scraped = state.get("scraped_content", {})
    criteria = state.get("criteria_reference_text", "")
    logs = list(state.get("logs", []))

    if not company:
        return {"logs": logs}

    logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] [Node 5] Evaluating website with Ollama ({OLLAMA_MODEL})...")

    prompt = f"""You are a world-class digital audit expert. Evaluate this website against the reference criteria rubric.

TARGET COMPANY:
Name: {company['company_name']}
URL: {company['website_url']}
Industry: {company['industry']}

REFERENCE CRITERIA (Benchmark Rubric):
{criteria[:1200]}

WEBSITE SCRAPED DATA:
Homepage Title: {scraped.get('homepage_title')}
Meta Description: {scraped.get('homepage_meta')}
Server Latency: {scraped.get('avg_latency_ms')}ms
Mobile Viewport Configured: {scraped.get('has_viewport')}
Scraped Content Snippet:
{scraped.get('combined_text', '')[:3000]}

INSTRUCTIONS:
Evaluate the website across exactly 5 categories:
1. Technical SEO & Metadata
2. Speed & Performance
3. Content Clarity & UVP
4. Conversion & UX
5. Trust & Security

For EACH category, you MUST:
- Assign an integer score from 1 (Critical Weakness) to 10 (World-Class Strength).
- Write a concise finding (1-2 sentences).
- Provide an EXACT VERBATIM quote or metric directly extracted from the scraped text above as evidence. DO NOT fabricate or invent quotes.
- Provide a concrete, high-ROI recommendation.

OUTPUT FORMAT:
Return ONLY a valid JSON array containing 5 objects with keys: "category", "score", "findings", "evidence_quote", "recommendation".
Example:
[
  {{
    "category": "Technical SEO & Metadata",
    "score": 6,
    "findings": "Meta description is missing on the homepage.",
    "evidence_quote": "Meta: ",
    "recommendation": "Add a 150-character meta description targeting high-intent buyer keywords."
  }}
]
"""

    raw_evaluations: List[AuditIssue] = []

    try:
        response_text = query_ollama_direct(prompt)
        parsed_array = extract_json_array(response_text)

        if parsed_array and len(parsed_array) >= 3:
            for item in parsed_array:
                raw_evaluations.append(AuditIssue(
                    category=str(item.get("category", "General Audit")),
                    score=int(item.get("score", 5)),
                    findings=str(item.get("findings", "")),
                    evidence_quote=str(item.get("evidence_quote", "")),
                    verified=False,
                    verification_score=0.0,
                    verification_notes="",
                    recommendation=str(item.get("recommendation", ""))
                ))
            logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Ollama evaluation completed successfully with {len(raw_evaluations)} categories.")
        else:
            logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Ollama output format invalid or truncated. Falling back to heuristic baseline.")
            raw_evaluations = fallback_heuristic_evaluation(scraped)

    except Exception as exc:
        logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Ollama unavailable ({exc}). Using heuristic evaluation engine.")
        raw_evaluations = fallback_heuristic_evaluation(scraped)

    return {
        "raw_evaluation": raw_evaluations,
        "logs": logs
    }
