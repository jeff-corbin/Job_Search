"""
state.py
========
Tracks seen job IDs between runs so you don't get the same jobs every time.
Reads/writes seen_jobs.json.

Handles old format (plain list) automatically for backward compat.
"""

import json
import logging
from pathlib import Path

from config import STATE_FILE

log = logging.getLogger(__name__)


def load_state() -> set[str]:
    """Load seen job IDs from disk. Returns empty set if file doesn't exist."""
    if not STATE_FILE.exists():
        log.info("No state file — starting fresh.")
        return set()

    try:
        with STATE_FILE.open() as f:
            data = json.load(f)

        # Old format was a plain list
        if isinstance(data, list):
            log.info("Migrating state file from old format...")
            return set(data)

        if isinstance(data, dict):
            return set(data.get("seen_ids", []))

        log.warning("Unrecognized state file format — starting fresh.")
        return set()

    except (json.JSONDecodeError, OSError) as e:
        log.warning(f"Could not read state file: {e} — starting fresh.")
        return set()


def save_state(seen_ids: set[str]) -> None:
    """Write seen job IDs to disk."""
    try:
        with STATE_FILE.open("w") as f:
            json.dump({"seen_ids": sorted(seen_ids)}, f, indent=2)
        log.info(f"Saved {len(seen_ids)} seen IDs.")
    except OSError as e:
        log.error(f"Failed to write state file: {e}")