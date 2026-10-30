"""Node 11: Email Report to Company (SMTP + Duplicate Guard)
Dispatches the audit PDF via SMTP while enforcing strict duplicate prevention.
"""
import json
import smtplib
import sys
from pathlib import Path
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from datetime import datetime, timedelta
from typing import Dict, Any, List

# Ensure parent directory is in sys.path to allow standalone execution and imports
_parent_dir = str(Path(__file__).resolve().parent.parent)
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from config import (
    SENT_REGISTRY_PATH, SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS,
    EMAIL_FROM, EMAIL_FROM_NAME, DRY_RUN_EMAIL, DUPLICATE_GUARD_COOLDOWN_DAYS
)
from state import AutomationState


def load_sent_registry() -> List[Dict[str, Any]]:
    """Loads past outreach history for duplicate protection."""
    if not SENT_REGISTRY_PATH.exists():
        return []
    try:
        with open(SENT_REGISTRY_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("records", [])
    except Exception:
        return []


def save_sent_registry(records: List[Dict[str, Any]]) -> None:
    """Saves updated outreach history."""
    SENT_REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(SENT_REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump({"records": records}, f, indent=2)


def is_duplicate_send(email: str, company_name: str, records: List[Dict[str, Any]]) -> bool:
    """Verifies whether company or email has received outreach within cooldown window."""
    if not email and not company_name:
        return False

    cutoff = datetime.now() - timedelta(days=DUPLICATE_GUARD_COOLDOWN_DAYS)
    for rec in records:
        rec_time_str = rec.get("sent_at", "")
        try:
            rec_time = datetime.fromisoformat(rec_time_str)
        except Exception:
            continue

        if rec_time > cutoff:
            same_email = email and rec.get("contact_email", "").strip().lower() == email.strip().lower()
            same_company = company_name and rec.get("company_name", "").strip().lower() == company_name.strip().lower()
            if same_email or same_company:
                return True
    return False


def email_report_node(state: AutomationState) -> Dict[str, Any]:
    """LangGraph node: Sends audit report with duplicate guard check."""
    placeholders = state.get("placeholders", {})
    content = state.get("personalized_content")
    pdf_path_str = state.get("pdf_path")
    logs = list(state.get("logs", []))

    recipient_email = placeholders.get("contact_email", "").strip()
    company_name = placeholders.get("company_name", "Target Company")

    logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] [Node 11] Duplicate Guard: Inspecting outreach history for '{company_name}' ({recipient_email})...")

    records = load_sent_registry()

    # Duplicate Guard Check
    if is_duplicate_send(recipient_email, company_name, records):
        msg = f"Duplicate Guard Triggered: '{company_name}' ({recipient_email}) already received an audit in last {DUPLICATE_GUARD_COOLDOWN_DAYS} days."
        logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] {msg} Skipping email dispatch.")
        return {
            "email_status": {
                "sent": False,
                "reason": "Duplicate Prevented",
                "recipient": recipient_email,
                "timestamp": datetime.now().isoformat()
            },
            "logs": logs
        }

    if isinstance(content, dict):
        subject = content.get("outreach_subject") or f"Website Audit Report: {company_name}"
        body = content.get("outreach_body") or f"Please find attached your digital audit report for {company_name}."
    elif content:
        subject = getattr(content, "outreach_subject", None) or f"Website Audit Report: {company_name}"
        body = getattr(content, "outreach_body", None) or f"Please find attached your digital audit report for {company_name}."
    else:
        subject = f"Website Audit Report: {company_name}"
        body = f"Please find attached your digital audit report for {company_name}."

    # Validate PDF Attachment
    pdf_path = Path(pdf_path_str) if pdf_path_str else None
    if not pdf_path or not pdf_path.exists():
        logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] ERROR: PDF report file missing at: {pdf_path_str}")
        return {
            "email_status": {
                "sent": False,
                "reason": "PDF File Missing",
                "recipient": recipient_email
            },
            "logs": logs
        }

    # Dry-run execution
    if DRY_RUN_EMAIL or not SMTP_USER or not SMTP_PASS:
        reason = "Dry-Run Simulation Active" if DRY_RUN_EMAIL else "SMTP Credentials Not Configured"
        logs.append(
            f"[{datetime.now().strftime('%H:%M:%S')}] [EMAIL DISPATCH - {reason.upper()}]\n"
            f"  To: {recipient_email or '(No recipient email provided)'}\n"
            f"  From: {EMAIL_FROM_NAME} <{EMAIL_FROM}>\n"
            f"  Subject: {subject}\n"
            f"  Attached: {pdf_path.name} ({pdf_path.stat().st_size} bytes)"
        )

        # Record in registry to ensure duplicate protection works in simulation too
        records.append({
            "company_name": company_name,
            "contact_email": recipient_email,
            "sent_at": datetime.now().isoformat(),
            "status": "Simulated (Dry-Run)",
            "pdf_file": pdf_path.name
        })
        save_sent_registry(records)

        return {
            "email_status": {
                "sent": True,
                "dry_run": True,
                "reason": reason,
                "recipient": recipient_email,
                "subject": subject,
                "timestamp": datetime.now().isoformat()
            },
            "logs": logs
        }

    # Real SMTP Dispatch
    try:
        msg = MIMEMultipart()
        msg["From"] = f"{EMAIL_FROM_NAME} <{EMAIL_FROM}>"
        msg["To"] = recipient_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain", "utf-8"))

        with open(pdf_path, "rb") as f:
            pdf_attach = MIMEApplication(f.read(), _subtype="pdf")
            pdf_attach.add_header("Content-Disposition", "attachment", filename=pdf_path.name)
            msg.attach(pdf_attach)

        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(EMAIL_FROM, [recipient_email], msg.as_string())
        server.quit()

        logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] Email sent successfully via SMTP to: {recipient_email}")

        records.append({
            "company_name": company_name,
            "contact_email": recipient_email,
            "sent_at": datetime.now().isoformat(),
            "status": "Sent",
            "pdf_file": pdf_path.name
        })
        save_sent_registry(records)

        return {
            "email_status": {
                "sent": True,
                "dry_run": False,
                "recipient": recipient_email,
                "timestamp": datetime.now().isoformat()
            },
            "logs": logs
        }

    except Exception as exc:
        logs.append(f"[{datetime.now().strftime('%H:%M:%S')}] SMTP Transmission Error: {exc}")
        return {
            "email_status": {
                "sent": False,
                "reason": f"SMTP Error: {exc}",
                "recipient": recipient_email,
                "timestamp": datetime.now().isoformat()
            },
            "logs": logs
        }
