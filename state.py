"""LangGraph State Definition for Website Automation Audit Pipeline."""
from typing import TypedDict, Optional, List, Dict, Any


class CompanyRecord(TypedDict):
    id: str
    company_name: str
    website_url: str
    contact_name: str
    contact_email: str
    industry: str
    status: str            # 'Pending', 'In Progress', 'Completed', 'Failed', 'Skipped'
    report_path: Optional[str]
    notes: Optional[str]
    updated_at: Optional[str]


class AuditIssue(TypedDict):
    category: str          # e.g., 'Performance', 'SEO & Metadata', 'Content & Clarity', 'Conversion & UX', 'Security & Trust'
    score: int             # 1 (Critical Weakness) to 10 (World-Class Strength)
    findings: str          # Description of the issue / observation
    evidence_quote: str    # Exact verbatim quote or metric extracted from the website
    verified: bool         # Validated by Anti-Hallucination Corroborator
    verification_score: float  # Confidence score (0.0 to 1.0)
    verification_notes: str    # Notes from verification process
    recommendation: str    # Actionable remediation step


class PersonalizedAuditContent(TypedDict):
    executive_summary: str
    primary_bottleneck: str
    top_strengths: List[str]
    critical_fixes: List[str]
    outreach_subject: str
    outreach_body: str
    overall_score: float


class AutomationState(TypedDict):
    # Company Pipeline Queue
    companies: List[CompanyRecord]
    current_index: int
    current_company: Optional[CompanyRecord]

    # Scraped Data
    scraped_content: Dict[str, Any]  # urls, combined_text, meta_tags, response_times, page_count

    # Reference PDF Criteria
    criteria_reference_text: str

    # LLM Evaluation & Validation
    raw_evaluation: List[AuditIssue]
    verified_issues: List[AuditIssue]
    ranked_issues: List[AuditIssue]  # Ranked Weakest -> Strongest

    # Client-Specific Context & Content
    placeholders: Dict[str, str]
    personalized_content: Optional[PersonalizedAuditContent]

    # Output Artifacts & Delivery
    pdf_path: Optional[str]
    email_status: Dict[str, Any]

    # Pipeline Diagnostics
    logs: List[str]
    has_more: bool
