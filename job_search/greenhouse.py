"""
greenhouse.py
=============
Fetches job listings from Greenhouse's free, public, no-key JSON API.

WHAT IS GREENHOUSE?
  An ATS (Applicant Tracking System) used by thousands of companies.
  Unlike enterprise portals (Workday, Oracle HCM) that are JavaScript-
  rendered and Cloudflare-protected, Greenhouse exposes a clean REST API
  that returns JSON directly — no browser needed, no auth required.

API ENDPOINT:
  GET https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true

  {token} is the company's board slug. Verified tokens are in config.py.
  A 404 means the token is wrong — it logs a warning and returns [],
  it does NOT crash the run.

WHAT'S COVERED HERE vs SCRAPER.PY:
  - greenhouse.py  → stadium sponsors, MSPs, and a handful of sports teams
                     confirmed to be on Greenhouse (6 of 120+ tested)
  - scraper.py     → remaining sports teams via TeamWork Online (Playwright)

HOW TO FIND MORE TOKENS:
  Run find_tokens.py from the project root. Or manually:
    1. Go to careers page, click any job listing
    2. Look for "greenhouse.io/XXXX" in the URL — XXXX is the token
    3. Verify: https://boards-api.greenhouse.io/v1/boards/TOKEN/jobs

Public API (what main.py calls):
    fetch_greenhouse_jobs()  ->  list[dict]
"""

import re
import time
import logging
import datetime

import requests # type: ignore

from config import GREENHOUSE_COMPANIES
from keywords import is_relevant

log = logging.getLogger(__name__)

GREENHOUSE_API = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
}


# is_relevant() imported from keywords.py — whole-phrase word-boundary matching


def _parse_salary(text: str) -> str | None:
    """Extract a dollar salary range from text using regex."""
    pattern = r"\$[\d,]+(?:\.\d+)?(?:\s*[-–]\s*\$[\d,]+(?:\.\d+)?)?"
    match   = re.search(pattern, text or "")
    return match.group() if match else None


def _fetch_company(token: str, label: str) -> list[dict]:
    """
    Call the Greenhouse API for one company and return matching jobs.

    response.json() parses the JSON body into a Python dict — equivalent
    to ConvertFrom-Json in PowerShell.

    .get("jobs", []) safely returns an empty list if the key is missing,
    rather than crashing with a KeyError — equivalent to:
        $data.jobs ?? @()   in PowerShell 7+
    """
    url = GREENHOUSE_API.format(token=token)
    log.info(f"Fetching Greenhouse: {label} ({token})")

    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        log.warning(f"  Request failed for {label}: {e}")
        return []
    except ValueError as e:
        log.warning(f"  JSON parse error for {label}: {e}")
        return []

    raw_jobs = data.get("jobs", [])
    log.info(f"  {len(raw_jobs)} total listings — filtering by keyword...")

    jobs = []
    for raw in raw_jobs:
        title = raw.get("title", "").strip()

        # Strip HTML tags from description for text processing
        description_html = raw.get("content", "") or ""
        description_text = re.sub(r"<[^>]+>", " ", description_html)

        if not is_relevant(title, description_text):
            continue

        job_id   = f"gh_{raw.get('id', '')}"
        job_url  = raw.get("absolute_url", "")
        location = raw.get("location", {}).get("name", "Not specified")

        remote = any(
            word in description_text.lower() or word in title.lower()
            for word in ["remote", "work from home", "wfh", "hybrid"]
        )

        salary = _parse_salary(description_text)

        jobs.append({
            "id":               job_id,
            "league":           f"Greenhouse – {label}",
            "title":            title,
            "organization":     label,
            "location":         location,
            "remote":           remote,
            "salary":           salary,
            "salary_estimated": False,
            "url":              job_url,
            "scraped_at":       datetime.datetime.now().isoformat(),
        })

    log.info(f"  {len(jobs)} relevant jobs for {label}")
    return jobs


def fetch_greenhouse_jobs() -> list[dict]:
    """
    Fetch IT/DevOps jobs from all configured Greenhouse companies.
    Returns a flat list in the same dict format as scraper.fetch_all_jobs().
    """
    all_jobs: list[dict] = []

    for entry in GREENHOUSE_COMPANIES:
        jobs = _fetch_company(entry["token"], entry["label"])
        all_jobs.extend(jobs)
        time.sleep(1)

    log.info(f"Greenhouse total: {len(all_jobs)} relevant jobs across all companies")
    return all_jobs
