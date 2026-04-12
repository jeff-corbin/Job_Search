"""
emailer.py
==========
Builds and sends the job summary email.
Filters out "✗ Low" salary band jobs — those aren't worth your time.
"""

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from config import EMAIL_TO, EMAIL_FROM, EMAIL_PASSWORD, SMTP_HOST, SMTP_PORT

log = logging.getLogger(__name__)


def _sort_key(job: dict) -> int:
    high = job.get("salary_high")
    return -(high if high is not None else 0)


def _clean_location(job: dict) -> str:
    location = job.get("location", "Not specified")
    for prefix in ["✓ US", "~ Canada", "~ Mexico", "~ Remote", "? Unknown", "✓", "~", "?"]:
        if location.startswith(prefix):
            location = location[len(prefix):].strip()
    return location or "Not specified"


def _build_report(new_jobs: list[dict], run_date: str) -> tuple[str, str]:
    # Filter out Low salary jobs for display — still tracked in state
    display_jobs = [j for j in new_jobs if j.get("salary_band") != "✗ Low"]

    if not display_jobs:
        plain = (
            f"IT Job Search — {run_date}\n"
            + "=" * 55 + "\n\n"
            + "No new jobs above your salary threshold this week.\n"
        )
        html = (
            f"<h2>IT Job Search — {run_date}</h2>"
            "<p>No new jobs above your salary threshold this week.</p>"
        )
        return plain, html

    # Group by company, sort alpha, sort within by salary desc
    by_company: dict[str, list] = {}
    for job in display_jobs:
        org = job.get("organization", "Unknown")
        by_company.setdefault(org, []).append(job)

    for org in by_company:
        by_company[org].sort(key=_sort_key)
    by_company = dict(sorted(by_company.items(), key=lambda x: x[0].lower()))

    total_companies = len(by_company)

    # Plain text
    lines = [
        f"IT Job Search — {run_date}",
        "=" * 55,
        f"  {len(display_jobs)} listing(s) across {total_companies} company/companies\n",
    ]
    for org, jobs in by_company.items():
        lines.append(f"\n{'─' * 45}")
        lines.append(f"  {org}  ({len(jobs)} job{'s' if len(jobs) != 1 else ''})")
        lines.append(f"{'─' * 45}")
        for j in jobs:
            salary_note = "  *estimate" if j.get("salary_estimated") else ""
            location    = _clean_location(j)
            remote_str  = "Remote" if j.get("remote") else "On-site"
            lines += [
                f"\n  Title:    {j['title']}",
                f"  Location: {location}  ({remote_str})",
                f"  Salary:   {j.get('salary_band', '')}  {j.get('salary') or 'Not listed'}{salary_note}",
                f"  Link:     {j['url']}",
            ]
    lines += [
        "\n" + "=" * 55,
        "*estimate — salary not listed; estimated by AI.",
        f"Generated {run_date}",
    ]
    plain = "\n".join(lines)

    # HTML — mobile-first, single column
    rows_html = ""
    for org, jobs in by_company.items():
        # Company header row — slightly larger, bold, stands out without being loud
        rows_html += (
            f'<tr>'
            f'<td colspan="3" style="background:#1a1a2e;color:#ffffff;'
            f'padding:10px 14px;font-size:16px;font-weight:700;letter-spacing:0.2px;'
            f'border-top:3px solid #3a3a5e;">'
            f'{org}'
            f'<span style="font-weight:400;font-size:12px;margin-left:10px;opacity:0.7;">'
            f'{len(jobs)} listing{"s" if len(jobs) != 1 else ""}'
            f'</span>'
            f'</td>'
            f'</tr>\n'
        )
        for j in jobs:
            salary_note = (
                '<span style="font-size:11px;color:#999;margin-left:4px">(est.)</span>'
                if j.get("salary_estimated") else ""
            )
            band       = j.get("salary_band", "")
            band_color = (
                "#2e7d32" if "Strong" in band else
                "#b45309" if "Review" in band else
                "#777"
            )
            location    = _clean_location(j)
            remote_str  = "Remote" if j.get("remote") else "On-site"
            loc_display = f"{location} · {remote_str}"

            rows_html += (
                '<tr style="border-bottom:1px solid #eee;vertical-align:top;">'
                # Title as link
                f'<td style="padding:8px 10px;min-width:0;word-break:break-word;">'
                f'<a href="{j["url"]}" style="color:#1a1a2e;font-weight:600;'
                f'text-decoration:none;font-size:14px;">{j["title"]}</a>'
                f'<div style="font-size:12px;color:#666;margin-top:3px;">{loc_display}</div>'
                f'</td>'
                # Salary + band
                f'<td style="padding:8px 10px;white-space:nowrap;font-size:13px;">'
                f'<span style="font-weight:700;color:{band_color};'
                f'font-size:11px;display:block;margin-bottom:2px;">{band}</span>'
                f'{j.get("salary") or "Not listed"}{salary_note}'
                f'</td>'
                '</tr>\n'
            )

    html = f"""<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
  body {{
    font-family: Arial, sans-serif;
    font-size: 14px;
    color: #222;
    margin: 0;
    padding: 12px;
    background: #f5f5f5;
  }}
  .container {{
    max-width: 680px;
    margin: 0 auto;
    background: #fff;
    border-radius: 6px;
    overflow: hidden;
    box-shadow: 0 1px 4px rgba(0,0,0,0.1);
  }}
  .header {{
    background: #1a1a2e;
    color: #fff;
    padding: 16px 20px;
  }}
  .header h2 {{
    margin: 0 0 4px 0;
    font-size: 20px;
  }}
  .header p {{
    margin: 0;
    opacity: 0.7;
    font-size: 13px;
  }}
  table {{
    width: 100%;
    border-collapse: collapse;
  }}
  .footer {{
    padding: 10px 14px;
    font-size: 11px;
    color: #999;
    background: #fafafa;
    border-top: 1px solid #eee;
  }}
  @media (max-width: 480px) {{
    body {{ padding: 0; }}
    .header {{ padding: 12px 14px; }}
    .header h2 {{ font-size: 17px; }}
    td {{ font-size: 13px !important; }}
  }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h2>IT Job Search — {run_date}</h2>
    <p>{len(display_jobs)} listing{"s" if len(display_jobs) != 1 else ""} across {total_companies} {"companies" if total_companies != 1 else "company"}</p>
  </div>
  <table>
    <thead>
      <tr style="background:#f0f0f0;border-bottom:2px solid #ccc;font-size:12px;color:#555;">
        <th align="left" style="padding:8px 10px;font-weight:600;">TITLE / LOCATION</th>
        <th align="left" style="padding:8px 10px;font-weight:600;">SALARY</th>
      </tr>
    </thead>
    <tbody>
      {rows_html}
    </tbody>
  </table>
  <div class="footer">
    (est.) = salary not listed, estimated by AI. &nbsp;|&nbsp; Generated {run_date}
  </div>
</div>
</body>
</html>"""

    return plain, html


def _send_via_smtp(subject: str, plain: str, html: str) -> bool:
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
    """Build and send the report. Falls back to console if EMAIL_PASSWORD isn't set."""
    subject     = f"IT Job Search — {run_date}"
    plain, html = _build_report(new_jobs, run_date)

    if not EMAIL_PASSWORD:
        log.warning("EMAIL_PASSWORD not set — printing to console.")
        print("\n" + plain)
        return

    if not _send_via_smtp(subject, plain, html):
        log.warning("Email failed — printing to console as fallback.")
        print("\n" + plain)