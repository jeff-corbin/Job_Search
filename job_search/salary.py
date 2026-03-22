"""
salary.py
=========
Handles everything salary-related:
  1. Fetching job detail pages to find advertised salary
  2. Estimating salary via AI (Gemini free tier or Claude) when not advertised
  3. Evaluating whether a salary range is worth your time

WHY FETCH THE DETAIL PAGE?
  Search result cards almost never include salary. The actual pay range is
  on the individual job posting page. We visit each job URL and look for
  salary patterns in the full page text before falling back to AI estimation.

AI PRIORITY ORDER:
  1. Gemini (free tier — 15 req/min, 1,500/day) — used if GEMINI_API_KEY set
  2. Claude  (paid, ~$0.01/week for this use case) — used if ANTHROPIC_API_KEY set
  3. Neither set → "Not available" noted in report

RATE LIMIT HANDLING:
  If Gemini's 15 req/min limit is hit, we wait 65 seconds and retry.
  You'll get the salary info — it just takes a bit longer.

SALARY RANGE EVALUATION:
  Every job gets a salary band label shown in the email:
    ✓ Strong   — low end >= $100k  (both ends comfortably in range)
    ~ Review   — low end < $100k but average >= $100k (worth a look)
    ✗ Low      — average < $100k
    ? Unknown  — no salary found and AI unavailable
  You'll always see the job — the label just helps you skim quickly.

Public API (what main.py calls):
    enrich_salaries(jobs)  ->  list[dict]
"""

import re
import time
import logging

import requests # type: ignore
from bs4 import BeautifulSoup # type: ignore

from config import ANTHROPIC_API_KEY, GEMINI_API_KEY

log = logging.getLogger(__name__)

# Silence noisy third-party loggers from Google's SDK and httpx
# These produce INFO lines like "AFC is enabled" and raw HTTP request logs
# that are not useful in our output
logging.getLogger("google_genai.models").setLevel(logging.WARNING)
logging.getLogger("google_genai").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# ---------------------------------------------------------------------------
# SALARY PARSING
# ---------------------------------------------------------------------------
#
# DOLLAR AMOUNT COMPONENT (reused across patterns):
#   \$\d{1,3}(?:,\d{3})*(?:\.\d+)?
#   Matches: $124,800  $124,800.00  $1,000,000
#   Requires commas for 5+ digit numbers to avoid matching $65 million
#
# SEPARATOR COMPONENT:
#   \s*(?:[-–—to]+|through)\s*
#   Matches: -  –  —  to  through  (with optional spaces)
#
# We try multiple patterns in order of specificity. The first match wins.
# All patterns require the salary to be >= $20,000 to filter out
# funding amounts, stock prices, and other non-salary dollar figures.

_DOLLAR = r'\$(\d{1,3}(?:,\d{3})+(?:\.\d+)?)'   # captures amount string
_SEP    = r'\s*(?:[-–—]+|(?:\s+to\s+))\s*'       # range separator

# Pattern 1: Keyword BEFORE dollar — "Pay range: $X - $Y" / "salary: $X"
# Allows up to 150 chars between keyword and dollar for verbose job descriptions
_PAT_KEYWORD_BEFORE = re.compile(
    r'(?:pay\s*range|salary\s*range|base\s*salary|annual\s*salary|'
    r'annual\s*base|compensation\s*range|salary|pay|compensation|'
    r'earns?\s+between|range\s+is|range\s+for)'
    r'[^$]{0,150}' + _DOLLAR + r'(?:' + _SEP + _DOLLAR + r')?',
    re.IGNORECASE
)

# Pattern 2: Keyword AFTER dollar — "between $X and $Y USD"
# Catches "is between: $159,000—$218,900 USD"
_PAT_KEYWORD_AFTER = re.compile(
    r'(?:between|from)\s+' + _DOLLAR + _SEP + _DOLLAR,
    re.IGNORECASE
)

# Pattern 3: Bare range — "$X - $Y" with no keyword needed
# Only used when both values look like plausible salaries (>$20k)
_PAT_BARE_RANGE = re.compile(
    _DOLLAR + _SEP + _DOLLAR,
    re.IGNORECASE
)

# Pattern 4: "earns between $X-$Y" or "earns $X to $Y"
_PAT_EARNS = re.compile(
    r'earns?\s+(?:between\s+)?' + _DOLLAR + _SEP + _DOLLAR,
    re.IGNORECASE
)


def _clean_amount(s: str) -> int:
    """Convert '$89,200.00' or '89,200.00' → 89200."""
    return int(re.sub(r'[^\d]', '', s.split('.')[0]))


def _is_plausible_salary(low: int, high: int) -> bool:
    """
    Return True if the values look like real salaries.
    Filters out funding amounts ($65M), stock prices, contract values, etc.
    """
    return (
        20_000 <= low <= 2_000_000 and
        20_000 <= high <= 2_000_000 and
        low <= high and
        high <= low * 10    # high shouldn't be 10x the low (catches weird matches)
    )


def parse_salary_from_text(text: str) -> tuple[str | None, int | None, int | None]:
    """
    Extract salary range from text using multiple patterns.
    Returns (display_string, low_int, high_int) or (None, None, None).

    Tries patterns in order of specificity — most specific first.
    Returns on the first valid plausible match.
    """
    if not text:
        return None, None, None

    for pattern in [_PAT_EARNS, _PAT_KEYWORD_BEFORE, _PAT_KEYWORD_AFTER, _PAT_BARE_RANGE]:
        for match in pattern.finditer(text):
            groups = [g for g in match.groups() if g is not None]
            if len(groups) >= 2:
                low_str, high_str = groups[0], groups[1]
                low, high         = _clean_amount(low_str), _clean_amount(high_str)
                if _is_plausible_salary(low, high):
                    return f"${low_str} – ${high_str}", low, high
            elif len(groups) == 1:
                low_str = groups[0]
                low     = _clean_amount(low_str)
                if 20_000 <= low <= 2_000_000:
                    return f"${low_str}", low, low

    return None, None, None


def evaluate_salary_band(low: int | None, high: int | None) -> str:
    """
    Return a quick-skim label for the email based on the salary range.

    Rules (all based on your stated preference for 6-figure roles):
      ✓ Strong  — low end >= $100k
      ~ Review  — low < $100k but midpoint >= $100k (e.g. $89k–$208k)
      ✗ Low     — midpoint < $100k
      ? Unknown — no salary data available
    """
    if low is None or high is None:
        return "? Unknown"
    midpoint = (low + high) / 2
    if low >= 100_000:
        return "✓ Strong"
    elif midpoint >= 100_000:
        return "~ Review"
    else:
        return "✗ Low"


# ---------------------------------------------------------------------------
# DETAIL PAGE FETCHING
# ---------------------------------------------------------------------------

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
}


def _fetch_salary_from_page(url: str, job: dict | None = None) -> tuple[str | None, int | None, int | None]:
    """
    Visit the job's detail page, extract salary, and store description text.

    If a job dict is passed, stores up to 1500 chars of page text on
    job["description_text"] so Gemini gets context about seniority,
    responsibilities, and required tech stack — not just the title.
    """
    if not url:
        return None, None, None
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        text = soup.get_text(" ", strip=True)

        # Store description for AI estimation context
        if job is not None and "description_text" not in job:
            job["description_text"] = text[:1500]

        return parse_salary_from_text(text)
    except requests.RequestException as e:
        log.debug(f"  Could not fetch detail page {url}: {e}")
        return None, None, None


# ---------------------------------------------------------------------------
# AI SALARY ESTIMATION
# ---------------------------------------------------------------------------

# Module-level rate limit state — shared across all calls in a run
# When Gemini says 429, we record when the window resets and wait once
_gemini_rate_limit_until: float = 0.0


def _estimate_with_gemini(job: dict) -> str:
    """
    Use Google Gemini to estimate salary using job title, org, location,
    AND description text for more accurate results.

    Including description context — responsibilities, qualifications, tech stack —
    gives Gemini enough signal to distinguish a senior Intune architect role from
    a junior MDM admin role even when the titles look similar.
    """
    global _gemini_rate_limit_until

    from google import genai
    client = genai.Client(api_key=GEMINI_API_KEY)

    # Build a description snippet — trim to ~800 chars to stay within token budget
    # while still giving meaningful context about seniority and responsibilities
    description = job.get("description_text", "") or ""
    if len(description) > 800:
        description = description[:800] + "..."
    desc_section = f"\nJob description excerpt:\n{description}" if description else ""

    prompt = (
        "You are a compensation data expert. Estimate the annual base salary range "
        "for the following job. Reply with ONLY a dollar range like "
        "'$120,000 – $160,000'. No explanation, no caveats, just the range.\n\n"
        f"Job title:    {job.get('title', '')}\n"
        f"Organization: {job.get('organization', '')}\n"
        f"Location:     {job.get('location', '')}\n"
        f"Remote:       {'Yes' if job.get('remote') else 'No'}"
        f"{desc_section}"
    )

    # If we already know the rate limit window hasn't reset yet, wait now
    wait_needed = _gemini_rate_limit_until - time.time()
    if wait_needed > 0:
        log.info(f"  Gemini rate limit cooldown — waiting {wait_needed:.0f}s...")
        time.sleep(wait_needed + 1)

    try:
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-preview",
            contents=prompt,
        )
        return response.text.strip()

    except Exception as e:
        error_str = str(e).lower()
        if "429" in error_str or "quota" in error_str or "rate" in error_str:
            # Set the reset time — wait 65s from now before next attempt
            _gemini_rate_limit_until = time.time() + 65
            log.warning("  Gemini rate limit hit — next call will wait for window reset")
            # Try once more after waiting
            time.sleep(65)
            try:
                response = client.models.generate_content(
                    model="gemini-3.1-flash-lite-preview",
                    contents=prompt,
                )
                _gemini_rate_limit_until = 0.0   # reset — we're clear now
                return response.text.strip()
            except Exception:
                return "Estimation unavailable (rate limit)"
        else:
            log.warning(f"  Gemini error for '{job['title']}': {e}")
            return "Estimation unavailable"


def _estimate_with_claude(job: dict) -> str:
    """Use Anthropic Claude to estimate salary (paid fallback)."""
    import anthropic # type: ignore
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    description = job.get("description_text", "") or ""
    if len(description) > 800:
        description = description[:800] + "..."
    desc_section = f"\nJob description excerpt:\n{description}" if description else ""

    prompt = (
        "You are a compensation data expert. Estimate the annual base salary range "
        "for the following job. Reply with ONLY a dollar range like "
        "'$120,000 – $160,000'. No explanation, no caveats, just the range.\n\n"
        f"Job title:    {job.get('title', '')}\n"
        f"Organization: {job.get('organization', '')}\n"
        f"Location:     {job.get('location', '')}\n"
        f"Remote:       {'Yes' if job.get('remote') else 'No'}"
        f"{desc_section}"
    )

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=60,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text.strip()
    except Exception as e:
        log.warning(f"  Claude error for '{job.get('title', '')}': {e}")
        return "Estimation unavailable"


def _estimate_salary(job: dict) -> str:
    """
    Estimate salary using whichever AI is configured.
    Gemini (free) takes priority over Claude (paid).
    """
    if GEMINI_API_KEY:
        return _estimate_with_gemini(job)
    elif ANTHROPIC_API_KEY:
        return _estimate_with_claude(job)
    else:
        return "Not available (set GEMINI_API_KEY or ANTHROPIC_API_KEY in .env)"


# ---------------------------------------------------------------------------
# MAIN ENRICHMENT FUNCTION
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# PUBLIC FUNCTION
# ---------------------------------------------------------------------------

def enrich_one_job(job: dict) -> None:
    """
    Enrich a single job dict with salary data. Mutates in place.

    ORDER OF OPERATIONS:
      1. Check salary cache — if we've looked this job up before, use that
      2. Fetch the job's detail page and look for an advertised salary
      3. Fall back to Gemini AI estimation if nothing found on page
      4. Cache the result so we never look it up again

    Adds these fields:
      salary           — display string e.g. "$89,200 – $207,900"
      salary_estimated — True if AI-generated, False if from listing
      salary_low       — integer low end (or None)
      salary_high      — integer high end (or None)
      salary_band      — "✓ Strong" / "~ Review" / "✗ Low" / "? Unknown"
    """
    from state import get_cached_salary, cache_salary

    job_id = job.get("id", "")
    title  = job.get("title", "Unknown")
    log.info(f"  Processing: {title} @ {job.get('organization', '')}")

    # Step 1: Check salary cache — skip ALL network calls if we have it
    cached = get_cached_salary(job_id)
    if cached:
        log.info(f"    Using cached salary: {cached.get('salary', 'N/A')}")
        job.update(cached)
        return

    # Step 2: Try fetching salary from the job's detail page
    # Also stores description_text on the job dict for AI estimation context
    display, low, high = _fetch_salary_from_page(job.get("url", ""), job)

    if display:
        log.info(f"    Found on page: {display}")
        job["salary"]           = display
        job["salary_estimated"] = False
        job["salary_low"]       = low
        job["salary_high"]      = high
    else:
        # Step 3: Fall back to AI estimation
        log.info(f"    Not on page — estimating via AI...")
        estimated               = _estimate_salary(job)
        job["salary"]           = estimated
        job["salary_estimated"] = True
        _, low, high            = parse_salary_from_text(estimated)
        job["salary_low"]       = low
        job["salary_high"]      = high

    # Step 4: Salary band label for quick skimming
    job["salary_band"] = evaluate_salary_band(
        job.get("salary_low"), job.get("salary_high")
    )
    log.info(f"    {job.get('salary', 'N/A')}  [{job['salary_band']}]")

    # Step 5: Cache result so next run skips the lookup entirely
    cache_salary(job_id, job)
