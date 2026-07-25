"""
salary.py
=========
Salary extraction and AI estimation via Gemini.
Thresholds live in config.py.
"""

import re
import json
import time
import logging

import requests  # type: ignore
from bs4 import BeautifulSoup  # type: ignore

from config import GEMINI_API_KEY, SALARY_STRONG_MIN, SALARY_REVIEW_AVG, GEMINI_BATCH_SIZE

log = logging.getLogger(__name__)

# Silence noisy Google SDK loggers
logging.getLogger("google_genai.models").setLevel(logging.WARNING)
logging.getLogger("google_genai").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)

# ---------------------------------------------------------------------------
# SALARY PARSING
# ---------------------------------------------------------------------------

_DOLLAR = r'\$(\d{1,3}(?:,\d{3})+(?:\.\d+)?)'
_SEP    = r'\s*(?:[-–—]+|(?:\s+to\s+))\s*'

_PAT_KEYWORD_BEFORE = re.compile(
    r'(?:pay\s*range|salary\s*range|base\s*salary|annual\s*salary|'
    r'annual\s*base|compensation\s*range|salary|pay|compensation|'
    r'earns?\s+between|range\s+is|range\s+for)'
    r'[^$]{0,150}' + _DOLLAR + r'(?:' + _SEP + _DOLLAR + r')?',
    re.IGNORECASE
)
_PAT_KEYWORD_AFTER = re.compile(
    r'(?:between|from)\s+' + _DOLLAR + _SEP + _DOLLAR,
    re.IGNORECASE
)
_PAT_BARE_RANGE = re.compile(_DOLLAR + _SEP + _DOLLAR, re.IGNORECASE)
_PAT_EARNS      = re.compile(
    r'earns?\s+(?:between\s+)?' + _DOLLAR + _SEP + _DOLLAR,
    re.IGNORECASE
)


def _clean_amount(s: str) -> int:
    return int(re.sub(r'[^\d]', '', s.split('.')[0]))


def _is_plausible_salary(low: int, high: int) -> bool:
    return (
        20_000 <= low  <= 2_000_000 and
        20_000 <= high <= 2_000_000 and
        low <= high and
        high <= low * 10
    )


def parse_salary_from_text(text: str) -> tuple[str | None, int | None, int | None]:
    """Pull a salary range out of raw text. Returns (display, low, high) or (None, None, None)."""
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
    Returns a band label based on thresholds in config.py:
      ✓ Strong  — low end >= SALARY_STRONG_MIN
      ~ Review  — avg >= SALARY_REVIEW_AVG
      ✗ Low     — below review threshold
      ? Unknown — no data
    """
    if low is None or high is None:
        return "? Unknown"
    avg = (low + high) / 2
    if low >= SALARY_STRONG_MIN:
        return "✓ Strong"
    elif avg >= SALARY_REVIEW_AVG:
        return "~ Review"
    else:
        return "✗ Low"

# ---------------------------------------------------------------------------
# DETAIL PAGE FETCH
# ---------------------------------------------------------------------------

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/122.0.0.0 Safari/537.36"
    ),
}


def _fetch_salary_from_page(url: str, job: dict | None = None) -> tuple[str | None, int | None, int | None]:
    """Hit the job's detail page and parse salary. Stashes description text on job dict for AI context."""
    if not url:
        return None, None, None
    try:
        response = requests.get(url, headers=_HEADERS, timeout=15)
        response.raise_for_status()
        text = BeautifulSoup(response.text, "html.parser").get_text(" ", strip=True)
        if job is not None:
            job["description_text"] = text[:1500]
        return parse_salary_from_text(text)
    except requests.RequestException as e:
        log.debug(f"  Detail page fetch failed {url}: {e}")
        return None, None, None


def try_salary_from_page(job: dict) -> bool:
    """
    Attempt to find a listed salary on the job's own detail page.
    On success, sets salary/salary_estimated/salary_low/salary_high/
    salary_band on the job dict and returns True.
    On failure, stashes description_text (if any) for later Gemini
    batching and returns False — caller is responsible for running the
    job through estimate_salaries_batch() afterward.
    """
    title = job.get("title", "Unknown")
    log.info(f"  Checking page for salary: {title} @ {job.get('organization', '')}")

    display, low, high = _fetch_salary_from_page(job.get("url", ""), job)

    if not display:
        return False

    log.info(f"    Found on page: {display}")
    job["salary"]           = display
    job["salary_estimated"] = False
    job["salary_low"]       = low
    job["salary_high"]      = high
    job["salary_band"]      = evaluate_salary_band(low, high)
    return True

# ---------------------------------------------------------------------------
# GEMINI ESTIMATION — single job (kept for manual/one-off use)
# ---------------------------------------------------------------------------

_gemini_rate_limit_until: float = 0.0


def _estimate_with_gemini(job: dict) -> str:
    """Ask Gemini to estimate salary for ONE job. Handles 429 with a single retry."""
    global _gemini_rate_limit_until

    from google import genai
    client = genai.Client(api_key=GEMINI_API_KEY)

    description = (job.get("description_text", "") or "")[:800]
    if len(job.get("description_text", "") or "") > 800:
        description += "..."
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

    wait = _gemini_rate_limit_until - time.time()
    if wait > 0:
        log.info(f"  Gemini rate limit — waiting {wait:.0f}s...")
        time.sleep(wait + 1)

    try:
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-preview",
            contents=prompt,
        )
        return response.text.strip()
    except Exception as e:
        err = str(e).lower()
        if "429" in err or "quota" in err or "rate" in err:
            _gemini_rate_limit_until = time.time() + 65
            log.warning("  Gemini rate limit hit — retrying in 65s")
            time.sleep(65)
            try:
                response = client.models.generate_content(
                    model="gemini-3.1-flash-lite-preview",
                    contents=prompt,
                )
                _gemini_rate_limit_until = 0.0
                return response.text.strip()
            except Exception:
                return "Estimation unavailable (rate limit)"
        log.warning(f"  Gemini error for '{job['title']}': {e}")
        return "Estimation unavailable"


def enrich_one_job(job: dict) -> None:
    """
    Adds salary fields to job dict in place, ONE job at a time.
    Tries the detail page first, falls back to Gemini.

    Kept for single-job/manual use. main.py uses the batched path
    (try_salary_from_page() + estimate_salaries_batch()) instead, to
    avoid one-Gemini-call-per-job rate limiting.

    Adds: salary, salary_estimated, salary_low, salary_high, salary_band
    """
    if try_salary_from_page(job):
        return

    if GEMINI_API_KEY:
        log.info("    Not on page — asking Gemini...")
        estimated = _estimate_with_gemini(job)
    else:
        estimated = "Not available (GEMINI_API_KEY not set)"

    job["salary"]           = estimated
    job["salary_estimated"] = True
    _, low, high            = parse_salary_from_text(estimated)
    job["salary_low"]       = low
    job["salary_high"]      = high
    job["salary_band"]      = evaluate_salary_band(low, high)
    log.info(f"    {job.get('salary', 'N/A')}  [{job['salary_band']}]")

# ---------------------------------------------------------------------------
# GEMINI ESTIMATION — batched (main.py uses this)
# ---------------------------------------------------------------------------

def _build_batch_prompt(chunk: list[dict]) -> str:
    """Build one prompt covering many jobs, asking for a JSON array matched by index."""
    job_entries = []
    for i, job in enumerate(chunk):
        desc = (job.get("description_text", "") or "")[:500]
        if len(job.get("description_text", "") or "") > 500:
            desc += "..."
        job_entries.append({
            "index":               i,
            "title":               job.get("title", ""),
            "organization":        job.get("organization", ""),
            "location":            job.get("location", ""),
            "remote":              bool(job.get("remote")),
            "description_excerpt": desc,
        })

    jobs_json = json.dumps(job_entries, indent=2)

    return (
        "You are a compensation data expert. For EACH job in the JSON array below, "
        "estimate its annual base salary range.\n\n"
        "Reply with ONLY a JSON array, one object per job, in exactly this shape:\n"
        '[{"index": 0, "salary": "$120,000 - $160,000"}, {"index": 1, "salary": "$95,000 - $130,000"}]\n\n'
        "Rules:\n"
        "- No explanation, no markdown code fences, no extra keys — just the JSON array.\n"
        "- Every job below must have exactly one corresponding object in your output, matched by \"index\".\n"
        "- \"salary\" must always be a plain dollar-range string, never null or a caveat.\n\n"
        f"Jobs:\n{jobs_json}"
    )


def _parse_batch_response(text: str, expected: int) -> dict[int, str]:
    """Parse Gemini's JSON array response into {index: salary_string}."""
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
    cleaned = re.sub(r"\s*```$", "", cleaned)

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as e:
        log.warning(f"  Could not parse Gemini batch JSON: {e}")
        return {}

    if not isinstance(parsed, list):
        log.warning("  Gemini batch response was not a JSON array")
        return {}

    results: dict[int, str] = {}
    for entry in parsed:
        if not isinstance(entry, dict):
            continue
        idx    = entry.get("index")
        salary = entry.get("salary")
        if isinstance(idx, int) and isinstance(salary, str):
            results[idx] = salary

    if len(results) != expected:
        log.warning(f"  Gemini batch returned {len(results)} of {expected} expected entries")

    return results


def _estimate_batch_with_gemini(chunk: list[dict]) -> None:
    """One Gemini call for a whole chunk of jobs. Mutates each job dict in place."""
    global _gemini_rate_limit_until

    from google import genai
    client = genai.Client(api_key=GEMINI_API_KEY)

    prompt = _build_batch_prompt(chunk)

    wait = _gemini_rate_limit_until - time.time()
    if wait > 0:
        log.info(f"  Gemini rate limit — waiting {wait:.0f}s...")
        time.sleep(wait + 1)

    response_text: str | None = None
    try:
        response = client.models.generate_content(
            model="gemini-3.1-flash-lite-preview",
            contents=prompt,
        )
        response_text = response.text
    except Exception as e:
        err = str(e).lower()
        if "429" in err or "quota" in err or "rate" in err:
            _gemini_rate_limit_until = time.time() + 65
            log.warning("  Gemini rate limit hit on batch — retrying once in 65s")
            time.sleep(65)
            try:
                response = client.models.generate_content(
                    model="gemini-3.1-flash-lite-preview",
                    contents=prompt,
                )
                _gemini_rate_limit_until = 0.0
                response_text = response.text
            except Exception as e2:
                log.warning(f"  Gemini batch retry failed: {e2}")
        else:
            log.warning(f"  Gemini batch error: {e}")

    results_by_index = _parse_batch_response(response_text, len(chunk)) if response_text else {}

    for i, job in enumerate(chunk):
        estimated = results_by_index.get(i, "Estimation unavailable")
        job["salary"]           = estimated
        job["salary_estimated"] = True
        _, low, high            = parse_salary_from_text(estimated)
        job["salary_low"]       = low
        job["salary_high"]      = high
        job["salary_band"]      = evaluate_salary_band(low, high)
        log.info(f"    {job.get('title', '')}: {estimated}  [{job['salary_band']}]")


def estimate_salaries_batch(jobs: list[dict], batch_size: int = GEMINI_BATCH_SIZE) -> None:
    """
    Estimate salaries for many jobs at once via Gemini, chunked into
    batches of `batch_size` (default from config.GEMINI_BATCH_SIZE) —
    one API call per chunk instead of one call per job.

    Only pass jobs that already went through try_salary_from_page() and
    came up empty — this is purely the Gemini-fallback step. Mutates
    each job dict in place: salary, salary_estimated, salary_low,
    salary_high, salary_band.
    """
    if not jobs:
        return

    if not GEMINI_API_KEY:
        for job in jobs:
            job["salary"]           = "Not available (GEMINI_API_KEY not set)"
            job["salary_estimated"] = True
            job["salary_low"]       = None
            job["salary_high"]      = None
            job["salary_band"]      = evaluate_salary_band(None, None)
        return

    total = len(jobs)
    for start in range(0, total, batch_size):
        chunk = jobs[start:start + batch_size]
        log.info(f"  Gemini batch: estimating {len(chunk)} job(s) "
                 f"({start + 1}-{start + len(chunk)} of {total})")
        _estimate_batch_with_gemini(chunk)

        if start + batch_size < total:
            time.sleep(2)  # polite pause between batches