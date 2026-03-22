# Sports IT Job Monitor

Monitors **TeamWork Online** for DevOps, SysAdmin, IT Manager, and related roles
at MLB, NBA, NFL, and NHL teams. Runs on a cron job and emails a weekly summary
with title, organization, location, remote status, and salary (or an AI estimate
if the listing doesn't include one).

---

## Project Structure

```
sports_jobs/
├── __init__.py     # empty — marks the folder as a Python package
├── config.py       # all env vars and constants (edit here or set as env vars)
├── main.py         # orchestrator — this is what cron calls
├── scraper.py      # fetches and filters listings from TeamWork Online
├── state.py        # reads/writes seen_jobs.json to track already-reported jobs
├── salary.py       # estimates pay via Claude API for listings without salary
└── emailer.py      # builds plain-text + HTML report and delivers via SMTP
```

---

## Quick Start

### 1. Install dependencies

```bash
pip install requests beautifulsoup4 anthropic
```

### 2. Set environment variables

```bash
export ANTHROPIC_API_KEY="sk-ant-..."       # for salary estimation
export EMAIL_TO="you@gmail.com"
export EMAIL_FROM="sender@gmail.com"
export EMAIL_PASSWORD="your-app-password"   # Gmail: use an App Password
```

> **Gmail App Password**: myaccount.google.com → Security → 2-Step Verification → App Passwords

### 3. Run it

```bash
# From the parent directory of sports_jobs/
python3 sports_jobs/main.py
```

---

## Cron Setup (Ubuntu)

```bash
crontab -e
```

Add this line to run every Monday at 8am:

```
0 8 * * 1 /usr/bin/python3 /path/to/sports_jobs/main.py >> /var/log/sports_jobs.log 2>&1
```

Cron doesn't load your shell profile, so either set env vars in `/etc/environment`
or inline them in the cron entry:

```
0 8 * * 1 ANTHROPIC_API_KEY=sk-ant-... EMAIL_TO=you@gmail.com /usr/bin/python3 /path/to/sports_jobs/main.py >> /var/log/sports_jobs.log 2>&1
```

---

## What Each Step Does

| Step | File | Description |
|------|------|-------------|
| 1 | `scraper.py` | Fetches IT/DevOps listings from TeamWork Online for all 4 leagues |
| 2 | `state.py` | Loads seen job IDs; filters to only new listings |
| 3 | `salary.py` | Calls Claude API to estimate pay for listings without salary info |
| 4 | `emailer.py` | Builds HTML + plain-text email and delivers via SMTP |
| 5 | `state.py` | Saves updated seen IDs so next run skips current listings |

---

## Customization

All settings are in `config.py`:

| Variable | What it controls |
|----------|-----------------|
| `TITLE_KEYWORDS` | Role keywords to match — add/remove freely |
| `SEARCH_URLS` | TeamWork Online search URLs per league |
| `STATE_FILE` | Path to the JSON file tracking seen job IDs |

---

## Testing Individual Modules

Because each module has a clear single responsibility, you can test them in isolation:

```bash
# Test salary estimation alone
python3 -c "
from sports_jobs.salary import _estimate_salary
fake_job = {'title': 'DevOps Engineer', 'organization': 'Chicago Cubs', 'league': 'MLB', 'location': 'Chicago, IL', 'remote': False}
print(_estimate_salary(fake_job))
"

# Inspect the state file
python3 -c "from sports_jobs.state import load_seen_ids; print(load_seen_ids())"
```

---

## PowerShell → Python Quick Reference

| PowerShell | Python (used in this project) |
|---|---|
| `Invoke-WebRequest` | `requests.get()` in `scraper.py` |
| `Select-String` / `-match` | `re.search()` in `scraper.py` |
| `ConvertTo-Json` / `Set-Content` | `json.dump()` in `state.py` |
| `ConvertFrom-Json` / `Get-Content` | `json.load()` in `state.py` |
| `Send-MailMessage` | `smtplib.SMTP` in `emailer.py` |
| `Write-Host` | `logging.info()` everywhere |
| `$env:VARIABLE` | `os.getenv("VARIABLE")` in `config.py` |
| `try/catch` | `try/except` everywhere |
| `function Invoke-X {}` | `def run():` in `main.py` |
| dot-sourcing `. ./helpers.ps1` | `from scraper import fetch_all_jobs` |
