"""
h1b.py
======
Fetches ACTIVE H1B job postings from the DOL's public LCA disclosure API.

WHAT THIS IS:
  Every employer must file a Labor Condition Application (LCA) with the
  Department of Labor BEFORE they can hire an H1B worker. The DOL publishes
  all certified LCAs publicly. A "Certified" status means the job is ACTIVE
  and approved for H1B hiring right now — the employer is required by law
  to have posted it publicly so US workers had a chance to apply first.

  This is exactly the list you want: active jobs where the employer
  must demonstrate they tried to hire a US citizen first.

WHY THIS IS USEFUL FOR YOUR SEARCH:
  - These are real, active job openings (not historical)
  - The salary is federally certified (prevailing wage) — no lowballing
  - Companies you'd never think to check show up here
  - The DOL API is free, stable, and requires no authentication

DOL API ENDPOINT:
  https://api.dol.gov/V1/H1B
  Requires a free API key from developer.dol.gov (takes 2 minutes to get)
  Set it in your .env as: DOL_API_KEY=your_key_here

  Without a key, we fall back to scraping h1bdata.info's recent certified
  filings page — slower but still works.

FALLBACK (no DOL key):
  Scrapes h1bdata.info for the most recent certified LCA filings.
  Server-rendered HTML, no Playwright needed.

Public API (what main.py calls):
    fetch_h1b_jobs()  ->  list[dict]
"""

import re
import time
import logging
import datetime
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

from config import TITLE_KEYWORDS, H1B_SEARCH_KEYWORDS, DOL_API_KEY

log = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
}


def _is_relevant_title(title: str) -> bool:
    title_lower = title.lower()
    return any(kw in title_lower for kw in TITLE_KEYWORDS)


def _parse_salary(text: str) -> str | None:
    pattern = r"\$[\d,]+(?:\.\d+)?(?:\s*[-–]\s*\$[\d,]+(?:\.\d+)?)?"
    match   = re.search(pattern, text or "")
    return match.group() if match else None


# ---------------------------------------------------------------------------
# METHOD 1: DOL Public API (preferred — requires free API key)
# Get your key at: developer.dol.gov
# ---------------------------------------------------------------------------

def _fetch_via_dol_api(keyword: str) -> list[dict]:
    """
    Query the DOL's official H1B LCA API for certified filings.

    The API returns JSON with fields including:
      EMPLOYER_NAME, JOB_TITLE, WAGE_RATE_OF_PAY_FROM, WAGE_RATE_OF_PAY_TO,
      WORKSITE_CITY, WORKSITE_STATE, CASE_STATUS, RECEIVED_DATE, DECISION_DATE

    We filter to CASE_STATUS = "Certified" — these are the active ones.
    """
    url = "https://api.dol.gov/V1/H1B"
    params = {
        "KEY":    DOL_API_KEY,
        "query":  f"JOB_TITLE eq '{keyword}'",
        "filter": "CASE_STATUS eq 'Certified'",
        "top":    100,
        "format": "json",
    }
    try:
        response = requests.get(url, params=params, headers=HEADERS, timeout=15)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        log.warning(f"  DOL API request failed for '{keyword}': {e}")
        return []
    except ValueError as e:
        log.warning(f"  DOL API JSON parse error for '{keyword}': {e}")
        return []

    records = data.get("d", {}).get("results", [])
    jobs    = []

    for rec in records:
        title = rec.get("JOB_TITLE", "").strip()
        if not _is_relevant_title(title):
            continue

        employer  = rec.get("EMPLOYER_NAME", "Unknown")
        city      = rec.get("WORKSITE_CITY", "")
        state     = rec.get("WORKSITE_STATE", "")
        location  = f"{city}, {state}".strip(", ")

        wage_from = rec.get("WAGE_RATE_OF_PAY_FROM", "")
        wage_to   = rec.get("WAGE_RATE_OF_PAY_TO", "")
        if wage_from and wage_to:
            salary = f"${wage_from:,.0f} – ${wage_to:,.0f}" if isinstance(wage_from, (int, float)) else f"{wage_from} – {wage_to}"
        elif wage_from:
            salary = f"${wage_from:,.0f}" if isinstance(wage_from, (int, float)) else str(wage_from)
        else:
            salary = None

        case_num  = rec.get("CASE_NUMBER", "")
        job_id    = f"h1b_dol_{re.sub(r'[^a-z0-9]', '', case_num.lower())}"
        job_url   = f"https://lcatracker.com/lca/{case_num}" if case_num else ""

        jobs.append({
            "id":               job_id,
            "league":           "H1B Active (DOL)",
            "title":            title,
            "organization":     employer,
            "location":         location,
            "remote":           False,
            "salary":           salary,
            "salary_estimated": False,
            "url":              job_url,
            "scraped_at":       datetime.datetime.now().isoformat(),
        })

    return jobs


# ---------------------------------------------------------------------------
# METHOD 2: h1bdata.info scrape (fallback — no API key needed)
# ---------------------------------------------------------------------------

def _fetch_via_h1bdata(keyword: str, year: int) -> list[dict]:
    """
    Scrape h1bdata.info for recent certified LCA filings.
    Falls back to this when no DOL API key is configured.

    h1bdata.info shows the most recently certified filings at the top
    when sorted by submit date — these are the closest thing to "active"
    without a DOL key.
    """
    url    = "https://h1bdata.info/index.php"
    params = {"job": keyword, "year": str(year)}

    try:
        response = requests.get(url, params=params, headers=HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
    except requests.RequestException as e:
        log.warning(f"  h1bdata.info fetch failed for '{keyword}' {year}: {e}")
        return []

    table = soup.find("table", id="myTable")
    if not table:
        log.debug(f"  No results table for '{keyword}' {year}")
        return []

    jobs = []
    rows = table.find_all("tr")

    # Sort by submit date descending to get most recent filings
    # Table columns: EMPLOYER | JOB TITLE | BASE SALARY | LOCATION | YEAR | SUBMIT DATE | START DATE
    data_rows = []
    for row in rows[1:]:
        cols = row.find_all("td")
        if len(cols) >= 6:
            data_rows.append(cols)

    # Sort by submit date (col 5) descending — most recent first
    def parse_date(cols):
        try:
            return datetime.datetime.strptime(cols[5].get_text(strip=True), "%m/%d/%Y")
        except Exception:
            return datetime.datetime.min

    data_rows.sort(key=parse_date, reverse=True)

    # Only take the most recent 50 per keyword to keep volume manageable
    for cols in data_rows[:50]:
        employer    = cols[0].get_text(strip=True)
        title       = cols[1].get_text(strip=True)
        salary_raw  = cols[2].get_text(strip=True)
        location    = cols[3].get_text(strip=True)
        yr          = cols[4].get_text(strip=True)
        submit_date = cols[5].get_text(strip=True)

        if not _is_relevant_title(title):
            continue

        # Format salary
        salary = salary_raw if salary_raw.startswith("$") else f"${salary_raw}" if salary_raw else None

        # Stable ID
        job_id = (
            f"h1b_{re.sub(r'[^a-z0-9]', '', employer.lower()[:20])}"
            f"_{re.sub(r'[^a-z0-9]', '', title.lower()[:15])}"
            f"_{re.sub(r'[^a-z0-9]', '', location.lower()[:10])}"
            f"_{yr}"
        )

        # Link to employer's h1bdata page
        emp_encoded = employer.replace(" ", "+")
        job_url     = f"https://h1bdata.info/index.php?em={emp_encoded}&job={quote(keyword)}&year={yr}"

        jobs.append({
            "id":               job_id,
            "league":           "H1B Active (LCA)",
            "title":            title,
            "organization":     employer,
            "location":         location,
            "remote":           False,
            "salary":           salary,
            "salary_estimated": False,
            "url":              job_url,
            "scraped_at":       datetime.datetime.now().isoformat(),
            "h1b_filed":        submit_date,
        })

    return jobs


# ---------------------------------------------------------------------------
# PUBLIC FUNCTION
# ---------------------------------------------------------------------------

def fetch_h1b_jobs() -> list[dict]:
    """
    Fetch active H1B LCA filings for our target job titles.
    Uses DOL API if key is configured, falls back to h1bdata.info scraping.
    Deduplicates by job ID across all keywords.
    """
    all_jobs: list[dict] = []
    seen_ids: set[str]   = set()
    current_year         = datetime.datetime.now().year

    use_dol_api = bool(DOL_API_KEY)
    if use_dol_api:
        log.info("Using DOL API for H1B data (authenticated)")
    else:
        log.info("No DOL_API_KEY set — using h1bdata.info fallback")
        log.info("  Get a free key at developer.dol.gov to use the official API")

    for keyword in H1B_SEARCH_KEYWORDS:
        if use_dol_api:
            log.info(f"  H1B DOL API: '{keyword}'")
            jobs = _fetch_via_dol_api(keyword)
        else:
            log.info(f"  H1B h1bdata.info: '{keyword}' ({current_year})")
            jobs = _fetch_via_h1bdata(keyword, current_year)

        new = [j for j in jobs if j["id"] not in seen_ids]
        seen_ids.update(j["id"] for j in new)
        all_jobs.extend(new)
        log.info(f"    {len(new)} new unique H1B filings for '{keyword}'")
        time.sleep(1)

    log.info(f"H1B total: {len(all_jobs)} active filings")
    return all_jobs
