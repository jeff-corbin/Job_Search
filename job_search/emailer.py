"""
emailer.py
==========
Builds the weekly job search summary and delivers it via SMTP.

REPORT STRUCTURE:
  - Grouped by company (organization field), not by source/ATS
  - Within each company, jobs sorted by salary high end descending
  - No emojis, no location tier prefixes, no ATS names in headers
  - Salary band shown as color-coded text (Strong / Review / Low / Unknown)
  - Salary marked (est.) if AI-generated, nothing if from listing

Public API (what main.py calls):
    send_report(new_jobs, run_date)  ->  None
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from config import EMAIL_TO, EMAIL_FROM, EMAIL_PASSWORD, SMTP_HOST, SMTP_PORT

log = logging.getLogger(__name__)


def _sort_key(job: dict) -> int:
    """
    Sort key for jobs within a company group — salary high end descending.
    Jobs with no salary data sort to the bottom.
    Negate the value so sorted() puts highest first.
    """
    high = job.get("salary_high")
    return -(high if high is not None else 0)


def _clean_location(job: dict) -> str:
    """
    Return a clean location string — just city/state, no tier prefix.
    Falls back to the raw location field if nothing better is available.
    """
    location = job.get("location", "Not specified")
    # Strip any leading tier labels that may have been left in the string
    for prefix in ["✓ US", "~ Canada", "~ Mexico", "~ Remote", "? Unknown", "✓", "~", "?"]:
        if location.startswith(prefix):
            location = location[len(prefix):].strip()
    return location or "Not specified"


def _build_report(new_jobs: list[dict], run_date: str) -> tuple[str, str]:
    """
    Build plain-text and HTML versions of the weekly summary.

    Grouping logic:
      - Group by job["organization"] (the company name, not the ATS/source)
      - Sort groups alphabetically by company name
      - Within each group, sort by salary_high descending
    """
    if not new_jobs:
        plain = (
            f"IT Job Search Weekly Summary — {run_date}\n"
            + "=" * 55 + "\n\n"
            + "No new matching jobs found this week.\n"
        )
        html = (
            f"<h2>IT Job Search — {run_date}</h2>"
            "<p>No new matching jobs found this week.</p>"
        )
        return plain, html

    # Group by organization (company name)
    by_company: dict[str, list] = {}
    for job in new_jobs:
        org = job.get("organization", "Unknown")
        by_company.setdefault(org, []).append(job)

    # Sort groups alphabetically
    # Sort jobs within each group by salary descending
    for org in by_company:
        by_company[org].sort(key=_sort_key)
    by_company = dict(sorted(by_company.items(), key=lambda x: x[0].lower()))

    total_companies = len(by_company)

    # ── Plain text ────────────────────────────────────────────────────────────
    lines = [
        f"IT Job Search Weekly Summary — {run_date}",
        "=" * 55,
        f"  {len(new_jobs)} new listing(s) across {total_companies} company/companies\n",
    ]

    for org, jobs in by_company.items():
        lines.append(f"\n{'─' * 45}")
        lines.append(f"  {org}  ({len(jobs)} job{'s' if len(jobs) != 1 else ''})")
        lines.append(f"{'─' * 45}")
        for j in jobs:
            salary_note = "  *estimate" if j.get("salary_estimated") else ""
            band        = j.get("salary_band", "")
            location    = _clean_location(j)
            remote_str  = "Remote" if j.get("remote") else "On-site"
            lines += [
                f"\n  Title:    {j['title']}",
                f"  Location: {location}  ({remote_str})",
                f"  Salary:   {band}  {j.get('salary') or 'Not listed'}{salary_note}",
                f"  Link:     {j['url']}",
            ]

    lines += [
        "\n" + "=" * 55,
        "*estimate — salary was not in the listing; estimated by AI.",
        f"Generated {run_date}",
    ]

    plain = "\n".join(lines)

    # ── HTML ─────────────────────────────────────────────────────────────────
    rows_html = ""
    for org, jobs in by_company.items():
        # Company header row
        rows_html += (
            f'<tr><td colspan="4" style="background:#1a1a2e;color:#fff;'
            f'padding:8px 12px;font-weight:bold;font-size:14px;letter-spacing:0.3px;">'
            f'{org}'
            f'<span style="font-weight:normal;font-size:12px;margin-left:8px;opacity:0.75;">'
            f'{len(jobs)} listing{"s" if len(jobs) != 1 else ""}'
            f'</span></td></tr>\n'
        )
        for j in jobs:
            # Salary display
            salary_note = (
                '<span style="font-size:11px;color:#999;margin-left:4px">(est.)</span>'
                if j.get("salary_estimated") else ""
            )
            band       = j.get("salary_band", "")
            band_color = (
                "#2e7d32" if "Strong" in band else
                "#b45309" if "Review" in band else
                "#c62828" if "Low"    in band else
                "#777"
            )
            salary_display = j.get("salary") or "Not listed"

            # Location — clean, no tier prefix
            location   = _clean_location(j)
            remote_str = "Remote" if j.get("remote") else "On-site"
            loc_display = f"{location} &nbsp;·&nbsp; {remote_str}"

            rows_html += (
                '<tr style="border-bottom:1px solid #eee;">'
                # Title as link
                f'<td style="padding:7px 8px;min-width:220px;">'
                f'<a href="{j["url"]}" style="color:#1a1a2e;font-weight:500;'
                f'text-decoration:none;">{j["title"]}</a></td>'
                # Location
                f'<td style="padding:7px 8px;color:#555;font-size:13px;'
                f'white-space:nowrap;">{loc_display}</td>'
                # Salary with band label
                f'<td style="padding:7px 8px;white-space:nowrap;">'
                f'<span style="font-weight:600;color:{band_color};'
                f'font-size:12px;margin-right:6px;">{band}</span>'
                f'{salary_display}{salary_note}</td>'
                "</tr>\n"
            )

    html = f"""<html>
<body style="font-family:Arial,sans-serif;font-size:14px;color:#222;
             max-width:900px;margin:0 auto;padding:16px;">
  <h2 style="color:#1a1a2e;border-bottom:2px solid #1a1a2e;
             padding-bottom:8px;margin-bottom:4px;">
    IT Job Search — {run_date}
  </h2>
  <p style="color:#666;margin-top:4px;margin-bottom:16px;">
    {len(new_jobs)} new listing{"s" if len(new_jobs) != 1 else ""}
    across {total_companies} {"companies" if total_companies != 1 else "company"}
  </p>
  <table cellpadding="0" cellspacing="0"
         style="border-collapse:collapse;width:100%;border:1px solid #ddd;">
    <thead>
      <tr style="background:#f0f0f0;font-weight:bold;
                 border-bottom:2px solid #ccc;font-size:13px;">
        <th align="left" style="padding:8px 8px;">Title</th>
        <th align="left" style="padding:8px 8px;">Location</th>
        <th align="left" style="padding:8px 8px;">Salary</th>
      </tr>
    </thead>
    <tbody>
      {rows_html}
    </tbody>
  </table>
  <p style="font-size:11px;color:#999;margin-top:12px;">
    (est.) — salary was not in the job listing and was estimated by AI.
    Jobs sorted by salary within each company.
  </p>
</body>
</html>"""

    return plain, html


def _send_via_smtp(subject: str, plain: str, html: str) -> bool:
    """Deliver the report via SMTP. Returns True on success."""
    msg            = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = EMAIL_FROM
    msg["To"]      = EMAIL_TO
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html,  "html"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.login(EMAIL_FROM, EMAIL_PASSWORD)
            server.sendmail(EMAIL_FROM, EMAIL_TO, msg.as_string())
        log.info(f"Email delivered to {EMAIL_TO}")
        return True
    except smtplib.SMTPException as e:
        log.error(f"SMTP error: {e}")
        return False


def send_report(new_jobs: list[dict], run_date: str) -> None:
    """
    Build and send the weekly report.
    Falls back to printing to console if email credentials aren't configured.
    """
    subject     = f"IT Job Search — {run_date} ({len(new_jobs)} new)"
    plain, html = _build_report(new_jobs, run_date)

    if not EMAIL_PASSWORD:
        log.warning("EMAIL_PASSWORD not set — printing report to console instead.")
        print("\n" + plain)
        return

    if not _send_via_smtp(subject, plain, html):
        log.warning("Email delivery failed — printing to console as fallback.")
        print("\n" + plain)
