# IT Job Monitor

Scrapes Greenhouse and Workday job boards for IT/DevOps/Cloud/Endpoint roles, estimates salary via Gemini for listings that don't post one, and emails you a weekly summary. Low-paying jobs are filtered out before the email is built.

---

## Project Structure

```
job_search/
├── main.py          # pipeline orchestrator — this is what cron calls
├── config.py        # all constants, env vars, keyword lists
├── vault_client.py  # pulls secrets (Gemini key, email password) from Vault
├── greenhouse.py    # Greenhouse public API fetcher
├── workday.py       # Workday Playwright scraper
├── keywords.py      # shared keyword matching logic
├── location.py      # location classification and filtering
├── salary.py        # salary parsing and Gemini estimation
├── emailer.py       # builds and sends the HTML/plain-text email
└── state.py         # tracks seen job IDs between runs (seen_jobs.json)
```

---

## Setup

### 1. Install dependencies

```bash
pip install requests beautifulsoup4 python-dotenv playwright google-genai
playwright install chromium
playwright install-deps   # Linux only
```

### 2. Set up Vault

Secrets are pulled from HashiCorp Vault at `kv/data/projects/job-search`.

Required keys in Vault:
- `gemini_api_key` — Google Gemini API key (free tier works)
- `gmail_app_pw` — Gmail App Password

Get a Gmail App Password: myaccount.google.com → Security → 2-Step Verification → App Passwords

### 3. Create a .env file

```
VAULT_ADDR=http://your-vault-server:8200
VAULT_ROLE_ID=your-approle-role-id
VAULT_SECRET_ID=your-approle-secret-id
EMAIL_TO=you@gmail.com
EMAIL_FROM=sender@gmail.com
```

### 4. Run it

```bash
python main.py
```

---

## Salary Thresholds

Thresholds live in `config.py` — change them there, not in salary.py.

| Band | Condition | Shown in email? |
|---|---|---|
| ✓ Strong | Low end ≥ $130k | Yes |
| ~ Review | Avg ≥ $120k | Yes |
| ✗ Low | Below review threshold | No — tracked but filtered |
| ? Unknown | No salary data | Yes |

---

## Adding Job Sources

### Greenhouse

Greenhouse has a free public API. Find a token:
1. Go to the company's careers page
2. Click any job listing
3. Look for `greenhouse.io/TOKEN` in the URL
4. Verify it works: `https://boards-api.greenhouse.io/v1/boards/TOKEN/jobs`
5. Add to `GREENHOUSE_COMPANIES` in `config.py`

### Workday

1. Go to the company's careers page
2. Click any job listing
3. Look for `myworkdayjobs.com` in the URL
4. Pull the tenant and board name from the URL pattern:
   `https://{tenant}.wd{N}.myworkdayjobs.com/en-US/{board}/jobs`
5. Add to `WORKDAY_COMPANIES` in `config.py`

---

## Cron Setup (Ubuntu)

```bash
crontab -e
```

Run every Monday at 8am:
```
0 8 * * 1 /usr/bin/python3 /path/to/job_search/main.py >> /var/log/job_search.log 2>&1
```

Cron doesn't load your shell profile. Either set env vars in `/etc/environment` or use a wrapper script that loads your `.env` before calling python.

---

## Keyword Tuning

Three lists in `config.py` control what gets surfaced:

| List | Purpose |
|---|---|
| `TITLE_KEYWORDS` | Job title must match at least one |
| `DESCRIPTION_KEYWORDS` | Used when full description is available (Greenhouse, Workday) |
| `TITLE_EXCLUDE` | Hard drop — title matches any of these = skip |
| `SEARCH_KEYWORDS` | What gets typed into each site's search box |

Matching uses word boundaries — `"it manager"` won't match `"credit manager"` and `"uem"` won't match `"requirement"`. See `keywords.py` for details.