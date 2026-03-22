"""
config.py
=========
Central home for every constant and environment variable in the project.
Every other module imports from here — nothing else reads os.getenv() directly.

PROFILE THIS IS TUNED FOR:
  Senior enterprise endpoint/infrastructure engineer — Microsoft ecosystem specialist.

  Core platforms:   Microsoft Intune (deep — all platforms: Windows, macOS, iOS,
                    Android), SCCM / Configuration Manager, co-management,
                    Jamf (migrating to Intune), Azure AD / Entra ID, Azure
  Automation:       PowerShell (strong), Azure Automation / Runbooks,
                    System Center Orchestrator, ServiceNow (in progress),
                    Python (learning), Bash
  Security:         Microsoft Defender for Endpoint, security baselines,
                    CIS benchmarks, Okta IDP, QRadar (IBM SIEM)
  Operations:       Device lifecycle, patching / WUfB / WSUS, software
                    packaging, OS imaging / task sequences, Autopilot,
                    hybrid join, compliance / conditional access
  Seniority:        IC, architect, player-coach, manager — comp dependent
  Style:            Build AND run — enterprise scale, cross-tool integration

HOW MATCHING WORKS:
  Two-stage filter on every job:
    1. TITLE_KEYWORDS   — job title must contain at least one of these
    2. DESCRIPTION_KEYWORDS — used by sources that fetch description text
       (Greenhouse, Workday) to surface jobs with generic titles like
       "Staff Engineer" or "Senior Engineer" that mention Intune/SCCM/etc.
       A job passes if it matches EITHER title OR description keywords.
  TITLE_EXCLUDE       — any job whose title contains one of these is dropped
                        regardless of keyword matches.
"""

import os
import logging
from pathlib import Path

# ---------------------------------------------------------------------------
# API KEYS
# ---------------------------------------------------------------------------

GEMINI_API_KEY:    str = os.getenv("GEMINI_API_KEY",    "")  # salary estimation
ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")  # optional fallback

# ---------------------------------------------------------------------------
# EMAIL
# Gmail: generate an App Password at myaccount.google.com → Security → App Passwords
# ---------------------------------------------------------------------------

EMAIL_TO:       str = os.getenv("EMAIL_TO",       "you@example.com")
EMAIL_FROM:     str = os.getenv("EMAIL_FROM",     "sender@example.com")
EMAIL_PASSWORD: str = os.getenv("EMAIL_PASSWORD", "")
SMTP_HOST:      str = os.getenv("SMTP_HOST",      "smtp.gmail.com")
SMTP_PORT:      int = int(os.getenv("SMTP_PORT",  "587"))

# ---------------------------------------------------------------------------
# STATE FILE
# Persists seen job IDs and salary cache between runs.
# Created automatically on first run.
# ---------------------------------------------------------------------------

STATE_FILE: Path = Path(os.getenv("STATE_FILE", "seen_jobs.json"))

# ---------------------------------------------------------------------------
# TITLE_KEYWORDS
# A job's title must contain at least one of these to be included.
# Matching is case-insensitive throughout.
#
# ORGANIZED BY AREA — add/remove freely:
# ---------------------------------------------------------------------------

TITLE_KEYWORDS: list[str] = [

    # ── Endpoint / Device Management ─────────────────────────────────────────
    # The core of your profile. These titles map directly to your work.
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

    # ── Modern Workplace / M365 ───────────────────────────────────────────────
    # "Modern workplace" is the current industry term for the space you work in
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

    # ── Intune / SCCM specific titles ────────────────────────────────────────
    # Some companies use the product name in the title
    "intune engineer",
    "intune administrator",
    "intune architect",
    "sccm engineer",
    "sccm administrator",
    "configmgr",
    "configuration manager engineer",
    "jamf engineer",
    "jamf administrator",

    # ── Cloud / Azure Infrastructure ─────────────────────────────────────────
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

    # ── Identity & Access Management ─────────────────────────────────────────
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

    # ── Zero Trust / Security Posture ─────────────────────────────────────────
    # These roles are typically implemented via the tools you already know
    "zero trust",
    "conditional access",
    "endpoint security engineer",
    "defender engineer",

    # ── Systems & Automation ──────────────────────────────────────────────────
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

    # ── VDI / Virtual Desktop ─────────────────────────────────────────────────
    "virtual desktop",
    "avd",
    "azure virtual desktop",
    "citrix engineer",
    "vdi engineer",

    # ── IT Management ─────────────────────────────────────────────────────────
    # IT Manager yes, Director/VP no (filtered by salary band in practice)
    "it manager",
    "infrastructure manager",
    "platform manager",
    "endpoint manager",
    "workplace manager",

    # ── Broad safety nets ─────────────────────────────────────────────────────
    "it operations",
    "information technology",
]

# ---------------------------------------------------------------------------
# DESCRIPTION_KEYWORDS
# Used by sources that provide full job description text (Greenhouse, Workday).
# A job passes if its title matches TITLE_KEYWORDS OR its description contains
# any of these — catches generic titles like "Staff Engineer" or "Sr. Engineer"
# that are really endpoint/infra roles in disguise.
#
# These are the specific technologies and concepts from your profile.
# More precise than title keywords — "intune" in a description is a strong
# signal this is your kind of role even if the title doesn't say so.
# ---------------------------------------------------------------------------

DESCRIPTION_KEYWORDS: list[str] = [

    # ── Your core tools — strongest signals ──────────────────────────────────
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

    # ── Device / MDM ecosystem ────────────────────────────────────────────────
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

    # ── Patching / update management ─────────────────────────────────────────
    "windows update for business",
    "wufb",
    "wsus",
    "patch management",
    "update rings",
    "software update",

    # ── Azure / cloud infrastructure ─────────────────────────────────────────
    "azure automation",
    "azure runbook",
    "azure policy",
    "azure monitor",
    "microsoft defender",
    "defender for endpoint",
    "defender for identity",
    "microsoft sentinel",

    # ── Automation / scripting ────────────────────────────────────────────────
    "powershell",
    "system center orchestrator",
    "orchestrator",
    "servicenow",
    "azure logic apps",
    "desired state configuration",
    "dsc",

    # ── Security / compliance ─────────────────────────────────────────────────
    "cis benchmark",
    "security baseline",
    "privileged identity management",
    "pim",
    "zero trust",
    "okta",
    "qradar",

    # ── M365 ecosystem ────────────────────────────────────────────────────────
    "microsoft 365",
    "m365",
    "office 365",
    "sharepoint",
    "teams administration",
    "exchange online",

    # ── Device platforms you manage ───────────────────────────────────────────
    "windows 11",
    "windows 10",
    "macos management",
    "ios management",
    "android management",
    "ios enterprise",
    "android enterprise",
]

# ---------------------------------------------------------------------------
# TITLE_EXCLUDE
# Any job whose title contains one of these is dropped immediately,
# regardless of keyword matches. Case-insensitive.
# ---------------------------------------------------------------------------

TITLE_EXCLUDE: list[str] = [
    "sales",
    "account executive",
    "account manager",
    "business development",
    "marketing",
    "recruiter",
    "recruiting",
    "talent acquisition",
    "customer success",           # usually sales-adjacent
    "solutions consultant",       # usually pre-sales
    "pre-sales",
    "presales",
]

# ---------------------------------------------------------------------------
# SEARCH_KEYWORDS — used by ALL job site modules as their search query
#
# These are what gets typed into each site's search box. Broad enough to
# surface relevant roles, specific enough to avoid drowning in noise.
# TITLE_KEYWORDS / DESCRIPTION_KEYWORDS do the precise filtering after
# results come back.
#
# Used by: scraper.py, workday.py, microsoft.py, and any future site module.
# Fewer terms = fewer page loads = faster runs. Keep this list tight.
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
]

TEAMWORK_BASE_URL: str = "https://www.teamworkonline.com/jobs-in-sports"

# ---------------------------------------------------------------------------
# GREENHOUSE COMPANIES — used by greenhouse.py
# Free public JSON API. Tokens verified 2026-03-13 via find_tokens.py.
# A 404 logs a warning and returns [] — will NOT crash the run.
#
# HOW TO FIND A TOKEN:
#   Go to careers page → click any job → look for "greenhouse.io/TOKEN" in URL
#   Verify: https://boards-api.greenhouse.io/v1/boards/TOKEN/jobs
# ---------------------------------------------------------------------------

GREENHOUSE_COMPANIES: list[dict] = [

    # Stadium / naming rights
    {"label": "AB InBev (Busch)",    "token": "abinbev"},
    {"label": "SoFi",                "token": "sofi"},

    # MSPs / IT providers — all relevant to your profile
    # Trace3:    cloud + infra consulting, heavy Microsoft stack
    # Okta:      your IDP experience directly applies
    # Datadog:   observability — adjacent to your monitoring work
    # PagerDuty: incident management, IT ops adjacent
    {"label": "Trace3",              "token": "trace3"},
    {"label": "Okta",                "token": "okta"},
    {"label": "Datadog",             "token": "datadog"},
    {"label": "PagerDuty",           "token": "pagerduty"},

    # Sports teams confirmed on Greenhouse
    {"label": "Baltimore Orioles",   "token": "baltimoreorioles"},
    {"label": "Oakland Athletics",   "token": "athletics"},
    {"label": "LA Clippers",         "token": "laclippers"},
    {"label": "Orlando Magic",       "token": "magic"},
    {"label": "Detroit Lions",       "token": "detroitlions"},
    {"label": "Philadelphia Eagles", "token": "philadelphiaeagles"},

    # --- Add more tokens below ---
    # Verify: https://boards-api.greenhouse.io/v1/boards/TOKEN/jobs
    # Template: {"label": "Company Name", "token": "companytoken"},
]

# ---------------------------------------------------------------------------
# WORKDAY COMPANIES — used by workday.py
# Playwright fetches each page since Workday is JavaScript-rendered.
# URL pattern: https://{tenant}.wd{N}.myworkdayjobs.com/en-US/{board}/jobs
#
# HOW TO FIND A WORKDAY URL:
#   Go to careers page → click a job → look for "myworkdayjobs.com" in the URL
#
# NOT ON WORKDAY (need custom scrapers — future todo):
#   Microsoft → jobs.careers.microsoft.com
#   Apple     → jobs.apple.com
#   Amex      → aexp.eightfold.ai
# ---------------------------------------------------------------------------

WORKDAY_COMPANIES: list[dict] = [

    # --- Stadium / naming rights ---
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
        "label":  "Target",
        "url":    "https://target.wd5.myworkdayjobs.com/en-US/targetcareers/jobs",
        "domain": "https://target.wd5.myworkdayjobs.com",
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

    # --- Requested ---
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

    # --- Forever company picks ---
    # Salesforce: top perks, strong IT infra, heavy M365/Azure footprint
    {
        "label":  "Salesforce",
        "url":    "https://salesforce.wd12.myworkdayjobs.com/en-US/External_Career_Site/jobs",
        "domain": "https://salesforce.wd12.myworkdayjobs.com",
    },
    # Workday (the company): strong culture, great benefits, modern IT stack
    {
        "label":  "Workday",
        "url":    "https://workday.wd5.myworkdayjobs.com/en-US/Workday/jobs",
        "domain": "https://workday.wd5.myworkdayjobs.com",
    },
    # Palo Alto Networks: Zero Trust is their product — your Intune +
    # Conditional Access + Defender background is directly relevant
    {
        "label":  "Palo Alto Networks",
        "url":    "https://paloaltonetworks.wd1.myworkdayjobs.com/en-US/External/jobs",
        "domain": "https://paloaltonetworks.wd1.myworkdayjobs.com",
    },
    # ServiceNow: IT automation platform — your PowerShell + Orchestrator +
    # endpoint automation background maps perfectly to their IT team
    {
        "label":  "ServiceNow",
        "url":    "https://servicenow.wd1.myworkdayjobs.com/en-US/Careers/jobs",
        "domain": "https://servicenow.wd1.myworkdayjobs.com",
    },
    # Intuit: strong perks, good retention, solid Azure/M365 footprint
    {
        "label":  "Intuit",
        "url":    "https://intuit.wd1.myworkdayjobs.com/en-US/Intuit_Careers/jobs",
        "domain": "https://intuit.wd1.myworkdayjobs.com",
    },
    # CrowdStrike: Falcon endpoint = adjacent to Defender for Endpoint,
    # their internal IT runs what they sell — great fit for your security posture work
    {
        "label":  "CrowdStrike",
        "url":    "https://crowdstrike.wd5.myworkdayjobs.com/en-US/crowdstrikecareers/jobs",
        "domain": "https://crowdstrike.wd5.myworkdayjobs.com",
    },

    # --- Add more Workday companies below ---
    # {
    #     "label":  "Company Name",
    #     "url":    "https://TENANT.wd1.myworkdayjobs.com/en-US/BOARD/jobs",
    #     "domain": "https://TENANT.wd1.myworkdayjobs.com",
    # },
]



# ---------------------------------------------------------------------------
# LOGGING
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  [%(name)s]  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)