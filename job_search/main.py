"""
main.py
=======
Runs the full pipeline. This is the only file cron needs to call.

Pipeline:
  1. Load seen IDs
  2. Fetch all sources, filter to new jobs, enrich salary
  3. Filter non-US/CA/MX locations
  4. Send email (Low salary jobs excluded from display, still tracked)
  5. Save updated seen IDs
"""

import logging
import datetime

from greenhouse import fetch_greenhouse_jobs
from workday    import fetch_workday_jobs
from location   import enrich_locations
from state      import load_state, save_state
from salary     import enrich_one_job
from emailer    import send_report

log = logging.getLogger(__name__)


def _process_source(
    source_name: str,
    jobs: list[dict],
    seen_ids: set[str],
    all_jobs: list[dict],
) -> int:
    """Deduplicates, enriches salary, appends new jobs. Returns count added."""
    existing_ids = {j["id"] for j in all_jobs}
    new_count    = 0

    for job in jobs:
        if job["id"] in seen_ids or job["id"] in existing_ids:
            continue
        enrich_one_job(job)
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

    log.info(f"Step 1 complete: {len(all_jobs)} new job(s)")

    all_jobs = enrich_locations(all_jobs)
    log.info(f"Step 2 complete: {len(all_jobs)} after location filter")

    send_report(all_jobs, run_date)
    log.info("Step 3 complete: report sent")

    seen_ids.update(job["id"] for job in all_jobs)
    save_state(seen_ids)
    log.info("Step 4 complete: state saved")
    log.info("Done.")


if __name__ == "__main__":
    run()