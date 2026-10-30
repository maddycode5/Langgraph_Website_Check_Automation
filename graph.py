"""LangGraph Graph Definition: Website Automation Audit Pipeline.
Implements the 12-node sequential and looping workflow as specified.
"""
from typing import Literal
from langgraph.graph import StateGraph, START, END
from state import AutomationState
from nodes.read_companies import read_companies_node
from nodes.select_company import select_company_node
from nodes.scrape_website import scrape_website_node
from nodes.load_reference_pdf import load_reference_pdf_node
from nodes.evaluate_website import evaluate_website_node
from nodes.validate_evidence import validate_evidence_node
from nodes.rank_issues import rank_issues_node
from nodes.load_placeholders import load_placeholders_node
from nodes.generate_content import generate_content_node
from nodes.generate_pdf import generate_pdf_node
from nodes.email_report import email_report_node
from nodes.update_status import update_status_node


def check_initial_selection(state: AutomationState) -> Literal["scrape_website", "__end__"]:
    """Routes to scrape_website if a company was selected, or ends if queue is empty."""
    if state.get("current_company") is not None:
        return "scrape_website"
    return END


def check_remaining_companies(state: AutomationState) -> Literal["select_company", "__end__"]:
    """Conditional Edge: Routes back to 'select_company' if more companies remain, else END."""
    if state.get("has_more", False):
        return "select_company"
    return END


def build_audit_workflow() -> StateGraph:
    """Assembles and wires the LangGraph StateGraph pipeline."""
    workflow = StateGraph(AutomationState)

    # 1. Register All 12 Nodes
    workflow.add_node("read_companies", read_companies_node)
    workflow.add_node("select_company", select_company_node)
    workflow.add_node("scrape_website", scrape_website_node)
    workflow.add_node("load_reference_pdf", load_reference_pdf_node)
    workflow.add_node("evaluate_website", evaluate_website_node)
    workflow.add_node("validate_evidence", validate_evidence_node)
    workflow.add_node("rank_issues", rank_issues_node)
    workflow.add_node("load_placeholders", load_placeholders_node)
    workflow.add_node("generate_content", generate_content_node)
    workflow.add_node("generate_pdf", generate_pdf_node)
    workflow.add_node("email_report", email_report_node)
    workflow.add_node("update_status", update_status_node)

    # 2. Wire Linear Processing Edges
    workflow.add_edge(START, "read_companies")
    workflow.add_edge("read_companies", "select_company")

    workflow.add_conditional_edges(
        "select_company",
        check_initial_selection,
        {
            "scrape_website": "scrape_website_node" if False else "scrape_website",
            END: END
        }
    )

    workflow.add_edge("scrape_website", "load_reference_pdf")
    workflow.add_edge("load_reference_pdf", "evaluate_website")
    workflow.add_edge("evaluate_website", "validate_evidence")
    workflow.add_edge("validate_evidence", "rank_issues")
    workflow.add_edge("rank_issues", "load_placeholders")
    workflow.add_edge("load_placeholders", "generate_content")
    workflow.add_edge("generate_content", "generate_pdf")
    workflow.add_edge("generate_pdf", "email_report")
    workflow.add_edge("email_report", "update_status")

    # 3. Wire Loop Conditional Edge: [More Companies Remaining?] -> select_company / END
    workflow.add_conditional_edges(
        "update_status",
        check_remaining_companies,
        {
            "select_company": "select_company",
            END: END
        }
    )

    return workflow


# Compiled executable graph
audit_app = build_audit_workflow().compile()
