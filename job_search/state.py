"""
state.py
========
Handles ALL persistence between weekly runs:

  1. SEEN JOB IDs — which jobs have already been reported
     (so we only surface new listings each run)

  2. SALARY CACHE — salary data we've already looked up
     (so we never hit Gemini twice for the same job)

Both are stored in seen_jobs.json as a single JSON object:
  {
    "seen_ids": ["gh_123", "wd_456", ...],
    "salary_cache": {
      "gh_123": {
        "salary": "$120,000 – $150,000",
        "salary_estimated": true,
        "salary_low": 120000,
        "salary_high": 150000,
        "salary_band": "✓ Strong"
      },
      ...
    }
  }

WHY CACHE SALARIES?
  Gemini's free tier has a daily request limit. Without caching, every
  run re-estimates salary for every job we've ever seen — burning quota
  on jobs we already have salary data for. With caching, Gemini is only
  called for genuinely new jobs we've never processed before.

  A job stays in the salary cache indefinitely. Salary data doesn't
  change much, and if it does, the next time the job appears as "new"
  (re-posted) it'll get a fresh lookup.

Public API (what main.py and salary.py call):
    load_state()                    -> (seen_ids: set, salary_cache: dict)
    save_state(seen_ids, salary_cache) -> None
    
    # Convenience wrappers used by salary.py:
    get_cached_salary(job_id)       -> dict | None
    cache_salary(job_id, job)       -> None
"""

import json
import logging
from pathlib import Path

from config import STATE_FILE

log = logging.getLogger(__name__)

# Module-level cache — loaded once per run, shared across all calls.
# This avoids re-reading the file on every salary lookup.
# PowerShell equivalent: a script-scoped $script:salaryCache hashtable.
_salary_cache: dict = {}
_seen_ids: set      = set()
_state_loaded       = False


def load_state() -> tuple[set[str], dict]:
    """
    Load both seen IDs and salary cache from seen_jobs.json.
    Returns (seen_ids_set, salary_cache_dict).

    Handles both the new format (dict with "seen_ids" + "salary_cache")
    and the old format (plain list of IDs) for backward compatibility —
    so your existing seen_jobs.json won't break when you upgrade.
    """
    global _salary_cache, _seen_ids, _state_loaded

    if not STATE_FILE.exists():
        log.info(f"No state file at '{STATE_FILE}' — starting fresh.")
        _seen_ids     = set()
        _salary_cache = {}
        _state_loaded = True
        return _seen_ids, _salary_cache

    try:
        with STATE_FILE.open() as f:
            data = json.load(f)

        # Handle old format: plain list of IDs
        # If it's a list, migrate it to the new dict format transparently
        if isinstance(data, list):
            log.info(f"Migrating state file from old format (list → dict)...")
            _seen_ids     = set(data)
            _salary_cache = {}

        # New format: dict with "seen_ids" and "salary_cache" keys
        elif isinstance(data, dict):
            _seen_ids     = set(data.get("seen_ids", []))
            _salary_cache = data.get("salary_cache", {})

        else:
            log.warning("Unrecognized state file format — starting fresh.")
            _seen_ids     = set()
            _salary_cache = {}

        log.info(
            f"Loaded {len(_seen_ids)} seen IDs and "
            f"{len(_salary_cache)} cached salaries from '{STATE_FILE}'."
        )

    except (json.JSONDecodeError, OSError) as e:
        log.warning(f"Could not read state file: {e} — starting fresh.")
        _seen_ids     = set()
        _salary_cache = {}

    _state_loaded = True
    return _seen_ids, _salary_cache


def save_state(seen_ids: set[str], salary_cache: dict) -> None:
    """
    Write both seen IDs and salary cache to seen_jobs.json.

    seen_ids is saved as a sorted list for human readability.
    salary_cache is saved as-is (dict keyed by job ID).
    """
    data = {
        "seen_ids":     sorted(seen_ids),
        "salary_cache": salary_cache,
    }
    try:
        with STATE_FILE.open("w") as f:
            json.dump(data, f, indent=2)
        log.info(
            f"Saved {len(seen_ids)} seen IDs and "
            f"{len(salary_cache)} cached salaries to '{STATE_FILE}'."
        )
    except OSError as e:
        log.error(f"Failed to write state file: {e}")


def get_cached_salary(job_id: str) -> dict | None:
    """
    Return cached salary data for a job ID, or None if not cached.
    Called by salary.py before making any AI or HTTP calls.

    Returns a dict with keys: salary, salary_estimated, salary_low,
    salary_high, salary_band — or None if this job hasn't been seen before.
    """
    return _salary_cache.get(job_id)


def cache_salary(job_id: str, job: dict) -> None:
    """
    Store salary data for a job in the in-memory cache.
    The cache is written to disk at the end of the run by save_state().

    We only cache the salary-related fields, not the full job dict,
    to keep the file size manageable.
    """
    _salary_cache[job_id] = {
        "salary":           job.get("salary"),
        "salary_estimated": job.get("salary_estimated", True),
        "salary_low":       job.get("salary_low"),
        "salary_high":      job.get("salary_high"),
        "salary_band":      job.get("salary_band", "? Unknown"),
    }


# ---------------------------------------------------------------------------
# BACKWARD COMPATIBILITY — keep old function names working so nothing breaks
# if any other module still calls them
# ---------------------------------------------------------------------------

def load_seen_ids() -> set[str]:
    """Legacy wrapper — loads full state, returns just the seen IDs set."""
    seen, _ = load_state()
    return seen


def save_seen_ids(ids: set[str]) -> None:
    """Legacy wrapper — saves seen IDs while preserving existing salary cache."""
    save_state(ids, _salary_cache)
