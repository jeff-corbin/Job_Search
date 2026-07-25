"""
main.py
=======
Runs the full job search pipeline

Pipeline:
  1. Load seen IDs
  2. Fetch all sources, dedupe against seen IDs
  3. Enrich salary: try each job's own page first, then batch whatever's
     left through Gemini in chunks
  4. Filter non-US/CA/MX locations
  5. Send email (Low salary jobs excluded from display, still tracked)
  6. Save updated seen IDs
"""

import logging
import datetime

from greenhouse import fetch_greenhouse_jobs
from workday    import fetch_workday_jobs
from netflix    import fetch_netflix_jobs
from location   import enrich_locations
from state      import load_state, save_state
from salary     import try_salary_from_page, estimate_salaries_batch
from emailer    import send_report

log = logging.getLogger(__name__)


def _process_source(
    source_name: str,
    jobs: list[dict],
    seen_ids: set[str],
    all_jobs: list[dict],
) -> int:
    """Deduplicates and appends new jobs. Returns count added. No salary enrichment here — see run()."""
    existing_ids = {j["id"] for j in all_jobs}
    new_count    = 0

    for job in jobs:
        if job["id"] in seen_ids or job["id"] in existing_ids:
            continue
        all_jobs.append(job)
        existing_ids.add(job["id"])
        new_count += 1

    log.info(f"  {source_name}: {new_count} new from {len(jobs)} fetched")
    return new_count


def run() -> None:
    run_date = datetime.datetime.now().strftime("%B %d, %Y")
    log.info("=" * 55)
    log.info(f"Job search starting — {run_date}")
    log.info("=" * 55)

    seen_ids = load_state()
    all_jobs: list[dict] = []

    log.info("Greenhouse")
    _process_source("Greenhouse", fetch_greenhouse_jobs(), seen_ids, all_jobs)

    log.info("Workday")
    _process_source("Workday", fetch_workday_jobs(), seen_ids, all_jobs)

    log.info("Netflix")
    _process_source("Netflix", fetch_netflix_jobs(), seen_ids, all_jobs)

    log.info(f"Step 1 complete: {len(all_jobs)} new job(s)")

    # Step 2: try each job's own detail page for a listed salary first —
    # this is just an HTTP GET per job, not rate-limited.
    still_needs_estimate = [job for job in all_jobs if not try_salary_from_page(job)]
    log.info(f"  {len(all_jobs) - len(still_needs_estimate)} found on page, "
             f"{len(still_needs_estimate)} need Gemini estimation")

    # Step 3: batch whatever's left through Gemini — one call per chunk
    # instead of one call per job.
    estimate_salaries_batch(still_needs_estimate)
    log.info("Step 2 complete: salary enrichment done")

    all_jobs = enrich_locations(all_jobs)
    log.info(f"Step 3 complete: {len(all_jobs)} after location filter")

    send_report(all_jobs, run_date)
    log.info("Step 4 complete: report sent")

    seen_ids.update(job["id"] for job in all_jobs)
    save_state(seen_ids)
    log.info("Step 5 complete: state saved")
    log.info("Done.")


if __name__ == "__main__":
    run()