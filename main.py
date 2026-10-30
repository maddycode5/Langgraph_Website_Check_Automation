"""Main CLI Entry Point: Run LangGraph Website Automation Pipeline.
"""
import sys
import argparse
from datetime import datetime
from config import CRITERIA_PDF_PATH, BASE_DIR
from setup_criteria_pdf import generate_criteria_pdf
from graph import audit_app


def print_banner():
    banner = r"""
========================================================================
   LANGGRAPH WEBSITE AUTOMATION & AUDIT INTELLIGENCE PIPELINE
========================================================================
  [Workflow: Read -> Select -> Scrape -> PyMuPDF -> Ollama llama3.2:1b
   -> Anti-Hallucination Corroborator -> Rank -> Placeholders
   -> Generate Content -> ReportLab PDF -> SMTP + Duplicate Guard -> Loop]
========================================================================
"""
    print(banner)


def main():
    parser = argparse.ArgumentParser(description="LangGraph Website Automation Audit Pipeline")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of companies to audit in this run")
    parser.add_argument("--no-banner", action="store_true", help="Suppress terminal startup banner")
    args = parser.parse_args()

    if not args.no_banner:
        print_banner()

    # Step 0: Ensure criteria_reference.pdf exists
    if not CRITERIA_PDF_PATH.exists():
        print(f"[*] Initializing criteria reference PDF at: {CRITERIA_PDF_PATH}...")
        generate_criteria_pdf(CRITERIA_PDF_PATH)
        print("[✓] Criteria reference PDF created.")

    print(f"[*] Launching LangGraph pipeline execution at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}...\n")

    initial_state = {
        "companies": [],
        "current_index": 0,
        "current_company": None,
        "scraped_content": {},
        "criteria_reference_text": "",
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
            print(f"  • Company: {c['company_name']}")
            print(f"    URL:     {c['website_url']}")
            print(f"    Status:  {c['status']}")
            print(f"    Report:  {c.get('report_path') or 'N/A'}")
            print(f"    Notes:   {c.get('notes') or 'N/A'}")
            print("  " + "-" * 68)

        print(f"\n[✓] Pipeline execution finished successfully. Total Companies Processed: {len(companies)}\n")

    except KeyboardInterrupt:
        print("\n[!] Execution interrupted by user.")
        sys.exit(1)
    except Exception as exc:
        print(f"\n[✗] Pipeline encountered an unhandled exception: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
