import logging
import os
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field

ROOT = Path(__file__).parent
DATABASE_URL = os.getenv("DATABASE_URL")
SQLITE_PATH = os.getenv("DATABASE_PATH", str(ROOT / "local_enquiries.db"))
POOL = None
logger = logging.getLogger("tech_talent_usa")

SCHEMA = """
CREATE TABLE IF NOT EXISTS enquiries (
    id BIGSERIAL PRIMARY KEY,
    company VARCHAR(160) NOT NULL,
    contact VARCHAR(120) NOT NULL,
    email VARCHAR(254) NOT NULL,
    phone VARCHAR(30) NOT NULL,
    job_title VARCHAR(160) NOT NULL,
    skills TEXT NOT NULL,
    experience VARCHAR(80) NOT NULL DEFAULT '',
    location VARCHAR(160) NOT NULL DEFAULT '',
    positions INTEGER NOT NULL CHECK (positions > 0),
    message TEXT NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_enquiries_created_at ON enquiries (created_at DESC);
"""

class Enquiry(BaseModel):
    company: str = Field(min_length=2, max_length=160)
    contact: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: str = Field(min_length=7, max_length=30)
    job_title: str = Field(min_length=2, max_length=160)
    skills: str = Field(min_length=2, max_length=1000)
    experience: str = Field(default="", max_length=80)
    location: str = Field(default="", max_length=160)
    positions: int = Field(ge=1, le=500)
    message: str = Field(default="", max_length=3000)

def init_sqlite():
    with sqlite3.connect(SQLITE_PATH) as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS enquiries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT NOT NULL, contact TEXT NOT NULL, email TEXT NOT NULL,
            phone TEXT NOT NULL, job_title TEXT NOT NULL, skills TEXT NOT NULL,
            experience TEXT NOT NULL DEFAULT '', location TEXT NOT NULL DEFAULT '',
            positions INTEGER NOT NULL, message TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_enquiries_created_at ON enquiries(created_at)")

@asynccontextmanager
async def lifespan(app: FastAPI):
    global POOL
    if DATABASE_URL:
        from psycopg_pool import ConnectionPool
        connection_string = DATABASE_URL.replace("postgres://", "postgresql://", 1)
        POOL = ConnectionPool(
            conninfo=connection_string,
            min_size=int(os.getenv("DB_POOL_MIN", "1")),
            max_size=int(os.getenv("DB_POOL_MAX", "10")),
            timeout=5,
            open=False,
        )
        POOL.open()
        with POOL.connection() as conn:
            conn.execute(SCHEMA)
            conn.commit()
    elif not os.getenv("RENDER"):
        init_sqlite()
    yield
    if POOL:
        POOL.close()
        POOL = None

app = FastAPI(title="Tech Talent USA", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")

@app.get("/about", response_class=HTMLResponse)
def about_page():
    return (ROOT / "static" / "index.html").read_text(encoding="utf-8")

@app.get("/services", response_class=HTMLResponse)
def services_page():
    return (ROOT / "static" / "index.html").read_text(encoding="utf-8")

@app.get("/how-we-work", response_class=HTMLResponse)
def process_page():
    return (ROOT / "static" / "index.html").read_text(encoding="utf-8")

@app.get("/contact", response_class=HTMLResponse)
def contact_page():
    return (ROOT / "static" / "index.html").read_text(encoding="utf-8")

@app.get("/privacy", response_class=HTMLResponse)
def privacy_page():
    return (ROOT / "static" / "privacy.html").read_text(encoding="utf-8")

@app.get("/", response_class=HTMLResponse)
def home():
    return (ROOT / "static" / "index.html").read_text(encoding="utf-8")

@app.get("/health")
def health():
    return {
        "status": "ok" if (POOL is not None or not os.getenv("RENDER")) else "degraded",
        "service": "Tech Talent USA",
        "database": "connected" if POOL is not None else ("local" if not os.getenv("RENDER") else "not_configured"),
    }

def deliver_notification(payload: dict):
    """Send a formatted hiring enquiry receipt through Resend's HTTPS API."""
    import html
    import json
    from datetime import datetime, timezone
    from urllib.error import HTTPError, URLError
    from urllib.request import Request, urlopen

    api_key = os.getenv("RESEND_API_KEY")
    recipient = os.getenv("CONTACT_EMAIL")
    if not api_key:
        logger.error("Resend notification skipped: RESEND_API_KEY is not configured")
        return
    if not recipient:
        logger.error("Resend notification skipped: CONTACT_EMAIL is not configured")
        return

    labels = [
        ("company", "Company"),
        ("contact", "Contact Person"),
        ("email", "Email Address"),
        ("phone", "Phone Number"),
        ("job_title", "Position / Job Title"),
        ("skills", "Required Skills"),
        ("experience", "Experience"),
        ("location", "Job Location"),
        ("positions", "Number of Positions"),
        ("message", "Additional Details"),
    ]
    rows = []
    text_lines = [
        "TECH TALENT USA",
        "NEW HIRING ENQUIRY",
        "Enquiry details submitted through the website",
        "",
    ]
    for key, label in labels:
        value = str(payload.get(key) or "Not provided")
        safe_label = html.escape(label)
        safe_value = html.escape(value).replace("\n", "<br>")
        rows.append(
            f'<tr><td style="padding:12px 14px;border-bottom:1px solid #e8edf3;'
            f'color:#526174;font-size:13px;font-weight:600;width:36%;vertical-align:top;">'
            f'{safe_label}</td><td style="padding:12px 14px;border-bottom:1px solid #e8edf3;'
            f'color:#172033;font-size:14px;vertical-align:top;">{safe_value}</td></tr>'
        )
        text_lines.append(f"{label}: {value}")

    submitted_at = datetime.now(timezone.utc).strftime("%d %b %Y, %I:%M %p UTC")
    safe_submitted_at = html.escape(submitted_at)
    job_title = str(payload.get("job_title") or "Website enquiry")
    safe_job_title = html.escape(job_title)
    html_body = f"""\
<!doctype html>
<html>
  <body style="margin:0;padding:24px;background:#f3f6fa;font-family:Arial,Helvetica,sans-serif;color:#172033;">
    <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="max-width:680px;margin:0 auto;background:#ffffff;border:1px solid #e5eaf1;border-radius:12px;overflow:hidden;">
      <tr>
        <td style="padding:26px 30px;background:#10243a;color:#ffffff;">
          <div style="font-size:12px;letter-spacing:2px;font-weight:700;color:#b9d4f2;">TECH TALENT USA</div>
          <div style="font-size:24px;font-weight:700;margin-top:9px;">New Hiring Enquiry</div>
          <div style="font-size:13px;color:#d4dfeb;margin-top:7px;">A new request has been submitted through your website.</div>
        </td>
      </tr>
      <tr>
        <td style="padding:24px 30px 10px;">
          <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f6f8fb;border:1px solid #e8edf3;border-radius:8px;">
            <tr>
              <td style="padding:14px 16px;">
                <div style="font-size:11px;color:#64748b;text-transform:uppercase;letter-spacing:1px;">Enquiry summary</div>
                <div style="font-size:17px;font-weight:700;color:#10243a;margin-top:5px;">{safe_job_title}</div>
                <div style="font-size:12px;color:#64748b;margin-top:6px;">Received: {safe_submitted_at}</div>
              </td>
            </tr>
          </table>
        </td>
      </tr>
      <tr>
        <td style="padding:18px 30px 28px;">
          <div style="font-size:15px;font-weight:700;color:#10243a;margin-bottom:10px;">Enquiry details</div>
          <table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="border:1px solid #e8edf3;border-radius:8px;border-collapse:separate;border-spacing:0;">
            {''.join(rows)}
          </table>
          <p style="font-size:12px;line-height:1.6;color:#7b8797;margin:20px 0 0;">This is an automated notification from the Tech Talent USA website. You can reply directly to this email to contact the person who submitted the enquiry.</p>
        </td>
      </tr>
      <tr>
        <td style="padding:16px 30px;background:#f6f8fb;border-top:1px solid #e8edf3;font-size:11px;color:#7b8797;">Tech Talent USA · Hiring Enquiry Notification</td>
      </tr>
    </table>
  </body>
</html>"""
    body = {
        "from": os.getenv("RESEND_FROM", "Tech Talent USA <onboarding@resend.dev>"),
        "to": [recipient],
        "subject": f"New hiring enquiry: {job_title}",
        "text": "\n".join(text_lines),
        "html": html_body,
    }
    reply_to = payload.get("email")
    if reply_to:
        body["reply_to"] = reply_to

    request = Request(
        "https://api.resend.com/emails",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "User-Agent": "TechTalentUSA/1.0",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=15) as response:
            result = json.loads(response.read().decode("utf-8"))
            logger.info("Resend accepted hiring enquiry notification; message_id=%s", result.get("id"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1000]
        logger.error("Resend API rejected hiring enquiry notification: status=%s response=%s", exc.code, detail)
    except (URLError, TimeoutError, OSError):
        logger.exception("Resend HTTPS request failed while sending hiring enquiry notification")
    except Exception:
        logger.exception("Unexpected error while sending hiring enquiry notification")

@app.post("/api/enquiries", status_code=201)
def submit_enquiry(data: Enquiry, background_tasks: BackgroundTasks):
    values = data.model_dump()
    values["email"] = str(data.email)

    if POOL is not None:
        with POOL.connection() as conn:
            row = conn.execute(
                """INSERT INTO enquiries
                (company, contact, email, phone, job_title, skills, experience, location, positions, message)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                tuple(values[k] for k in ("company","contact","email","phone","job_title","skills","experience","location","positions","message")),
            ).fetchone()
            conn.commit()
            enquiry_id = row[0]
    elif not os.getenv("RENDER"):
        with sqlite3.connect(SQLITE_PATH) as conn:
            cur = conn.execute(
                """INSERT INTO enquiries
                (company, contact, email, phone, job_title, skills, experience, location, positions, message)
                VALUES (?,?,?,?,?,?,?,?,?,?)""",
                tuple(values[k] for k in ("company","contact","email","phone","job_title","skills","experience","location","positions","message")),
            )
            enquiry_id = cur.lastrowid
    else:
        raise HTTPException(status_code=503, detail="Enquiry service is temporarily unavailable. Please contact our team by email.")

    background_tasks.add_task(deliver_notification, values)
    return {"success": True, "enquiry_id": enquiry_id, "message": "Your hiring enquiry has been received."}
