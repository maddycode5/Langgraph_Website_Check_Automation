# Configuration for LangGraph Website Automation Pipeline
import os
from pathlib import Path
from dotenv import load_dotenv

# Base Directory
BASE_DIR = Path(__file__).resolve().parent

# Load .env if present
load_dotenv(BASE_DIR / ".env")

# Ollama LLM Configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:1b")
OLLAMA_TIMEOUT_SECONDS = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "120"))

# File & Directory Paths
DATA_DIR = BASE_DIR / "data"
REPORTS_DIR = BASE_DIR / "reports"
CRITERIA_PDF_PATH = BASE_DIR / "criteria_reference.pdf"
CRITERIA_RULES_CACHE_PATH = DATA_DIR / "criteria_rules_cache.txt"
CRITERIA_RULES_META_PATH = DATA_DIR / "criteria_rules_meta.json"
CRITERIA_TEMPLATE_PATH = DATA_DIR / "criteria_reference_template.txt"
COMPANIES_CSV_PATH = DATA_DIR / "companies.csv"
SENT_REGISTRY_PATH = DATA_DIR / "sent_registry.json"

# Google Doc Rules Configuration (Dynamic Live Benchmark Rules)
GOOGLE_DOC_RULES_URL = os.getenv(
    "GOOGLE_DOC_RULES_URL",
    os.getenv("CRITERIA_DOC_URL", "https://docs.google.com/document/d/1m4aU0MB1w2vxqA1PuCVPLLIktNMB7WLoJDT994fSpMQ/edit?usp=sharing")
).strip()

# Google Sheets Configuration (Optional)
GOOGLE_SERVICE_ACCOUNT_JSON = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON", "")
GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME", "Website_Audit_Leads")

# Web Scraping Configuration
MAX_PAGES_PER_SITE = int(os.getenv("MAX_PAGES_PER_SITE", "3"))
REQUEST_TIMEOUT_SECONDS = int(os.getenv("REQUEST_TIMEOUT_SECONDS", "15"))
USER_AGENT = os.getenv(
    "SCRAPER_USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 (WebsiteAuditBot/1.0)"
)

# Anti-Hallucination Corroborator Settings
EVIDENCE_SIMILARITY_THRESHOLD = float(os.getenv("EVIDENCE_SIMILARITY_THRESHOLD", "0.60"))
MIN_QUOTE_LENGTH_WORDS = 3

# Email & Duplicate Guard Configuration
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
EMAIL_FROM = os.getenv("EMAIL_FROM", "audit@agency.example.com")
EMAIL_FROM_NAME = os.getenv("EMAIL_FROM_NAME", "Digital Performance Audit Team")
DRY_RUN_EMAIL = os.getenv("DRY_RUN_EMAIL", "true").lower() in ("true", "1", "yes")
DUPLICATE_GUARD_COOLDOWN_DAYS = int(os.getenv("DUPLICATE_GUARD_COOLDOWN_DAYS", "30"))

# Audit Agency Branding
AGENCY_NAME = os.getenv("AGENCY_NAME", "Apex Digital Insights")
AUDITOR_NAME = os.getenv("AUDITOR_NAME", "Automated Lead Auditor")
AUDITOR_CONTACT = os.getenv("AUDITOR_CONTACT", "support@apexdigital.example.com")

# Ensure required directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
REPORTS_DIR.mkdir(parents=True, exist_ok=True)
