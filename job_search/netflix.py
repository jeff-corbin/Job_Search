"""
netflix.py
==========
Fetches job listings from Netflix's careers site.

Runs GET requests in blocks of 10 (what's provided on the "Show more 
positions" button in the GUI)
e.g.:
    GET https://explore.jobs.netflix.net/api/apply/v2/jobs
        ?domain=netflix.com&start={offset}&num={page_size}
        &sort_by=old&triggerGoButton=true
"""

import time
import logging
import datetime

import requests  # type: ignore

from config import (
    NETFLIX_CAREERS_URL,
    NETFLIX_API_URL,
    NETFLIX_DOMAIN,
    NETFLIX_PAGE_SIZE,
    NETFLIX_MAX_PAGES,
)
from keywords import is_relevant

log = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept":          "*/*",
    "Accept-Language": "en-US,en;q=0.9",
    "Content-Type":    "application/json",
    "Referer":         NETFLIX_CAREERS_URL,
}


def _job_from_position(position: dict) -> dict | None:
    """Convert one Eightfold position dict into our common job dict format."""
    title = (position.get("name") or "").strip()
    if not title:
        return None

    # No full description available from this endpoint — title-only match.
    # (DESCRIPTION_KEYWORDS in config.py won't fire for Netflix jobs.)
    if not is_relevant(title, ""):
        return None

    job_id   = f"nf_{position.get('id', abs(hash(title)))}"
    location = position.get("location") or "Not specified"

    work_opt = (position.get("work_location_option") or "").lower()
    remote   = "remote" in work_opt or "remote" in location.lower()

    return {
        "id":               job_id,
        "title":            title,
        "organization":     "Netflix",
        "location":         location,
        "remote":           remote,
        "salary":           None,          # never present in this API's response
        "salary_estimated": False,
        "url":              position.get("canonicalPositionUrl", ""),
        "scraped_at":       datetime.datetime.now().isoformat(),
    }


def _fetch_all_positions(session: requests.Session, debug_log: bool = False) -> dict[int, dict]:
    """
    Walk the Eightfold API's pagination (start/num) until it stops
    returning new positions, a reported total is reached, or the
    NETFLIX_MAX_PAGES safety cap is hit.
    """
    collected: dict[int, dict] = {}
    start = 0
    total_count: int | None = None

    for page_num in range(NETFLIX_MAX_PAGES):
        params = {
            "domain":         NETFLIX_DOMAIN,
            "start":          start,
            "num":            NETFLIX_PAGE_SIZE,
            "sort_by":        "old",
            "triggerGoButton": "true",
        }

        try:
            resp = session.get(NETFLIX_API_URL, params=params, headers=_HEADERS, timeout=15)
        except requests.RequestException as e:
            log.warning(f"  Netflix API request failed (start={start}): {e}")
            break

        if debug_log:
            log.debug(f"  page {page_num}: GET {resp.url} -> {resp.status_code}")

        if resp.status_code != 200:
            log.warning(f"  Netflix API returned {resp.status_code} at start={start} — stopping")
            break

        try:
            data = resp.json()
        except ValueError as e:
            log.warning(f"  Netflix API JSON parse error at start={start}: {e}")
            break

        positions = data.get("positions", [])
        if debug_log:
            log.debug(f"    positions returned: {len(positions)}   count field: {data.get('count')}")

        if not positions:
            break

        for pos in positions:
            pid = pos.get("id")
            if pid is not None:
                collected[pid] = pos

        if total_count is None and isinstance(data.get("count"), int):
            total_count = data["count"]

        start += NETFLIX_PAGE_SIZE

        if total_count is not None and start >= total_count:
            break

        time.sleep(1)  # polite pause between pages

    return collected


def fetch_netflix_jobs() -> list[dict]:
    """
    Fetch Netflix's full job list via the Eightfold API and filter
    locally with is_relevant() — same shape as fetch_greenhouse_jobs()
    / fetch_workday_jobs().
    """
    log.info("Fetching Netflix (Eightfold API)...")

    session = requests.Session()
    try:
        session.get(NETFLIX_CAREERS_URL, headers=_HEADERS, timeout=15)  # prime session cookies
    except requests.RequestException as e:
        log.warning(f"  Could not prime Netflix session cookies: {e}")

    positions = _fetch_all_positions(session)
    log.info(f"  Collected {len(positions)} total Netflix postings")

    jobs = [j for j in (_job_from_position(p) for p in positions.values()) if j]
    log.info(f"Netflix total: {len(jobs)} unique relevant jobs (filtered from {len(positions)} fetched)")
    return jobs


# ---------------------------------------------------------------------------
# DEBUG / STANDALONE RUN
# python job_search/netflix.py
#
# Prints page-by-page fetch progress (including HTTP status codes —
# check these first if something looks wrong), then the final filtered
# job list, plus a check for the specific job that motivated this
# whole redesign.
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s  %(levelname)-8s  [%(name)s]  %(message)s",
    )
    logging.getLogger().setLevel(logging.DEBUG)  # config.py's basicConfig() runs first and wins otherwise

    print("\nDebug: Netflix full job list fetch (direct API)\n")

    session = requests.Session()
    priming_resp = session.get(NETFLIX_CAREERS_URL, headers=_HEADERS, timeout=15)
    print(f"Priming GET {NETFLIX_CAREERS_URL} -> {priming_resp.status_code}")
    print(f"Cookies acquired: {list(session.cookies.keys())}\n")

    positions = _fetch_all_positions(session, debug_log=True)

    print(f"\nCollected {len(positions)} total Netflix postings")

    jobs = [j for j in (_job_from_position(p) for p in positions.values()) if j]
    print(f"Jobs passing is_relevant() filter: {len(jobs)}\n")
    for j in jobs:
        print(f"  {j['title']} — {j['location']}  ({'Remote' if j['remote'] else 'On-site'})")
        print(f"    {j['url']}")

    target_id = 790315492635
    if target_id in positions:
        print(f"\n✓ Confirmed: job {target_id} (Systems Administrator, Engineering Operations) was collected.")
        print(f"  Passed is_relevant()? {any(j['id'] == f'nf_{target_id}' for j in jobs)}")
    else:
        print(f"\n✗ Job {target_id} was NOT in the collected list — pagination didn't reach it.")