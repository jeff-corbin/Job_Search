"""
greenhouse.py
=============
Fetches jobs from Greenhouse's public JSON API. No key needed.

Endpoint: GET https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true
A 404 means the token is wrong — logs a warning and returns [], won't crash.

How to find a token:
  Go to a company's careers page → click any job →
  look for "greenhouse.io/TOKEN" in the URL.
  Verify: https://boards-api.greenhouse.io/v1/boards/TOKEN/jobs
"""

import re
import time
import logging
import datetime

import requests  # type: ignore

from config import GREENHOUSE_COMPANIES
from keywords import is_relevant

log = logging.getLogger(__name__)

_API     = "https://boards-api.greenhouse.io/v1/boards/{token}/jobs?content=true"
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
}


def _fetch_company(token: str, label: str) -> list[dict]:
    log.info(f"Fetching Greenhouse: {label}")
    try:
        resp = requests.get(_API.format(token=token), headers=_HEADERS, timeout=15)
        resp.raise_for_status()
        raw_jobs = resp.json().get("jobs", [])
    except requests.RequestException as e:
        log.warning(f"  Request failed for {label}: {e}")
        return []
    except ValueError as e:
        log.warning(f"  JSON parse error for {label}: {e}")
        return []

    log.info(f"  {len(raw_jobs)} total — filtering...")
    jobs = []

    for raw in raw_jobs:
        title            = raw.get("title", "").strip()
        description_html = raw.get("content", "") or ""
        description_text = re.sub(r"<[^>]+>", " ", description_html)

        if not is_relevant(title, description_text):
            continue

        job_id   = f"gh_{raw.get('id', '')}"
        location = raw.get("location", {}).get("name", "Not specified")
        remote   = any(
            w in description_text.lower() or w in title.lower()
            for w in ["remote", "work from home", "wfh", "hybrid"]
        )

        salary_match = re.search(r"\$[\d,]+(?:\.\d+)?(?:\s*[-–]\s*\$[\d,]+(?:\.\d+)?)?", description_text)

        jobs.append({
            "id":               job_id,
            "title":            title,
            "organization":     label,
            "location":         location,
            "remote":           remote,
            "salary":           salary_match.group() if salary_match else None,
            "salary_estimated": False,
            "url":              raw.get("absolute_url", ""),
            "scraped_at":       datetime.datetime.now().isoformat(),
        })

    log.info(f"  {len(jobs)} relevant for {label}")
    return jobs


def fetch_greenhouse_jobs() -> list[dict]:
    """Fetch IT jobs from all configured Greenhouse companies."""
    all_jobs: list[dict] = []
    for entry in GREENHOUSE_COMPANIES:
        all_jobs.extend(_fetch_company(entry["token"], entry["label"]))
        time.sleep(1)
    log.info(f"Greenhouse total: {len(all_jobs)}")
    return all_jobs