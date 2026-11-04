"""Main CLI Entry Point: Run LangGraph Website Automation Pipeline.
"""
import sys
import argparse
from datetime import datetime

# Configure UTF-8 encoding for standard outputs on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
from config import (
    CRITERIA_PDF_PATH,
    CRITERIA_RULES_CACHE_PATH,
    GOOGLE_DOC_RULES_URL,
    BASE_DIR
)
from setup_criteria_pdf import generate_criteria_pdf
from graph import audit_app


def print_banner():
    banner = r"""
========================================================================
   LANGGRAPH WEBSITE AUTOMATION & AUDIT INTELLIGENCE PIPELINE
========================================================================
  [Workflow: Read -> Select -> Scrape -> Google Doc Live Rules
   -> Ollama llama3.2:1b -> Anti-Hallucination Corroborator -> Rank
   -> Placeholders -> Generate Content -> ReportLab PDF
   -> SMTP + Duplicate Guard -> Loop]
========================================================================
"""
    print(banner)


def main():
    parser = argparse.ArgumentParser(description="LangGraph Website Automation Audit Pipeline")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of companies to audit in this run")
    parser.add_argument("--doc-url", type=str, default=None, help="Google Doc URL containing live criteria reference rules")
    parser.add_argument("--no-banner", action="store_true", help="Suppress terminal startup banner")
    args = parser.parse_args()

    if not args.no_banner:
        print_banner()

    active_doc_url = args.doc_url or GOOGLE_DOC_RULES_URL

    # Step 0: Announce criteria rules source or initialize fallback
    if active_doc_url:
        print(f"[*] Criteria Rules Source: Live Google Doc ({active_doc_url})")
    elif CRITERIA_RULES_CACHE_PATH.exists():
        print(f"[*] Criteria Rules Source: Local Cached Google Doc ({CRITERIA_RULES_CACHE_PATH.name})")
    elif CRITERIA_PDF_PATH.exists():
        print(f"[*] Criteria Rules Source: Local Reference PDF ({CRITERIA_PDF_PATH.name})")
    else:
        print(f"[*] Initializing fallback criteria reference PDF at: {CRITERIA_PDF_PATH}...")
        generate_criteria_pdf(CRITERIA_PDF_PATH)
        print("[OK] Fallback criteria reference PDF created.")

    print(f"[*] Launching LangGraph pipeline execution at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}...\n")

    initial_state = {
        "companies": [],
        "current_index": 0,
        "current_company": None,
        "scraped_content": {},
        "criteria_reference_text": "",
        "google_doc_url": active_doc_url or None,
        "rules_source": None,
        "rules_hash": None,
        "rules_updated_at": None,
        "raw_evaluation": [],
        "verified_issues": [],
        "ranked_issues": [],
        "placeholders": {},
        "personalized_content": None,
        "pdf_path": None,
        "email_status": {},
        "logs": [],
        "has_more": False
    }

    try:
        # Run graph
        final_state = audit_app.invoke(initial_state)

        # Print Execution Logs
        print("\n" + "=" * 72)
        print("PIPELINE EXECUTION LOGS")
        print("=" * 72)
        for log in final_state.get("logs", []):
            print(f"  {log}")

        # Summary of audited companies
        print("\n" + "=" * 72)
        print("AUDIT RESULTS SUMMARY")
        print("=" * 72)
        companies = final_state.get("companies", [])
        for c in companies:
            print(f"  - Company: {c['company_name']}")
            print(f"    URL:     {c['website_url']}")
            print(f"    Status:  {c['status']}")
            print(f"    Report:  {c.get('report_path') or 'N/A'}")
            print(f"    Notes:   {c.get('notes') or 'N/A'}")
            print("  " + "-" * 68)

        print(f"\n[OK] Pipeline execution finished successfully. Total Companies Processed: {len(companies)}\n")

    except KeyboardInterrupt:
        print("\n[!] Execution interrupted by user.")
        sys.exit(1)
    except Exception as exc:
        print(f"\n[X] Pipeline encountered an unhandled exception: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
