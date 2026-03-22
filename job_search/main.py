"""
main.py
=======
Orchestrates the full job search pipeline.
This is the ONLY file your cron job needs to call.

PIPELINE:
  0. Load seen IDs + salary cache from seen_jobs.json
  1. Fetch each source; enrich salary inline for each new job
  2. Filter out non-US/Canada/Mexico jobs; classify location tier
  3. Send the weekly email report
  4. Save updated seen IDs + salary cache to seen_jobs.json

HOW KEYWORD MATCHING WORKS:
  config.py has three lists:
    TITLE_KEYWORDS      — job title must contain at least one (whole phrase)
    DESCRIPTION_KEYWORDS — job description must contain at least one (whole phrase)
    TITLE_EXCLUDE       — job title must NOT contain any of these

  Matching uses word boundaries so "it manager" won't match "credit manager"
  and "uem" won't match "requirement". See keywords.py for details.

HOW TO ADD A NEW JOB SOURCE:
  1. Create a new module: mysite.py (copy workday.py as a template)
     - Implement fetch_myjobs() -> list[dict]
     - Each dict needs: id, title, organization, location, remote,
       salary, salary_estimated, url, league, scraped_at
     - Call is_relevant(title, description) from keywords.py to filter
  2. Add any config it needs to config.py (search keywords, URLs, etc.)
  3. In main.py: add import, add fetch call in Step 1, add to all_fetched

  Microsoft example (currently blocked by bot detection — see microsoft.py):
    from microsoft import fetch_microsoft_jobs
    microsoft_jobs = fetch_microsoft_jobs()
    _process_source("Microsoft", microsoft_jobs, seen_ids, all_jobs)
    # add microsoft_jobs to all_fetched below

CRON SETUP (Ubuntu — every Friday at 8am):
  crontab -e
  0 8 * * 5 cd /home/you/Job_Search && /usr/bin/python3 job_search/main.py >> /var/log/job_search.log 2>&1
"""

import logging
import datetime

from dotenv import load_dotenv # type: ignore
load_dotenv()   # must be before local imports — config.py reads os.getenv() at import time

from scraper    import fetch_all_jobs
from greenhouse import fetch_greenhouse_jobs
from workday    import fetch_workday_jobs
from location   import enrich_locations
from state      import load_state, save_state
from salary     import enrich_one_job
from emailer    import send_report

# ── Future sources (uncomment when ready) ────────────────────────────────────
# from microsoft import fetch_microsoft_jobs

log = logging.getLogger(__name__)


def _process_source(
    source_name: str,
    jobs: list[dict],
    seen_ids: set[str],
    all_jobs: list[dict],
) -> int:
    """
    Process one source's job list:
      - Skip jobs already in seen_ids (reported in a previous run)
      - Skip duplicates within this run (cross-source deduplication)
      - Enrich salary inline for each new job
      - Add to all_jobs

    Returns the count of new jobs added.
    """
    existing_ids = {j["id"] for j in all_jobs}
    new_count    = 0

    for job in jobs:
        if job["id"] in seen_ids:
            continue
        if job["id"] in existing_ids:
            continue

        enrich_one_job(job)         # salary: page fetch → AI estimate → cache
        all_jobs.append(job)
        existing_ids.add(job["id"])
        new_count += 1

    log.info(f"  {source_name}: {new_count} new job(s) from {len(jobs)} fetched")
    return new_count


def run() -> None:
    """Execute the full pipeline end to end."""
    run_date = datetime.datetime.now().strftime("%B %d, %Y")
    log.info("=" * 55)
    log.info(f"Job search starting — {run_date}")
    log.info("=" * 55)

    # ── Step 0: Load state ────────────────────────────────────────────────────
    seen_ids, _ = load_state()
    all_jobs: list[dict] = []

    # ── Step 1: Fetch all sources ─────────────────────────────────────────────
    # Each source fetches jobs, filters by keywords, returns a list of dicts.
    # _process_source() deduplicates, enriches salary, and accumulates.

    log.info("── Source 1: TeamWork Online (sports teams) ──")
    sports_jobs = fetch_all_jobs()
    _process_source("TeamWork Online", sports_jobs, seen_ids, all_jobs)

    log.info("── Source 2: Greenhouse API ──")
    greenhouse_jobs = fetch_greenhouse_jobs()
    _process_source("Greenhouse", greenhouse_jobs, seen_ids, all_jobs)

    log.info("── Source 3: Workday portals ──")
    workday_jobs = fetch_workday_jobs()
    _process_source("Workday", workday_jobs, seen_ids, all_jobs)

    # ── Add new sources here ──────────────────────────────────────────────────
    # log.info("── Source 4: Microsoft Careers ──")
    # microsoft_jobs = fetch_microsoft_jobs()
    # _process_source("Microsoft", microsoft_jobs, seen_ids, all_jobs)

    log.info(f"Step 1 complete: {len(all_jobs)} new job(s) total.")

    # ── Step 2: Location filter ───────────────────────────────────────────────
    all_jobs = enrich_locations(all_jobs)
    log.info(f"Step 2 complete: {len(all_jobs)} job(s) after location filter.")

    # ── Step 3: Send report ───────────────────────────────────────────────────
    send_report(all_jobs, run_date)
    log.info("Step 3 complete: report sent.")

    # ── Step 4: Save state ────────────────────────────────────────────────────
    all_fetched = sports_jobs + greenhouse_jobs + workday_jobs
    # + microsoft_jobs   # uncomment when Microsoft source is active
    seen_ids.update(job["id"] for job in all_fetched)

    from state import _salary_cache
    save_state(seen_ids, _salary_cache)
    log.info("Step 4 complete: state saved.")

    log.info("Pipeline finished.")


if __name__ == "__main__":
    run()
