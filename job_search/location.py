"""
location.py
===========
Classifies job locations and filters out jobs outside the US, Canada, or Mexico.

TIERS (for jobs that pass the filter):
  ✓ US       — confirmed US location (or explicitly US remote)
  ~ Canada   — Canadian location
  ~ Mexico   — Mexican location (border cities and beyond)
  ~ Remote   — "Remote" with no specific country identified
  ? Unknown  — couldn't determine location (kept — better to show than miss)

FILTER BEHAVIOR:
  Jobs confirmed to be in other countries (India, UK, Germany, etc.)
  are REMOVED from the list entirely — they won't appear in the email.
  Jobs with unknown or ambiguous locations are KEPT — better to show
  something borderline than silently drop a real opportunity.

Public API (what main.py calls):
    enrich_locations(jobs)  ->  list[dict]
        Classifies each job and returns only jobs that pass the location filter.
        Adds "location_tier" to each kept job.
"""

import re
import logging

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# US STATE ABBREVIATIONS AND NAMES
# ---------------------------------------------------------------------------

US_STATES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC", "PR", "GU", "VI",   # territories
}

US_STATE_NAMES = {
    "alabama", "alaska", "arizona", "arkansas", "california", "colorado",
    "connecticut", "delaware", "florida", "georgia", "hawaii", "idaho",
    "illinois", "indiana", "iowa", "kansas", "kentucky", "louisiana",
    "maine", "maryland", "massachusetts", "michigan", "minnesota",
    "mississippi", "missouri", "montana", "nebraska", "nevada",
    "new hampshire", "new jersey", "new mexico", "new york",
    "north carolina", "north dakota", "ohio", "oklahoma", "oregon",
    "pennsylvania", "rhode island", "south carolina", "south dakota",
    "tennessee", "texas", "utah", "vermont", "virginia", "washington",
    "west virginia", "wisconsin", "wyoming", "district of columbia",
}

# Well-known US cities — covers most of what you'll see in job listings
US_CITIES = {
    "new york", "los angeles", "chicago", "houston", "phoenix",
    "philadelphia", "san antonio", "san diego", "dallas", "san jose",
    "austin", "jacksonville", "fort worth", "columbus", "charlotte",
    "indianapolis", "san francisco", "seattle", "denver", "nashville",
    "oklahoma city", "el paso", "washington", "boston", "portland",
    "las vegas", "memphis", "louisville", "baltimore", "milwaukee",
    "albuquerque", "tucson", "fresno", "sacramento", "kansas city",
    "mesa", "atlanta", "omaha", "colorado springs", "raleigh",
    "long beach", "virginia beach", "minneapolis", "tampa", "new orleans",
    "arlington", "bakersfield", "honolulu", "anaheim", "aurora",
    "santa ana", "corpus christi", "riverside", "st. louis", "lexington",
    "pittsburgh", "anchorage", "stockton", "cincinnati", "st. paul",
    "toledo", "greensboro", "newark", "plano", "henderson", "lincoln",
    "buffalo", "fort wayne", "jersey city", "chula vista", "orlando",
    "st. petersburg", "norfolk", "chandler", "laredo", "madison",
    "durham", "lubbock", "winston-salem", "garland", "glendale",
    "hialeah", "reno", "baton rouge", "irvine", "chesapeake",
    "scottsdale", "north las vegas", "fremont", "gilbert", "san bernardino",
    "birmingham", "rochester", "richmond", "spokane", "des moines",
    "montgomery", "modesto", "fayetteville", "tacoma", "shreveport",
    "salt lake city", "oxnard", "akron", "yonkers", "huntington beach",
    "grand rapids", "moreno valley", "glendale", "aurora", "fontana",
    "knoxville", "providence", "little rock", "oceanside", "garden grove",
    "chattanooga", "tempe", "cape coral", "worcester", "fort lauderdale",
    "brownsville", "santa clarita", "rancho cucamonga", "peoria",
    "overland park", "fort collins", "tallahassee", "springfield",
    "hartford", "clarksville", "lakewood", "vancouver", "worcester",
    "sunnyvale", "torrance", "bridgeport", "pasadena", "mc allen",
    "paterson", "santa rosa", "pomona", "hayward", "frisco",
    "mesquite", "roseville", "escondido", "kansas city", "naperville",
    "sunnyvale", "bellevue", "metairie", "macon", "mobile", "savannah",
    "rockford", "alexandria", "elizabeth", "columbia", "joliet",
    "syracuse", "pasadena", "jackson", "hollywood", "palmdale",
    "salinas", "springfield", "fort smith", "pembroke pines",
    "eugene", "corona", "cary", "lansing", "south bend",
    "thousand oaks", "athens", "sioux falls", "chattanooga",
}

# ---------------------------------------------------------------------------
# CANADA — kept, labeled ~ Canada
# ---------------------------------------------------------------------------

CANADA_CITIES = {
    "vancouver", "surrey", "burnaby", "richmond", "abbotsford", "kelowna",
    "victoria", "toronto", "mississauga", "brampton", "hamilton", "ottawa",
    "st. catharines", "windsor", "sarnia", "niagara falls", "kingston",
    "london", "kitchener", "waterloo", "barrie", "sudbury", "thunder bay",
    "montreal", "laval", "longueuil", "quebec city", "gatineau",
    "calgary", "edmonton", "red deer", "lethbridge", "medicine hat",
    "winnipeg", "saskatoon", "regina", "halifax", "moncton", "fredericton",
    "saint john", "charlottetown", "st. john's",
}

CANADA_PROVINCES = {
    "british columbia", "ontario", "quebec", "alberta", "manitoba",
    "saskatchewan", "nova scotia", "new brunswick", "prince edward island",
    "newfoundland", "northwest territories", "yukon", "nunavut",
    # Common abbreviations
    "bc", "ab", "mb", "sk", "on", "qc", "ns", "nb", "pe", "nl",
}

CANADA_INDICATORS = CANADA_CITIES | CANADA_PROVINCES | {"canada", "canadian"}

# ---------------------------------------------------------------------------
# MEXICO — kept, labeled ~ Mexico
# ---------------------------------------------------------------------------

MEXICO_CITIES = {
    "tijuana", "mexicali", "ciudad juarez", "juarez", "nogales",
    "nuevo laredo", "reynosa", "matamoros", "monterrey", "guadalajara",
    "mexico city", "cdmx", "puebla", "cancun", "queretaro", "leon",
    "san luis potosi", "merida", "aguascalientes", "chihuahua",
    "hermosillo", "culiacan", "acapulco", "veracruz", "oaxaca",
}

MEXICO_INDICATORS = MEXICO_CITIES | {"mexico", "mexican", "mx"}

# ---------------------------------------------------------------------------
# FILTERED OUT — not US, Canada, or Mexico
# Jobs with any of these are removed entirely from results
# ---------------------------------------------------------------------------

FILTERED_COUNTRIES = {
    # Asia
    "india", "bangalore", "bengaluru", "mumbai", "hyderabad", "chennai",
    "pune", "kolkata", "delhi", "noida", "gurgaon", "gurugram", "ahmedabad",
    "japan", "tokyo", "osaka", "china", "beijing", "shanghai", "shenzhen",
    "singapore", "philippines", "manila", "vietnam", "ho chi minh",
    "thailand", "bangkok", "malaysia", "kuala lumpur", "indonesia", "jakarta",
    "south korea", "seoul", "taiwan", "taipei", "pakistan", "bangladesh",
    "sri lanka", "nepal",

    # Europe
    "united kingdom", "england", "london", "manchester", "birmingham",
    "edinburgh", "glasgow", "leeds", "bristol", "scotland", "wales",
    "ireland", "dublin", "germany", "berlin", "munich", "frankfurt",
    "hamburg", "cologne", "france", "paris", "lyon", "marseille",
    "netherlands", "amsterdam", "rotterdam", "belgium", "brussels",
    "switzerland", "zurich", "geneva", "austria", "vienna", "sweden",
    "stockholm", "norway", "oslo", "denmark", "copenhagen", "finland",
    "helsinki", "poland", "warsaw", "krakow", "czech republic", "prague",
    "hungary", "budapest", "romania", "bucharest", "bulgaria", "sofia",
    "portugal", "lisbon", "spain", "madrid", "barcelona", "italy",
    "rome", "milan", "ukraine", "kyiv", "greece", "athens",
    "croatia", "zagreb", "serbia", "belgrade", "slovakia", "bratislava",
    "luxembourg", "estonia", "latvia", "lithuania",

    # Middle East / Africa
    "israel", "tel aviv", "uae", "dubai", "abu dhabi", "saudi arabia",
    "riyadh", "qatar", "doha", "kuwait", "bahrain", "egypt", "cairo",
    "nigeria", "lagos", "south africa", "johannesburg", "cape town",
    "kenya", "nairobi",

    # Oceania
    "australia", "sydney", "melbourne", "brisbane", "perth", "adelaide",
    "new zealand", "auckland",

    # Latin America (non-Mexico)
    "brazil", "sao paulo", "rio de janeiro", "brasilia",
    "argentina", "buenos aires", "colombia", "bogota", "chile", "santiago",
    "peru", "lima", "venezuela", "ecuador", "costa rica", "panama",
}


def classify_location(location: str, is_remote: bool = False) -> str | None:
    """
    Classify a location string. Returns a tier label or None if filtered out.

    None means the job should be excluded from results entirely.

    Check order:
      1. Explicitly filtered countries → None (excluded)
      2. Canada indicators → ~ Canada
      3. Mexico indicators → ~ Mexico
      4. Remote keywords → ~ Remote
      5. US state/city indicators → ✓ US
      6. "N Locations" / ambiguous → ✓ US (assume US for domestic job boards)
      7. Empty/unknown → ? Unknown (kept — don't silently drop)
    """
    if not location or location.strip() in ("Not specified", ""):
        if is_remote:
            return "~ Remote"
        return "? Unknown"

    loc_lower = location.lower().strip()

    # Step 1: Check filtered countries first — hard exclude
    if any(indicator in loc_lower for indicator in FILTERED_COUNTRIES):
        return None     # caller should drop this job

    # Step 2: Canada
    if any(indicator in loc_lower for indicator in CANADA_INDICATORS):
        return "~ Canada"

    # Step 3: Mexico
    if any(indicator in loc_lower for indicator in MEXICO_INDICATORS):
        return "~ Mexico"

    # Step 4: Remote
    if is_remote or any(w in loc_lower for w in ["remote", "work from home", "wfh"]):
        return "~ Remote"

    # Step 5: US state abbreviation — look for ", XX" pattern (e.g. "Dallas, TX")
    state_match = re.search(r'\b([A-Z]{2})\b', location)
    if state_match and state_match.group(1) in US_STATES:
        return "✓ US"

    # Step 6: US state name
    if any(state in loc_lower for state in US_STATE_NAMES):
        return "✓ US"

    # Step 7: US city name
    if any(city in loc_lower for city in US_CITIES):
        return "✓ US"

    # Step 8: Workday "N Locations" or "Multiple Locations" — assume US
    if re.search(r'\d+\s+location', loc_lower) or "multiple" in loc_lower:
        return "✓ US"

    # Step 9: Explicitly stated USA
    if any(x in loc_lower for x in ["usa", "united states", "u.s.", "u.s.a"]):
        return "✓ US"

    # Default: assume US — better to show a mislabeled foreign job than
    # silently drop a real domestic opportunity
    return "✓ US"


def enrich_locations(jobs: list[dict]) -> list[dict]:
    """
    Classify each job's location, filter out non-US/Canada/Mexico jobs,
    and add a "location_tier" field to the ones that pass.

    Returns the filtered list — jobs outside the target regions are removed.
    Logs how many were filtered so you can see what got dropped.
    """
    kept    = []
    dropped = 0

    for job in jobs:
        tier = classify_location(
            job.get("location", ""),
            job.get("remote", False)
        )
        if tier is None:
            log.debug(f"  Filtered (location): {job.get('title')} @ {job.get('location')}")
            dropped += 1
        else:
            job["location_tier"] = tier
            kept.append(job)

    if dropped:
        log.info(f"Location filter: kept {len(kept)}, removed {dropped} non-US/CA/MX jobs.")

    return kept
