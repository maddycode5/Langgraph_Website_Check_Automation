# LangGraph Website Automation & Audit Intelligence Pipeline

An enterprise-grade, autonomous website auditing pipeline engineered with **LangGraph**, **Google Docs Dynamic Rules Sync**, **PyMuPDF**, **Ollama (`llama3.2:1b`)**, and **ReportLab**. The workflow crawls target company websites across multiple pages, benchmarks them against dynamic evaluation criteria loaded directly from a live Google Doc link, evaluates findings with anti-hallucination verification, synthesizes publication-grade PDF reports, and delivers them via SMTP with duplicate outreach prevention.

---

## Workflow Diagram

```mermaid
flowchart TD
    Start(["Start Workflow"]) --> ReadSheets["Read Google Sheets / CSV"]
    ReadSheets --> GetPending["Get Next Pending Company"]

    MoveNext["Move to Next Company"] --> GetPending

    GetPending --> CheckAvailable{"Company Available?"}
    CheckAvailable -- "No" --> EndWorkflow(["End Workflow"])
    CheckAvailable -- "Yes" --> GetURL["Get Company Website URL"]

    GetURL --> Scraper["AI Scraper: Crawl Website"]
    Scraper --> LoadRules["Load Reference Rules (Dynamic Google Doc / PDF)"]
    LoadRules --> LLMEval["LLM Evaluates Every Reference Point"]
    LLMEval --> LLMValidate["LLM Validates Scores and Evidence"]

    LLMValidate --> CheckValid{"Evaluation Valid?"}
    CheckValid -- "No" --> Retry["Retry Evaluation"]
    Retry --> LLMValidate
    CheckValid -- "Yes" --> RankIssues["Rank Issues Within Company"]

    RankIssues --> GenPDF["Generate PDF of All Verified Issues"]
    GenPDF --> PrepEmail["Prepare Email with PDF Attachment"]
    PrepEmail --> SendEmail["Send Email to Company"]

    SendEmail --> EmailCheck{"Email Sent Successfully?"}
    EmailCheck -- "Yes" --> UpdateSuccess["Update Sheet: Audit and Email Completed"]
    EmailCheck -- "No" --> UpdateFail["Update Sheet: Email Failed"]

    UpdateFail --> LogError["Log Error"]

    UpdateSuccess --> MoveNext
    LogError --> MoveNext

    %% Flowchart Styling Matching UI Palette
    style Start fill:#e0f2fe,stroke:#0284c7,stroke-width:2px,color:#0369a1
    style EndWorkflow fill:#fee2e2,stroke:#ef4444,stroke-width:2px,color:#991b1b
    style CheckAvailable fill:#eff6ff,stroke:#3b82f6,stroke-width:2px,stroke-dasharray: 4 4,color:#1e40af
    style CheckValid fill:#eff6ff,stroke:#3b82f6,stroke-width:2px,stroke-dasharray: 4 4,color:#1e40af
    style EmailCheck fill:#eff6ff,stroke:#3b82f6,stroke-width:2px,stroke-dasharray: 4 4,color:#1e40af
    style ReadSheets fill:#f0f9ff,stroke:#38bdf8,stroke-width:1.5px,color:#0f172a
    style GetPending fill:#f0f9ff,stroke:#38bdf8,stroke-width:1.5px,color:#0f172a
    style GetURL fill:#f0f9ff,stroke:#38bdf8,stroke-width:1.5px,color:#0f172a
    style Scraper fill:#f0f9ff,stroke:#38bdf8,stroke-width:1.5px,color:#0f172a
    style LoadRules fill:#f0f9ff,stroke:#38bdf8,stroke-width:1.5px,color:#0f172a
    style LLMEval fill:#f0f9ff,stroke:#38bdf8,stroke-width:1.5px,color:#0f172a
    style LLMValidate fill:#f0f9ff,stroke:#38bdf8,stroke-width:1.5px,color:#0f172a
    style Retry fill:#fef3c7,stroke:#f59e0b,stroke-width:1.5px,color:#92400e
    style RankIssues fill:#f0f9ff,stroke:#38bdf8,stroke-width:1.5px,color:#0f172a
    style GenPDF fill:#f0f9ff,stroke:#38bdf8,stroke-width:1.5px,color:#0f172a
    style PrepEmail fill:#f0f9ff,stroke:#38bdf8,stroke-width:1.5px,color:#0f172a
    style SendEmail fill:#f0f9ff,stroke:#38bdf8,stroke-width:1.5px,color:#0f172a
    style UpdateSuccess fill:#ecfdf5,stroke:#10b981,stroke-width:1.5px,color:#065f46
    style UpdateFail fill:#fef2f2,stroke:#f87171,stroke-width:1.5px,color:#991b1b
    style LogError fill:#fff1f2,stroke:#fb7185,stroke-width:1.5px,color:#9f1239
    style MoveNext fill:#f0f9ff,stroke:#38bdf8,stroke-width:1.5px,color:#0f172a
```

---

## Key Pipeline Components

| # | Step / Node | Module | Description |
|---|---|---|---|
| 1 | **Read Google Sheets / CSV** | `nodes/read_companies.py` | Reads company leads from Google Sheets (if service account provided) or `data/companies.csv`. |
| 2 | **Select Next Company** | `nodes/select_company.py` | Picks the next company in the execution queue and initializes state variables. |
| 3 | **Scrape Website** | `nodes/scrape_website.py` | Crawls homepage and key subpages (`/about`, `/services`, etc.) using BeautifulSoup and requests; captures latency, headings, metadata, and body text. |
| 4 | **Load Reference Rules** | `nodes/load_reference_rules.py` | Synchronizes benchmark criteria dynamically from a live Google Doc URL. Automatically detects remote document changes via SHA-256 hashing, persists local cache, and supports PDF/rubric fallback. |
| 5 | **Evaluates 20-Pillar Rubric** | `nodes/evaluate_website.py` | Evaluates the website against all 20 reference rubric criteria, guaranteeing a minimum of 10-15 grounded flaws/weak points with zero hallucinations and exact DOM evidence citations. |
| 6 | **Anti-Hallucination Corroborator** | `nodes/validate_evidence.py` | Cross-references LLM evidence quotes against raw scraped website text using exact and token-based fuzzy matching. |
| 7 | **Rank Verified Issues** | `nodes/rank_issues.py` | Sorts issues from weakest (lowest score = highest urgency) to strongest. |
| 8 | **Load Client-Specific Placeholders** | `nodes/load_placeholders.py` | Merges company name, contact, industry, date, scores, and agency branding. |
| 9 | **Generate Personalized Audit Content** | `nodes/generate_content.py` | Composes executive summary, tactical fixes, and outreach email copy. |
| 10 | **Generate PDF** | `nodes/generate_pdf.py` | Compiles publication-grade, styled PDF audit report using **ReportLab** with dynamic page numbering canvas. |
| 11 | **Email Report & Duplicate Guard** | `nodes/email_report.py` | Checks `data/sent_registry.json` cooldown to prevent duplicate outreach; sends email with PDF attachment via SMTP (or runs dry-run simulation). |
| 12 | **Update Status** | `nodes/update_status.py` | Writes updated audit status, report path, and timestamp back to CSV / Google Sheet and increments queue pointer. |
| 13 | **More Companies Remaining?** | `graph.py` | Conditional edge loops back to Node 2 if pending companies remain, or exits to `[END]`. |

---

## Dynamic Google Doc Benchmark Rules

The benchmark evaluation criteria are no longer limited to a static file. You can manage and update your evaluation rubric live in a Google Doc:

1. **Live Synchronisation**: Evaluates against the latest live content from the reference rules Google Doc link:
   - **Active Reference Doc**: [Google Doc Benchmark Rubric](https://docs.google.com/document/d/1m4aU0MB1w2vxqA1PuCVPLLIktNMB7WLoJDT994fSpMQ/edit?usp=sharing) (Configured with view-only permissions).
2. **Continuous Change Detection**: Computes SHA-256 hashes of the doc text on every run and each company cycle. If rules are modified in Google Docs, the pipeline detects the change, logs the update (`v1 -> v2`), and follows the revised rules immediately.
3. **Resilient Offline Caching**: Persists synced rules to `data/criteria_rules_cache.txt` and `data/criteria_rules_meta.json`. If network connectivity is lost, execution continues seamlessly using the cached rules.
4. **Fallback Rubric**: If no Google Doc URL is configured and no cache is present, falls back gracefully to `criteria_reference.pdf` (parsed via PyMuPDF) or built-in benchmark standards.

---

## 20-Pillar Benchmark Rubric & Zero-Hallucination Flaw Detection

Rather than generic 5-pillar overviews, the pipeline now assesses each target website against **all 20 criteria** from the official benchmark document, guaranteeing a minimum of **10 to 14 verified flaws or weak points** (scores 1–6) in every generated audit report:

| Pillar # | Evaluation Pillar | Checked Criteria & Grounded Citations |
|---|---|---|
| **1** | **Industry Fit & Brand Positioning** | Clinic messaging vs generic copy; verified against scanned brand terms. |
| **2** | **Above-the-Fold First Impression** | Single authoritative H1 hero vs zero or multiple conflicting H1 tags. |
| **3** | **Treatment Depth & Recovery Guidance** | Downtime duration, session count, recovery routines, and contraindications. |
| **4** | **Dedicated Service Landing Pages** | Dedicated URLs per treatment vs bundling all procedures into one URL. |
| **5** | **Patient Intent & Comparison Content** | Procedure comparison guides (e.g. PRP vs GFC) and candidacy self-tests. |
| **6** | **Doctor Credentials & Council Proof** | Official State/National Medical Council registration numbers (MCI/NMC). |
| **7** | **Clinical Case Studies & Visual Proof** | Verifiable clinical before-and-after photo comparisons and transformation timelines. |
| **8** | **Procedure FAQs & Consultation Guidance** | FAQ modules addressing fees, session counts, pain levels, and consultation steps. |
| **9** | **Call-to-Action Visibility & Placement** | High-contrast appointment CTAs above the fold and persistent sticky mobile booking bar. |
| **10** | **Appointment Scheduling Friction** | Real-time interactive slot scheduling vs friction-heavy static forms. |
| **11** | **Operating Hours & Schedule Transparency** | Weekly clinic timings, Sunday hours, and walk-in consultation transparency. |
| **12** | **Direct Contact & Click-to-Call** | Direct `tel:` anchor links allowing one-tap calling on mobile devices. |
| **13** | **Instant Messaging & WhatsApp Channel** | Direct `wa.me`/WhatsApp consultation links for instant patient triage. |
| **14** | **Social Media Integration & Cross-Linking**| Active links to official Instagram, YouTube, and Facebook profiles. |
| **15** | **Content Hierarchy & Semantic Headings** | Clean semantic hierarchy from H1 to H3 without skipped levels. |
| **16** | **SEO Title Tag Calibration** | Optimal SERP pixel width (35–60 characters) and high-intent keyword inclusion. |
| **17** | **SERP Meta Description Quality** | Compelling 145–160 character snippet with clinical UVP and phone/CTA prompt. |
| **18** | **Technical SEO & Schema.org Markup** | `MedicalBusiness` / `Physician` JSON-LD structured data scripts in HTML head. |
| **19** | **Server Speed & Latency Performance** | Measured Time-To-First-Byte (TTFB) and HTTP response latency in milliseconds. |
| **20** | **Medical Disclaimer & Regulatory Notice**| Mandatory healthcare disclaimers ("Results may vary") and privacy policies. |

### Zero-Hallucination Corroboration Engine
- **No Invented Claims**: Every identified deficiency is backed by direct DOM evidence (e.g. `"Zero tel: click-to-call links found"`, `"Average latency measured at 916.3ms"`, `"Zero H1 tags detected on homepage"`, `"JSON-LD structured data script missing from HTML"`).
- **Multi-Page ReportLab Table**: The PDF report engine repeats table headers across pages (`repeatRows=1`) and formats all 20 pillars with color-coded score badges (`[Critical]`, `[Moderate]`, `[Strong]`) and verified quotes across publication-grade pages.

---

## Google Sheets Integration & URL-Only Mode

The pipeline natively connects with **Google Sheets** for real-time lead ingestion and status synchronization:

1. **Dual Queue Sources**: Attempts to read target companies from Google Sheets (`Website_Audit_Leads`) via a Google Service Account. If unconfigured or offline, seamlessly falls back to `data/companies.csv`.
2. **URL-Only Auto-Inference**: When input data only contains website URLs (e.g. `website_url` column), the pipeline automatically extracts and cleans the brand/company name from the domain (e.g., `https://thedermabright.com/` → `Thedermabright`), filling in defaults for contacts and industry without requiring manual data prep.
3. **Two-Way Synchronization**: As each audit finishes (Node 12), the pipeline writes the audit status, output PDF file path, score summary, and timestamp directly back into the Google Sheet in real time.

### Sheet Schema & Column Layout

| Column | Required | Description | Example |
|---|---|---|---|
| `id` | Optional | Unique identifier or row index | `1` |
| `company_name` | Optional | Auto-derived from URL domain if blank | `Dermatokare` |
| `website_url` | **Required** | The target website to crawl and audit | `https://drafrozskinhairclinic.com/` |
| `contact_name` | Optional | Decision maker name for personalization | `Dr. Garima Mehrotra` |
| `contact_email` | Optional | Recipient email for report dispatch | `info@clinic.example` |
| `industry` | Optional | Business vertical (defaults to `Technology` or vertical category) | `Dermatology & Skincare` |
| `status` | **Required** | Queue flag (`Pending` to process) | `Pending` -> `Completed` |
| `report_path` | System | Auto-populated path to generated PDF report | `reports/Report_*.pdf` |
| `notes` | System | Audit score summary and delivery logs | `Score: 7.4/10 \| Dry-Run Simulation Active` |
| `updated_at` | System | Timestamp of last audit update | `2026-11-05 01:29:30` |

### Batch Importing URLs (`scripts/populate_sheet.py`)

A helper script is included to quickly deduplicate and load a raw list of website URLs into your connected Google Sheet:

```bash
python scripts/populate_sheet.py
```

This cleans query parameters, deduplicates base domains, derives readable names, and writes formatted rows with `status = Pending`.

---

## Directory Structure

```
Langgraph_Website_Automation/
├── .env.example                       # Environment variables template
├── .gitignore                         # Git ignore patterns
├── config.py                          # Central configuration & paths
├── criteria_reference.pdf             # Standardized 5-pillar benchmark rubric PDF
├── graph.py                           # LangGraph StateGraph pipeline assembly
├── main.py                            # Main CLI execution entry point
├── requirements.txt                   # Python dependencies
├── setup_criteria_pdf.py              # Fallback PDF rubric generator
├── state.py                           # TypedDict state schema definitions
├── credentials/                       # Service account JSON keys (gitignored)
│   └── service_account.json
├── data/
│   ├── companies.csv                  # Target leads database (CSV fallback)
│   ├── criteria_reference_template.txt# Starter rubric text for Google Docs
│   └── sent_registry.json             # Duplicate guard outreach registry
├── nodes/
│   ├── __init__.py
│   ├── read_companies.py              # Node 1: CSV / Google Sheets loader
│   ├── select_company.py              # Node 2: Queue controller
│   ├── scrape_website.py              # Node 3: Multi-page web scraper
│   ├── load_reference_rules.py        # Node 4: Dynamic Google Doc synchronizer & change detector
│   ├── load_reference_pdf.py          # Node 4 backwards-compatibility proxy
│   ├── evaluate_website.py            # Node 5: Ollama llama3.2:1b evaluator
│   ├── validate_evidence.py           # Node 6: Anti-Hallucination Corroborator
│   ├── rank_issues.py                 # Node 7: Weakest -> Strongest ranker
│   ├── load_placeholders.py           # Node 8: Client placeholders injector
│   ├── generate_content.py            # Node 9: Executive narrative synthesizer
│   ├── generate_pdf.py                # Node 10: Publication-grade ReportLab PDF engine
│   ├── email_report.py                # Node 11: SMTP sender + Duplicate Guard
│   └── update_status.py               # Node 12: CSV / Sheet persistence updater
├── scripts/
│   └── populate_sheet.py              # Batch URL importer & deduplicator for Google Sheets
├── tests/
│   └── test_google_doc_rules.py       # Unit tests for URL parsing, change detection, and caching
└── reports/                           # Generated PDF audit reports
```

---

## Quick Start Guide

### 1. Install Dependencies
```bash
cd Langgraph_Website_Automation
pip install -r requirements.txt
```

### 2. Configure Environment & Rules
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

The pipeline is pre-configured with the reference rules doc link:
```env
GOOGLE_DOC_RULES_URL=https://docs.google.com/document/d/1m4aU0MB1w2vxqA1PuCVPLLIktNMB7WLoJDT994fSpMQ/edit?usp=sharing
```
*(Configured with view-only permissions for dynamic reference rule loading).*

#### Optional: Google Sheets Connection
To read and write company leads to a Google Sheet instead of CSV:
1. Place your Google Service Account key at `credentials/service_account.json`.
2. Share your Google Sheet (e.g. `Website_Audit_Leads`) with the service account email as **Editor**.
3. Configure your `.env`:
   ```env
   GOOGLE_SERVICE_ACCOUNT_JSON=credentials/service_account.json
   GOOGLE_SHEET_NAME=Website_Audit_Leads
   ```

You can also override the rules doc URL directly via CLI:
```bash
python main.py --doc-url "https://docs.google.com/document/d/1m4aU0MB1w2vxqA1PuCVPLLIktNMB7WLoJDT994fSpMQ/edit?usp=sharing"
```

### 3. Ollama Setup (Local LLM)
Make sure Ollama is installed and running with `llama3.2:1b`:
```bash
ollama run llama3.2:1b
```
*(If Ollama is offline, the pipeline automatically falls back to its built-in heuristic scoring engine without crashing).*

### 4. Run the Pipeline
```bash
python main.py
```

### 5. Inspect Results
- Check the generated PDF reports in the `reports/` folder.
- Inspect updated statuses and paths in your Google Sheet (or `data/companies.csv`).
- Inspect outreach logs in `data/sent_registry.json`.

---

## Troubleshooting & Best Practices

| Issue / Symptom | Root Cause | Solution |
|---|---|---|
| `ModuleNotFoundError: No module named 'dotenv'` | Python virtual environment has not had `requirements.txt` installed | Run `python -m pip install -r requirements.txt` or execute using system Python (`python main.py`). |
| `SpreadsheetNotFound` on Google Sheets connect | The spreadsheet file title in Google Drive does not match `GOOGLE_SHEET_NAME` | Ensure the Google Sheet title matches `GOOGLE_SHEET_NAME` in `.env` exactly (default: `Website_Audit_Leads`). |
| `APIError: 403 Forbidden` on Google Sheets connect | The service account email has not been granted access to the sheet | Open Google Sheet -> Click **Share** -> Add the `client_email` from `service_account.json` with **Editor** permissions. |
| `iam.disableServiceAccountKeyCreation` error in Google Cloud | Google Cloud Organization has an organization policy blocking service account keys | Create the Google Cloud project with **Location: "No organization"** under your personal account. |
| Pipeline falls back to built-in heuristic evaluator | Ollama service is not running on port 11434 | Run `ollama serve` and `ollama run llama3.2:1b`. Execution continues seamlessly even if Ollama is offline. |

