"""
scraper.py
==========
Fetches IT/DevOps/SysAdmin job listings from TeamWork Online —
the primary job board for MLB, NBA, NFL, and NHL teams.

WHY PLAYWRIGHT INSTEAD OF REQUESTS + BEAUTIFULSOUP?
  TeamWork Online is protected by Cloudflare. When a plain requests.get()
  hits the page, Cloudflare detects it's not a real browser and serves a
  JavaScript challenge page with "html { opacity: 0 }" — an empty shell.
  BeautifulSoup then finds zero job cards because there are none in the HTML.

  Playwright launches a real headless Chromium browser, which executes
  JavaScript, passes Cloudflare's fingerprinting checks, and returns the
  fully-rendered page with actual job listings.

  The rest of the code (parsing, filtering, deduplication) is identical
  to what you'd write with BeautifulSoup — we just get real HTML first.

FIRST-TIME SETUP (run these once after pip install):
  playwright install chromium
  playwright install-deps          # Ubuntu/Linux only — installs system libs

Public API (what main.py calls):
    fetch_all_jobs()  ->  list[dict]
        Same dict format as greenhouse.py so main.py handles both identically.
"""

import re
import time
import logging
import datetime

from bs4 import BeautifulSoup # type: ignore
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout # type: ignore

from config import SEARCH_KEYWORDS, TEAMWORK_BASE_URL
from keywords import is_relevant

log = logging.getLogger(__name__)


def _parse_salary(text: str) -> str | None:
    """Extract a dollar salary range from text using regex."""
    pattern = r"\$[\d,]+(?:\.\d+)?(?:\s*[-–]\s*\$[\d,]+(?:\.\d+)?)?"
    match   = re.search(pattern, text or "")
    return match.group() if match else None


# is_relevant() imported from keywords.py — whole-phrase word-boundary matching
# prevents "credit manager" matching "it manager", "requirement" matching "uem", etc.


def _parse_job_cards(html: str) -> list[dict]:
    """
    Parse job listings from fully-rendered TeamWork Online HTML.

    CONFIRMED STRUCTURE (inspected from debug_page.html 2026-03-13):
      Each job is a <div class="browse-jobs-card"> inside a <div class="result-list">
      
      Inside each card:
        Title:   <a class="browse-jobs-card__content--title">
        Org:     <div class="browse-jobs-card__content--organization">
        Location:<div class="trending__content--small">  (first one in the card)
        URL:     href on the title <a> tag
        Job ID:  last segment of URL, e.g. "devops-engineer-2160219" → 2160219

    Example URL pattern:
        /baseball-jobs/pittsburghpirates/pittsburgh-pirates-jobs/devops-engineer-2160219

    If selectors stop working after a site redesign:
      1. python job_search/scraper.py  — saves debug_page.html
      2. Open in browser, inspect a job card, update class names below
    """
    soup  = BeautifulSoup(html, "html.parser")
    jobs  = []

    cards = soup.find_all("div", class_="browse-jobs-card")
    log.debug(f"  Raw browse-jobs-card elements found: {len(cards)}")

    for card in cards:
        # --- Title ---
        title_tag = card.find("a", class_="browse-jobs-card__content--title")
        if not title_tag:
            continue
        title = title_tag.get_text(strip=True)
        if not title or not is_relevant(title):
            continue

        # --- URL and stable job ID ---
        job_url = title_tag.get("href", "")
        if job_url and not job_url.startswith("http"):
            job_url = "https://www.teamworkonline.com" + job_url

        # Extract the numeric ID from the end of the URL: "devops-engineer-2160219"
        id_match = re.search(r"-(\d{6,})$", job_url)
        job_id   = f"two_{id_match.group(1)}" if id_match else f"two_{job_url.split('/')[-1]}"

        # --- Organization ---
        org_tag      = card.find("div", class_="browse-jobs-card__content--organization")
        organization = org_tag.get_text(strip=True) if org_tag else "Sports Org"

        # --- Location ---
        # "trending__content--small" is used for location text in the card
        loc_tag  = card.find("div", class_="trending__content--small")
        location = loc_tag.get_text(strip=True) if loc_tag else "Not specified"

        # --- Remote detection ---
        card_text = card.get_text(" ", strip=True).lower()
        remote    = any(w in card_text for w in ["remote", "work from home", "wfh", "hybrid"])

        # --- Salary ---
        salary = _parse_salary(card_text)

        jobs.append({
            "id":               job_id,
            "league":           "TeamWork Online",
            "title":            title,
            "organization":     organization,
            "location":         location,
            "remote":           remote,
            "salary":           salary,
            "salary_estimated": False,
            "url":              job_url,
            "scraped_at":       datetime.datetime.now().isoformat(),
        })

    return jobs


def fetch_all_jobs() -> list[dict]:
    """
    Launch a headless Chromium browser, search TeamWork Online for each
    keyword, parse results, and return all unique matching jobs.

    We open ONE browser for the entire run and reuse it across all keyword
    searches — much faster than launching a new browser per search.

    sync_playwright() is Playwright's synchronous context manager.
    The 'with' block ensures the browser always closes cleanly, even if
    an exception occurs — equivalent to try/finally in PowerShell.

    Deduplication: we track job IDs in a local set so the same listing
    doesn't appear twice if it matches multiple keywords.
    """
    all_jobs: list[dict] = []
    seen_ids: set[str]   = set()

    log.info("Launching headless Chromium for TeamWork Online...")

    with sync_playwright() as pw:
        # launch(headless=True) means no visible browser window —
        # it runs silently in the background, perfect for a cron job.
        browser = pw.chromium.launch(headless=True)

        # new_context() is like a fresh browser profile — clean cookies,
        # clean cache. Helps avoid Cloudflare session tracking.
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
        )
        page = context.new_page()

        for keyword in SEARCH_KEYWORDS:
            log.info(f"Searching TeamWork Online: '{keyword}'")
            url = (
                f"{TEAMWORK_BASE_URL}"
                f"?employment_opportunity_search[query]={requests_encode(keyword)}"
                f"&utf8=✓"
            )

            try:
                # goto() loads the page; "networkidle" waits until no network
                # requests have fired for 500ms — i.e. JS has finished loading.
                page.goto(url, wait_until="networkidle", timeout=30_000)

                # Extra wait for any lazy-loaded job cards to appear
                page.wait_for_timeout(2000)

            except PlaywrightTimeout:
                log.warning(f"  Timeout loading page for '{keyword}' — skipping")
                continue

            # page.content() returns the fully-rendered HTML that JavaScript built
            html  = page.content()
            jobs  = _parse_job_cards(html)
            new   = [j for j in jobs if j["id"] not in seen_ids]
            seen_ids.update(j["id"] for j in new)
            all_jobs.extend(new)

            log.info(f"  {len(new)} new unique jobs for '{keyword}' ({len(jobs)} on page)")
            time.sleep(2)   # polite pause between searches

        browser.close()

    log.info(f"TeamWork Online total: {len(all_jobs)} unique jobs")
    return all_jobs


def requests_encode(text: str) -> str:
    """
    URL-encode a search string — spaces become %20, etc.
    Python's urllib does this; we avoid importing requests just for this.

    PowerShell equivalent: [System.Uri]::EscapeDataString($text)
    """
    from urllib.parse import quote
    return quote(text, safe="")


# ---------------------------------------------------------------------------
# DEBUG / STANDALONE RUN
# Run this file directly to inspect what TeamWork Online returns:
#   python job_search/scraper.py
#
# Saves the raw rendered HTML to debug_page.html so you can open it in a
# browser and inspect the job card structure if selectors need updating.
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    from pathlib import Path

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s  %(levelname)-8s  [%(name)s]  %(message)s",
    )

    keyword = sys.argv[1] if len(sys.argv) > 1 else "devops"
    print(f"\nDebug: fetching TeamWork Online for '{keyword}'...\n")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        )
        page = context.new_page()

        from urllib.parse import quote
        url = f"{TEAMWORK_BASE_URL}?employment_opportunity_search[query]={quote(keyword)}&utf8=✓"
        print(f"URL: {url}\n")

        page.goto(url, wait_until="networkidle", timeout=30_000)
        page.wait_for_timeout(2000)
        html = page.content()
        browser.close()

    # Save full HTML for inspection
    debug_file = Path("debug_page.html")
    debug_file.write_text(html, encoding="utf-8")
    print(f"Full HTML saved to: {debug_file.resolve()}")
    print(f"HTML length: {len(html)} characters\n")

    # Try parsing
    jobs = _parse_job_cards(html)
    print(f"Jobs found: {len(jobs)}")
    for j in jobs[:5]:
        print(f"  {j['title']} — {j['organization']} — {j['location']}")