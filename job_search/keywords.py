"""
keywords.py
===========
Shared keyword matching logic used by every source module.

HOW MATCHING WORKS:
  By using word-boundary matching (\\b in regex):
    "it manager"  matches  "IT Manager" or "Senior IT Manager"
    "it manager"  does NOT match "credit manager" or "digital"
    "uem"         matches  "UEM Administrator"
    "uem"         does NOT match "requirement" or "urement"
    "entra"       matches  "Entra ID Engineer"
    "entra"       does NOT match "entrepreneur"

  Multi-word phrases like "it manager" are matched as a whole phrase,
  not as individual words. The phrase must appear with word boundaries
  on both ends.

  Case-insensitive throughout — "Intune" matches "intune", "INTUNE", etc.

Public API (what source modules call):
    is_relevant(title, description="")  ->  bool
    compile_patterns(keywords)          ->  list[re.Pattern]  (for performance)
"""

import re
import logging
from functools import lru_cache

log = logging.getLogger(__name__)


def _make_pattern(phrase: str) -> re.Pattern:
    """
    Compile a regex pattern for whole-phrase word-boundary matching.

    For a phrase like "it manager":
      Pattern becomes: \\bit\\s+manager\\b
      This matches "IT Manager", "Senior IT Manager" but NOT "credit manager"

    For a single word like "intune":
      Pattern becomes: \\bintune\\b
      This matches "Intune Engineer" but NOT "requirement"

    re.escape() handles any special regex chars in the phrase (e.g. "&" in "M&T").
    """
    # Escape special regex characters, then replace escaped spaces with \s+
    # to allow flexible whitespace between words in the phrase
    escaped = re.escape(phrase.strip())
    # re.escape turns spaces into '\ ' — replace with \s+ for flexibility
    pattern = escaped.replace(r'\ ', r'\s+')
    return re.compile(r'\b' + pattern + r'\b', re.IGNORECASE)


@lru_cache(maxsize=None)
def _get_title_patterns():
    """
    Compile and cache regex patterns for TITLE_KEYWORDS.
    lru_cache means this only runs once per process — not once per job.
    """
    from config import TITLE_KEYWORDS
    return [_make_pattern(kw) for kw in TITLE_KEYWORDS]


@lru_cache(maxsize=None)
def _get_exclude_patterns():
    """Compile and cache regex patterns for TITLE_EXCLUDE."""
    from config import TITLE_EXCLUDE
    return [_make_pattern(ex) for ex in TITLE_EXCLUDE]


@lru_cache(maxsize=None)
def _get_description_patterns():
    """Compile and cache regex patterns for DESCRIPTION_KEYWORDS."""
    from config import DESCRIPTION_KEYWORDS
    return [_make_pattern(kw) for kw in DESCRIPTION_KEYWORDS]


def is_relevant(title: str, description: str = "") -> bool:
    """
    Return True if this job should be included in results.

    Rules (applied in order):
      1. If title matches any TITLE_EXCLUDE phrase → False (hard drop)
      2. If title matches any TITLE_KEYWORDS phrase → True
      3. If description matches any DESCRIPTION_KEYWORDS phrase → True
      4. Otherwise → False

    Args:
        title:       The job title string
        description: Full or partial job description text (optional)
    """
    # Rule 1: Hard exclude
    for pattern in _get_exclude_patterns():
        if pattern.search(title):
            return False

    # Rule 2: Title keyword match
    for pattern in _get_title_patterns():
        if pattern.search(title):
            return True

    # Rule 3: Description keyword match (only if description provided)
    if description:
        for pattern in _get_description_patterns():
            if pattern.search(description):
                return True

    return False


def is_excluded(title: str) -> bool:
    """
    Return True if the title contains an excluded term.
    Convenience function for sources that only have a title.
    """
    for pattern in _get_exclude_patterns():
        if pattern.search(title):
            return True
    return False
