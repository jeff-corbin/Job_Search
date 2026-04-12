"""
workday.py
==========
Fetches IT/DevOps job listings from Workday career portals using Playwright.

HOW WORKDAY SEARCH URLS WORK:
  Every Workday career site follows this pattern:
    https://{tenant}.wd{N}.myworkdayjobs.com/en-US/{board}/jobs?q={keyword}

  The tenant and board name are company-specific. We store them in
  config.WORKDAY_COMPANIES. The search keyword is appended at runtime.

  We search each company once per keyword from SEARCH_KEYWORDS,
  then deduplicate by job ID so the same listing never appears twice.

CONFIRMED WORKDAY TENANTS (verified 2026-03-13):
  AT&T, T-Mobile, Target, Comcast/Xfinity, Capital One, Nationwide,
  American Family Insurance — all confirmed via their careers pages.

Public API (what main.py calls):
    fetch_workday_jobs()  ->  list[dict]
        Same dict format as scraper.py and greenhouse.py.
"""

import re
import time
import logging
import datetime

from bs4 import BeautifulSoup # type: ignore
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout # type: ignore

from config import WORKDAY_COMPANIES, SEARCH_KEYWORDS
from keywords import is_relevant

log = logging.getLogger(__name__)


def _parse_salary(text: str) -> str | None:
    """Extract a dollar salary range from text using regex."""
    pattern = r"\$[\d,]+(?:\.\d+)?(?:\s*[-–]\s*\$[\d,]+(?:\.\d+)?)?"
    match   = re.search(pattern, text or "")
    return match.group() if match else None


# is_relevant() imported from keywords.py — whole-phrase word-boundary matching


def _parse_workday_html(html: str, label: str, domain: str) -> list[dict]:
    """
    Extract job listings from a rendered Workday search results page.

    CONFIRMED WORKDAY STRUCTURE (inspected from AT&T debug HTML 2026-03-13):
      Job list:  <ul> inside <section data-automation-id="jobResults">
      Job cards: <li> direct children of that <ul>

      Inside each card (all use stable data-automation-id attributes):
        Title + URL: <a data-automation-id="jobTitle">
        Location:    <div data-automation-id="locations">
        Remote:      <div data-automation-id="remoteType">
        Job ID:      extracted from href, e.g. "DevOps-Engineer_R-73647" → R-73647

      Note: CSS class names like "css-1q2dra3" are hashed by Workday and change
      on rebuilds. We use data-automation-id exclusively — those are stable.

    If parsing breaks after a Workday update, run:
        python job_search/workday.py
    This saves debug_workday_{label}.html for inspection.
    """
    soup = BeautifulSoup(html, "html.parser")
    jobs = []

    # Find the job results container then the list inside it
    results_section = soup.find(attrs={"data-automation-id": "jobResults"})
    if not results_section:
        log.debug(f"  {label}: no jobResults section found in HTML")
        return []

    ul    = results_section.find("ul")
    if not ul:
        log.debug(f"  {label}: no <ul> inside jobResults")
        return []

    cards = ul.find_all("li", recursive=False)
    log.debug(f"  {label}: {len(cards)} raw job cards found")

    for card in cards:
        # --- Title + URL ---
        title_tag = card.find(attrs={"data-automation-id": "jobTitle"})
        if not title_tag:
            continue

        title     = title_tag.get_text(strip=True)
        card_text = card.get_text(" ", strip=True)   # extract early for relevance check

        if not title or not is_relevant(title, card_text):
            continue

        # --- URL and stable job ID ---
        # Workday hrefs are relative: /en-US/ATTGeneral/job/Location/Title_R-12345
        # The job ID is after the last underscore: R-73647, JR-123456, etc.
        job_url  = title_tag.get("href", "")
        id_match = re.search(r"_([A-Z0-9\-]+)(?:\?|$)", job_url)
        job_id   = f"wd_{id_match.group(1)}" if id_match else f"wd_{abs(hash(job_url))}"

        # Make URL absolute using the company's own tenant domain
        if job_url and not job_url.startswith("http"):
            job_url = f"{domain}{job_url}"

        # --- Location ---
        loc_tag  = card.find(attrs={"data-automation-id": "locations"})
        location = loc_tag.get_text(strip=True) if loc_tag else "Not specified"
        location = re.sub(r"^locations", "", location, flags=re.I).strip()

        # --- Remote detection ---
        remote_tag  = card.find(attrs={"data-automation-id": "remoteType"})
        remote_text = remote_tag.get_text(strip=True).lower() if remote_tag else ""
        remote = any(w in remote_text for w in ["remote", "hybrid", "work from home"])

        # --- Salary ---
        salary = _parse_salary(card_text)

        jobs.append({
            "id":               job_id,
            "league":           f"Workday – {label}",
            "title":            title,
            "organization":     label,
            "location":         location,
            "remote":           remote,
            "salary":           salary,
            "salary_estimated": False,
            "url":              job_url,
            "scraped_at":       datetime.datetime.now().isoformat(),
        })

    return jobs


def _search_company(page, company: dict, keyword: str) -> list[dict]:
    """
    Search one Workday company for one keyword.
    Reuses an already-open Playwright page for efficiency.
    """
    label    = company["label"]
    base_url = company["url"]

    # Append keyword as query parameter
    # Workday uses ?q= for search — standard across all tenants
    from urllib.parse import quote
    search_url = f"{base_url}?q={quote(keyword)}"

    try:
        page.goto(search_url, wait_until="domcontentloaded", timeout=30_000)
        # Workday needs extra time to render job cards after DOM loads
        page.wait_for_timeout(4000)
    except PlaywrightTimeout:
        log.warning(f"  Timeout: {label} / '{keyword}' — skipping")
        return []

    html  = page.content()
    jobs  = _parse_workday_html(html, label, company["domain"])
    return jobs


def fetch_workday_jobs() -> list[dict]:
    """
    Search all configured Workday companies for all keywords.
    Returns unique matching jobs as a flat list.

    We open ONE browser for the entire run and reuse it across all
    company + keyword combinations — much faster than launching a
    new browser for each search.
    """
    all_jobs: list[dict] = []
    seen_ids: set[str]   = set()

    log.info("Launching headless Chromium for Workday companies...")

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
        )
        page = context.new_page()

        for company in WORKDAY_COMPANIES:
            label       = company["label"]
            company_jobs: list[dict] = []
            company_seen: set[str]   = set()

            for keyword in SEARCH_KEYWORDS:
                log.info(f"  Workday: {label} / '{keyword}'")
                jobs = _search_company(page, company, keyword)

                # Deduplicate within this company across keywords
                new = [j for j in jobs if j["id"] not in company_seen]
                company_seen.update(j["id"] for j in new)
                company_jobs.extend(new)

                time.sleep(2)   # polite pause between searches

            log.info(f"  {label}: {len(company_jobs)} relevant jobs total")

            # Deduplicate across all companies (unlikely but possible)
            new_global = [j for j in company_jobs if j["id"] not in seen_ids]
            seen_ids.update(j["id"] for j in new_global)
            all_jobs.extend(new_global)

        browser.close()

    log.info(f"Workday total: {len(all_jobs)} unique jobs across all companies")
    return all_jobs


# ---------------------------------------------------------------------------
# DEBUG / STANDALONE RUN
# python job_search/workday.py [company_label] [keyword]
# Saves debug_workday_{label}.html for selector inspection.
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys
    from pathlib import Path
    from urllib.parse import quote

    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s  %(levelname)-8s  [%(name)s]  %(message)s",
    )

    # Default to first company and "devops" if no args given
    target_label = sys.argv[1] if len(sys.argv) > 1 else WORKDAY_COMPANIES[0]["label"]
    keyword      = sys.argv[2] if len(sys.argv) > 2 else "devops"

    company = next((c for c in WORKDAY_COMPANIES if c["label"].lower() == target_label.lower()), WORKDAY_COMPANIES[0])
    print(f"\nDebug: {company['label']} / '{keyword}'")
    search_url = f"{company['url']}?q={quote(keyword)}"
    print(f"URL: {search_url}\n")

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
        page.goto(search_url, wait_until="domcontentloaded", timeout=30_000)
        page.wait_for_timeout(4000)
        html = page.content()
        browser.close()

    safe_label = re.sub(r"[^a-z0-9]", "_", company["label"].lower())
    debug_file = Path(f"debug_workday_{safe_label}.html")
    debug_file.write_text(html, encoding="utf-8")
    print(f"HTML saved to: {debug_file.resolve()}")
    print(f"HTML length: {len(html)} chars\n")

    jobs = _parse_workday_html(html, company["label"], company["domain"])
    print(f"Jobs parsed: {len(jobs)}")
    for j in jobs[:5]:
        print(f"  {j['title']} — {j['organization']} — {j['location']}")