"""
config.py
=========
All constants and config for the project. Every other module imports from this file.

Secrets (GEMINI_API_KEY, EMAIL_PASSWORD) come from Vault at runtime.
Bootstrap vars (VAULT_*, EMAIL_TO, EMAIL_FROM) come from .env.
"""

import os
import logging
from pathlib import Path
from dotenv import load_dotenv  # type: ignore

load_dotenv()

# ---------------------------------------------------------------------------
# SECRETS — pulled from Vault at startup
# ---------------------------------------------------------------------------

def _load_vault_secrets() -> dict:
    try:
        from vault_client import get_secrets
        return get_secrets()
    except Exception as e:
        log.warning(f"Vault unavailable, falling back to env vars: {e}")
        return {}

# Bootstrap logging early so Vault errors are visible
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  [%(name)s]  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

_secrets = _load_vault_secrets()

GEMINI_API_KEY: str = _secrets.get("gemini_api_key", os.getenv("GEMINI_API_KEY", ""))
EMAIL_PASSWORD: str = _secrets.get("gmail_app_pw",   os.getenv("EMAIL_PASSWORD", ""))

# ---------------------------------------------------------------------------
# EMAIL — non-secret config stays in .env
# ---------------------------------------------------------------------------

EMAIL_TO:   str = os.getenv("EMAIL_TO",   "you@example.com")
EMAIL_FROM: str = os.getenv("EMAIL_FROM", "sender@example.com")
SMTP_HOST:  str = os.getenv("SMTP_HOST",  "smtp.gmail.com")
SMTP_PORT:  int = int(os.getenv("SMTP_PORT", "587"))

# ---------------------------------------------------------------------------
# STATE FILE
# ---------------------------------------------------------------------------

STATE_FILE: Path = Path(os.getenv("STATE_FILE", "seen_jobs.json"))
GEMINI_BATCH_SIZE: int = 50

# ---------------------------------------------------------------------------
# SALARY THRESHOLDS
# Tweak these as your expectations change.
# ---------------------------------------------------------------------------

SALARY_STRONG_MIN:  int = 140_000   # low end must be >= this for "Strong"
SALARY_REVIEW_AVG:  int = 125_000   # avg must be >= this for "Review"
# Anything below SALARY_REVIEW_AVG average = "Low" — filtered out of email

# ---------------------------------------------------------------------------
# TITLE KEYWORDS
# Job title must contain at least one of these (whole phrase, case-insensitive).
# ---------------------------------------------------------------------------

TITLE_KEYWORDS: list[str] = [

    # Endpoint / Device Management
    "endpoint engineer",
    "endpoint manager",
    "endpoint architect",
    "endpoint platform",
    "endpoint automation",
    "endpoint management",
    "device engineer",
    "device management",
    "device platform",
    "unified endpoint",
    "uem",
    "mobile device management",
    "mdm engineer",
    "mdm administrator",

    # Modern Workplace / M365
    "modern workplace",
    "workplace engineer",
    "workplace architect",
    "digital workplace",
    "m365 engineer",
    "m365 administrator",
    "microsoft 365 engineer",
    "microsoft 365 architect",
    "office 365 engineer",
    "o365 engineer",
    "collaboration engineer",

    # MDM titles
    "intune engineer",
    "intune administrator",
    "intune architect",
    "sccm engineer",
    "sccm administrator",
    "configmgr",
    "configuration manager engineer",
    "jamf engineer",
    "jamf administrator",

    # Cloud / Azure Infrastructure
    "azure engineer",
    "azure architect",
    "azure administrator",
    "azure infrastructure",
    "cloud engineer",
    "cloud architect",
    "cloud infrastructure",
    "infrastructure engineer",
    "infrastructure architect",
    "platform engineer",
    "platform architect",

    # Identity & Access Management
    "identity engineer",
    "identity architect",
    "identity and access",
    "iam engineer",
    "iam architect",
    "entra",
    "azure ad engineer",
    "azure active directory",
    "okta engineer",
    "okta administrator",

    # Zero Trust / Security Posture
    "zero trust",
    "conditional access",
    "endpoint security engineer",
    "defender engineer",

    # Systems & Automation
    "systems engineer",
    "system engineer",
    "systems administrator",
    "system administrator",
    "automation engineer",
    "infrastructure automation",
    "devops",
    "devsecops",
    "site reliability",
    "sre",

    # VDI / Virtual Desktop
    "virtual desktop",
    "avd",
    "azure virtual desktop",
    "citrix engineer",
    "vdi engineer",

    # IT Management
    "it manager",
    "infrastructure manager",
    "platform manager",
    "endpoint manager",
    "workplace manager",

    # Broad safety nets
    "it operations",
    "information technology",
    "observability engineer",
    "monitoring engineer",

    # DevOps / Platform (you're already here, cast wider)
    "platform operations",
    "cloud operations",
    "infrastructure operations",

    # Your Orchestrator/SCCM background maps to these
    "configuration management engineer",
    "release engineer",
    "build and release",

    # DevSecOps
    "devsecops engineer",
    "security automation",
    "security engineer", 
]

# ---------------------------------------------------------------------------
# DESCRIPTION KEYWORDS
# Used by sources that provide full description text (Greenhouse, Workday).
# ---------------------------------------------------------------------------

DESCRIPTION_KEYWORDS: list[str] = [
    "intune",
    "microsoft intune",
    "endpoint manager",
    "sccm",
    "configuration manager",
    "jamf",
    "autopilot",
    "windows autopilot",
    "co-management",
    "comanagement",
    "hybrid azure ad join",
    "hybrid join",
    "entra id",
    "azure ad",
    "azure active directory",
    "mdm",
    "mobile device management",
    "unified endpoint management",
    "uem",
    "device compliance",
    "device lifecycle",
    "device enrollment",
    "device configuration",
    "compliance policy",
    "conditional access",
    "app protection policy",
    "windows update for business",
    "wufb",
    "wsus",
    "patch management",
    "update rings",
    "software update",
    "azure automation",
    "azure runbook",
    "azure policy",
    "azure monitor",
    "microsoft defender",
    "defender for endpoint",
    "defender for identity",
    "microsoft sentinel",
    "powershell",
    "system center orchestrator",
    "orchestrator",
    "servicenow",
    "azure logic apps",
    "desired state configuration",
    "dsc",
    "cis benchmark",
    "security baseline",
    "privileged identity management",
    "pim",
    "zero trust",
    "okta",
    "microsoft 365",
    "m365",
    "office 365",
    "sharepoint",
    "teams administration",
    "exchange online",
    "windows 11",
    "windows 10",
    "macos management",
    "ios management",
    "android management",
    "ios enterprise",
    "android enterprise",
    "terraform",
    "ansible",
    "kubernetes",
    "docker",
    "ci/cd",
    "github actions",
    "jenkins",
    "infrastructure as code",
    "iac",
    "hashicorp",
    "vault",
    "artifactory",
    "jfrog",
]

# ---------------------------------------------------------------------------
# TITLE EXCLUDE
# ---------------------------------------------------------------------------

TITLE_EXCLUDE: list[str] = [
    "marketing",
    "recruiter",
    "recruiting",
    "talent acquisition",
    "help desk",
    "desktop support",
    "it support",
    "technician",
    "tier 1",
    "tier 2",
    "intern",
    "entry level",
    "junior",
    "analyst",
    "vice president",
    "director",
    "account executive",
    "sales manager",
    "Corporate Counsel",
]

# ---------------------------------------------------------------------------
# SEARCH KEYWORDS — typed into each site's search box
# Keep tight — fewer = faster runs. Filtering happens after results come back.
# ---------------------------------------------------------------------------

SEARCH_KEYWORDS: list[str] = [
    "intune",
    "endpoint",
    "modern workplace",
    "azure",
    "platform engineer",
    "infrastructure engineer",
    "systems administrator",
    "identity",
    "it manager",
    "devops",
    "site reliability",
    "cloud engineer",
    "cloud architect",
    "devsecops",
    "platform operations",
    "cloud operations",
]

# ---------------------------------------------------------------------------
# GREENHOUSE COMPANIES
# Find a token: go to a company's careers page → click any job →
# look for "greenhouse.io/TOKEN" in the URL.
# Verify: https://boards-api.greenhouse.io/v1/boards/TOKEN/jobs
# ---------------------------------------------------------------------------

GREENHOUSE_COMPANIES: list[dict] = [
    {"label": "Trace3",     "token": "trace3"},
    {"label": "Okta",       "token": "okta"},
    {"label": "Datadog",    "token": "datadog"},
    {"label": "PagerDuty",  "token": "pagerduty"},
    {"label": "Stripe",     "token": "stripe"},
    {"label": "Cloudflare", "token": "cloudflare"},
    {"label": "Figma",      "token": "figma"},
    # {"label": "Company Name", "token": "companytoken"},
]

# ---------------------------------------------------------------------------
# WORKDAY COMPANIES
# URL pattern: https://{tenant}.wd{N}.myworkdayjobs.com/en-US/{board}/jobs
# Find a URL: go to a company's careers page → click any job →
# look for "myworkdayjobs.com" in the URL.
# ---------------------------------------------------------------------------

WORKDAY_COMPANIES: list[dict] = [
    {
        "label":  "AT&T",
        "url":    "https://att.wd1.myworkdayjobs.com/en-US/ATTGeneral/jobs",
        "domain": "https://att.wd1.myworkdayjobs.com",
    },
    {
        "label":  "T-Mobile",
        "url":    "https://tmobile.wd1.myworkdayjobs.com/en-US/External/jobs",
        "domain": "https://tmobile.wd1.myworkdayjobs.com",
    },
    {
        "label":  "Comcast / Xfinity",
        "url":    "https://comcast.wd5.myworkdayjobs.com/en-US/Comcast_Careers/jobs",
        "domain": "https://comcast.wd5.myworkdayjobs.com",
    },
    {
        "label":  "Capital One",
        "url":    "https://capitalone.wd12.myworkdayjobs.com/en-US/Capital_One/jobs",
        "domain": "https://capitalone.wd12.myworkdayjobs.com",
    },
    {
        "label":  "Nationwide Insurance",
        "url":    "https://nationwide.wd1.myworkdayjobs.com/en-US/Nationwide_Career/jobs",
        "domain": "https://nationwide.wd1.myworkdayjobs.com",
    },
    {
        "label":  "American Family Insurance",
        "url":    "https://amfam.wd1.myworkdayjobs.com/en-US/Careers/jobs",
        "domain": "https://amfam.wd1.myworkdayjobs.com",
    },
    {
        "label":  "Verizon",
        "url":    "https://verizon.wd12.myworkdayjobs.com/en-US/verizon-careers/jobs",
        "domain": "https://verizon.wd12.myworkdayjobs.com",
    },
    {
        "label":  "Nvidia",
        "url":    "https://nvidia.wd5.myworkdayjobs.com/en-US/NVIDIAExternalCareerSite/jobs",
        "domain": "https://nvidia.wd5.myworkdayjobs.com",
    },
    {
        "label":  "Salesforce",
        "url":    "https://salesforce.wd12.myworkdayjobs.com/en-US/External_Career_Site/jobs",
        "domain": "https://salesforce.wd12.myworkdayjobs.com",
    },
    {
        "label":  "Workday",
        "url":    "https://workday.wd5.myworkdayjobs.com/en-US/Workday/jobs",
        "domain": "https://workday.wd5.myworkdayjobs.com",
    },
    {
        "label":  "Palo Alto Networks",
        "url":    "https://paloaltonetworks.wd1.myworkdayjobs.com/en-US/External/jobs",
        "domain": "https://paloaltonetworks.wd1.myworkdayjobs.com",
    },
    {
        "label":  "ServiceNow",
        "url":    "https://servicenow.wd1.myworkdayjobs.com/en-US/Careers/jobs",
        "domain": "https://servicenow.wd1.myworkdayjobs.com",
    },
    {
        "label":  "Intuit",
        "url":    "https://intuit.wd1.myworkdayjobs.com/en-US/Intuit_Careers/jobs",
        "domain": "https://intuit.wd1.myworkdayjobs.com",
    },
    {
        "label":  "CrowdStrike",
        "url":    "https://crowdstrike.wd5.myworkdayjobs.com/en-US/crowdstrikecareers/jobs",
        "domain": "https://crowdstrike.wd5.myworkdayjobs.com",
    },
    # {
    #     "label":  "Company Name",
    #     "url":    "https://TENANT.wd1.myworkdayjobs.com/en-US/BOARD/jobs",
    #     "domain": "https://TENANT.wd1.myworkdayjobs.com",
    # },
]

# ---------------------------------------------------------------------------
# COMPANY SPECIFIC VARIABLES
# Specific sites, constraints, and misc things for highly-desirable employers
# 
# ---------------------------------------------------------------------------

NETFLIX_CAREERS_URL: str = "https://explore.jobs.netflix.net/careers"
NETFLIX_DOMAIN:      str = "netflix.com"
NETFLIX_API_URL:     str = "https://explore.jobs.netflix.net/api/apply/v2/jobs"
NETFLIX_PAGE_SIZE:   int = 10
NETFLIX_MAX_PAGES:   int = 80