"""Node 9: Generate Personalized Audit Content
Composes executive summary, tactical action plan, and personalized outreach message.
"""
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
from state import AutomationState, PersonalizedAuditContent


def query_ollama_content(prompt: str) -> str:
    """Invokes Ollama API for narrative generation."""
    endpoint = f"{OLLAMA_BASE_URL.rstrip('/')}/api/generate"
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.4
        }
    }
    resp = requests.post(endpoint, json=payload, timeout=OLLAMA_TIMEOUT_SECONDS)
    resp.raise_for_status()
    return resp.json().get("response", "").strip()


def generate_content_node(state: AutomationState) -> Dict[str, Any]:
    """LangGraph node: Synthesizes personalized audit narrative and executive outreach."""
    placeholders = state.get("placeholders", {})
    ranked = state.get("ranked_issues", [])
    logs = list(state.get("logs", []))

    logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] [Node 9] Generating personalized audit narrative...")

    company_name = placeholders.get("company_name", "your business")
    contact_name = placeholders.get("contact_name", "Decision Maker")
    industry = placeholders.get("industry", "Industry")
    weakest = ranked[0] if ranked else {"category": "Technical Optimization", "score": 4, "findings": "", "recommendation": ""}
    overall_score = float(placeholders.get("overall_score_raw", "6.5"))

    critical_fixes: List[str] = [
        f"{issue['category']} (Score: {issue['score']}/10): {issue['recommendation']}"
        for issue in ranked if issue['score'] <= 6
    ]
    if not critical_fixes and ranked:
        critical_fixes = [f"{ranked[0]['category']}: {ranked[0]['recommendation']}"]

    top_strengths: List[str] = [
        f"{issue['category']} (Score: {issue['score']}/10): {issue['findings']}"
        for issue in reversed(ranked) if issue['score'] >= 7
    ]
    if not top_strengths and ranked:
        top_strengths = [f"{ranked[-1]['category']}: Performing at baseline expectations."]

    # Default robust content synthesis
    exec_summary = (
        f"A comprehensive performance and conversion assessment was conducted for {company_name} "
        f"in the {industry} space. Across the 5 foundational evaluation pillars, {company_name} achieved "
        f"an aggregate score of {overall_score} out of 10. While core infrastructure demonstrates competence in "
        f"'{placeholders.get('strongest_area', 'Baseline Performance')}', significant commercial upside remains uncaptured "
        f"due to deficiencies in '{weakest['category']}' (scoring {weakest['score']}/10). Addressing these specific vulnerabilities "
        f"will directly reduce bounce rates and improve qualified inbound conversion."
    )

    outreach_subject = f"Digital Performance Audit for {company_name} ({placeholders.get('weakest_area')} Findings)"
    outreach_body = (
        f"Hi {contact_name},\n\n"
        f"Our research team recently analyzed the digital footprint and user experience for {company_name}. "
        f"We identified a high-impact bottleneck within your {weakest['category']} that may be constraining conversion efficiency.\n\n"
        f"We compiled a publication-grade audit report detailing our verified findings, exact page benchmarks, "
        f"and prioritized action steps (attached as PDF for your review).\n\n"
        f"Key Highlights:\n"
        f"• Overall Performance Rating: {overall_score}/10\n"
        f"• Primary Optimization Focus: {weakest['category']} ({weakest['score']}/10)\n"
        f"• Recommended Immediate Action: {weakest.get('recommendation', 'Schedule a 15-minute walkthrough')}\n\n"
        f"Best regards,\n"
        f"{placeholders.get('auditor_name', 'Audit Lead')}\n"
        f"{placeholders.get('agency_name', 'Apex Digital Insights')}"
    )

    # Attempt LLM polish if Ollama is accessible
    try:
        llm_prompt = f"""Write a professional 2-paragraph executive summary for {company_name} ({industry}).
Overall audit score: {overall_score}/10.
Primary weakness: {weakest['category']} ({weakest['score']}/10).
Recommendation: {weakest.get('recommendation', '')}.
Keep it concise, objective, authoritative, and focused on revenue growth."""
        llm_resp = query_ollama_content(llm_prompt)
        if len(llm_resp) > 80:
            exec_summary = llm_resp
            logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Executive summary enriched via Ollama {OLLAMA_MODEL}.")
    except Exception:
        logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Using deterministic narrative template.")

    content = PersonalizedAuditContent(
        executive_summary=exec_summary,
        primary_bottleneck=weakest["category"],
        top_strengths=top_strengths,
        critical_fixes=critical_fixes,
        outreach_subject=outreach_subject,
        outreach_body=outreach_body,
        overall_score=overall_score
    )

    return {
        "personalized_content": content,
        "logs": logs
    }
