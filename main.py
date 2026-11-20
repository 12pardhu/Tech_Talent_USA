import logging
import os
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field

ROOT = Path(__file__).parent
DATABASE_URL = os.getenv("DATABASE_URL")
SQLITE_PATH = os.getenv("DATABASE_PATH", str(ROOT / "local_enquiries.db"))
POOL = None
SUBMISSION_ATTEMPTS = {}
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
    consent BOOLEAN NOT NULL DEFAULT FALSE,
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
        existing = {row[1] for row in conn.execute("PRAGMA table_info(enquiries)").fetchall()}
        for column, definition in (
            ("whatsapp_number", "TEXT NOT NULL DEFAULT ''"),
            ("resume_filename", "TEXT NOT NULL DEFAULT ''"),
            ("resume_content_type", "TEXT NOT NULL DEFAULT ''"),
            ("resume_data", "BLOB"),
            ("consent", "INTEGER NOT NULL DEFAULT 0"),
        ):
            if column not in existing:
                conn.execute(f"ALTER TABLE enquiries ADD COLUMN {column} {definition}")

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
            conn.execute("ALTER TABLE enquiries ADD COLUMN IF NOT EXISTS whatsapp_number VARCHAR(30) NOT NULL DEFAULT ''")
            conn.execute("ALTER TABLE enquiries ADD COLUMN IF NOT EXISTS resume_filename VARCHAR(255) NOT NULL DEFAULT ''")
            conn.execute("ALTER TABLE enquiries ADD COLUMN IF NOT EXISTS resume_content_type VARCHAR(120) NOT NULL DEFAULT ''")
            conn.execute("ALTER TABLE enquiries ADD COLUMN IF NOT EXISTS resume_data BYTEA")
            conn.execute("ALTER TABLE enquiries ADD COLUMN IF NOT EXISTS consent BOOLEAN NOT NULL DEFAULT FALSE")
            conn.commit()
    else:
        init_sqlite()
    yield
    if POOL:
        POOL.close()
        POOL = None

app = FastAPI(title="Tech Talent USA", lifespan=lifespan)

@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["X-Frame-Options"] = "DENY"
    return response
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

@app.get("/faq", response_class=HTMLResponse)
def faq_page():
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
        "status": "ok",
        "service": "Tech Talent USA",
        "database": "postgres" if POOL is not None else "sqlite_preview_store",
    }

def deliver_notification(payload: dict):
    """Send candidate profile notification through Resend, attaching an uploaded resume."""
    import html
    import json
    from datetime import datetime, timezone
    from urllib.error import HTTPError, URLError
    from urllib.request import Request, urlopen

    api_key = os.getenv("RESEND_API_KEY")
    recipient = os.getenv("CONTACT_EMAIL")
    if not api_key or not recipient:
        logger.error("Candidate notification skipped: email configuration is incomplete")
        return

    labels = [
        ("name", "Candidate Name"),
        ("email", "Email Address"),
        ("phone", "Phone Number"),
        ("whatsapp_number", "WhatsApp Number"),
        ("experience", "Years of Experience"),
        ("location", "Current Location"),
        ("skills", "Key Skills"),
        ("resume_filename", "Resume"),
        ("message", "Additional Details"),
    ]
    rows = []
    text_lines = ["TECH TALENT USA", "NEW CANDIDATE PROFILE", ""]
    for key, label in labels:
        value = str(payload.get(key) or "Not provided")
        text_lines.append(f"{label}: {value}")
        rows.append(
            '<tr><td style="padding:12px 14px;border-bottom:1px solid #e8edf3;color:#526174;font-size:13px;font-weight:600;width:36%;vertical-align:top;">'
            + html.escape(label) +
            '</td><td style="padding:12px 14px;border-bottom:1px solid #e8edf3;color:#172033;font-size:14px;vertical-align:top;">'
            + html.escape(value).replace("\n", "<br>") +
            '</td></tr>'
        )

    submitted_at = datetime.now(timezone.utc).strftime("%d %b %Y, %I:%M %p UTC")
    safe_name = html.escape(str(payload.get("name") or "Candidate"))
    html_body = f"""<!doctype html>
<html><body style="margin:0;padding:24px;background:#f3f6fa;font-family:Arial,Helvetica,sans-serif;color:#172033;">
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="max-width:680px;margin:0 auto;background:#fff;border:1px solid #e5eaf1;border-radius:12px;overflow:hidden;">
<tr><td style="padding:26px 30px;background:#10243a;color:#fff;"><div style="font-size:12px;letter-spacing:2px;font-weight:700;color:#b9d4f2;">TECH TALENT USA</div><div style="font-size:24px;font-weight:700;margin-top:9px;">New Candidate Profile</div><div style="font-size:13px;color:#d4dfeb;margin-top:7px;">A candidate has submitted their profile through your website.</div></td></tr>
<tr><td style="padding:24px 30px 10px;"><div style="font-size:17px;font-weight:700;color:#10243a;">{safe_name}</div><div style="font-size:12px;color:#64748b;margin-top:6px;">Received: {html.escape(submitted_at)}</div></td></tr>
<tr><td style="padding:18px 30px 28px;"><div style="font-size:15px;font-weight:700;color:#10243a;margin-bottom:10px;">Candidate details</div>
<table role="presentation" cellpadding="0" cellspacing="0" border="0" width="100%" style="border:1px solid #e8edf3;border-radius:8px;border-collapse:separate;border-spacing:0;">{''.join(rows)}</table>
<p style="font-size:12px;line-height:1.6;color:#7b8797;margin:20px 0 0;">This is an automated candidate registration notification from the Tech Talent USA website.</p></td></tr>
<tr><td style="padding:16px 30px;background:#f6f8fb;border-top:1px solid #e8edf3;font-size:11px;color:#7b8797;">Tech Talent USA · Candidate Profile Notification</td></tr></table></body></html>"""

    body = {
        "from": os.getenv("RESEND_FROM", "Tech Talent USA <onboarding@resend.dev>"),
        "to": [recipient],
        "subject": f"New candidate profile: {payload.get('name', 'Website submission')}",
        "text": "\n".join(text_lines),
        "html": html_body,
    }
    if payload.get("email"):
        body["reply_to"] = payload["email"]
    if payload.get("resume_content_base64") and payload.get("resume_filename"):
        body["attachments"] = [{
            "filename": payload["resume_filename"],
            "content": payload["resume_content_base64"],
        }]

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
        with urlopen(request, timeout=20) as response:
            result = json.loads(response.read().decode("utf-8"))
            logger.info("Resend accepted candidate profile notification; message_id=%s", result.get("id"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:1000]
        logger.error("Resend rejected candidate notification: status=%s response=%s", exc.code, detail)
    except (URLError, TimeoutError, OSError):
        logger.exception("Resend HTTPS request failed while sending candidate notification")
    except Exception:
        logger.exception("Unexpected error while sending candidate notification")

@app.post("/api/enquiries", status_code=201)
async def submit_enquiry(
    request: Request,
    background_tasks: BackgroundTasks,
    name: str = Form(..., min_length=2, max_length=120),
    email: str = Form(..., max_length=254),
    phone: str = Form(..., min_length=7, max_length=30),
    whatsapp_number: str = Form("", max_length=30),
    experience: str = Form("", max_length=80),
    location: str = Form("", max_length=160),
    skills: str = Form(..., min_length=2, max_length=1000),
    message: str = Form("", max_length=3000),
    consent: bool = Form(False),
    website: str = Form("", max_length=300),
    resume: Optional[UploadFile] = File(None),
):
    import base64
    import re

    if website.strip():
        raise HTTPException(status_code=400, detail="Unable to process this submission.")
    if not consent:
        raise HTTPException(status_code=422, detail="Please confirm the privacy notice before submitting.")
    client_ip = request.client.host if request.client else "unknown"
    now = __import__("time").time()
    recent = [stamp for stamp in SUBMISSION_ATTEMPTS.get(client_ip, []) if now - stamp < 600]
    if len(recent) >= 5:
        raise HTTPException(status_code=429, detail="Too many submissions. Please wait a few minutes and try again.")
    recent.append(now)
    SUBMISSION_ATTEMPTS[client_ip] = recent
    if len(SUBMISSION_ATTEMPTS) > 2000:
        SUBMISSION_ATTEMPTS.clear()
    if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", email.strip()):
        raise HTTPException(status_code=422, detail="Please enter a valid email address.")

    resume_bytes = None
    resume_filename = ""
    resume_content_type = ""
    if resume and resume.filename:
        resume_filename = Path(resume.filename).name
        extension = Path(resume_filename).suffix.lower()
        if extension not in {".pdf", ".docx"}:
            raise HTTPException(status_code=400, detail="Resume must be a PDF or DOCX file.")
        resume_bytes = await resume.read(5 * 1024 * 1024 + 1)
        if len(resume_bytes) > 5 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="Resume file must be 5 MB or smaller.")
        if extension == ".pdf":
            if not resume_bytes.startswith(b"%PDF-"):
                raise HTTPException(status_code=400, detail="The uploaded file does not appear to be a valid PDF.")
            resume_content_type = "application/pdf"
        else:
            if not resume_bytes.startswith(b"PK\x03\x04"):
                raise HTTPException(status_code=400, detail="The uploaded file does not appear to be a valid DOCX document.")
            resume_content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    values = {
        "name": name.strip(),
        "email": email.strip(),
        "phone": phone.strip(),
        "whatsapp_number": whatsapp_number.strip(),
        "experience": experience.strip(),
        "location": location.strip(),
        "skills": skills.strip(),
        "message": message.strip(),
        "resume_filename": resume_filename,
        "consent": consent,
    }

    if POOL is not None:
        with POOL.connection() as conn:
            row = conn.execute(
                """INSERT INTO enquiries
                (company, contact, email, phone, job_title, skills, experience, location,
                 positions, message, whatsapp_number, resume_filename, resume_content_type, resume_data, consent)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                (
                    "Candidate profile", values["name"], values["email"], values["phone"],
                    "Candidate registration", values["skills"], values["experience"],
                    values["location"], 1, values["message"], values["whatsapp_number"],
                    resume_filename, resume_content_type, resume_bytes, consent,
                ),
            ).fetchone()
            conn.commit()
            enquiry_id = row[0]
    else:
        with sqlite3.connect(SQLITE_PATH) as conn:
            cur = conn.execute(
                """INSERT INTO enquiries
                (company, contact, email, phone, job_title, skills, experience, location,
                 positions, message, whatsapp_number, resume_filename, resume_content_type, resume_data, consent)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    "Candidate profile", values["name"], values["email"], values["phone"],
                    "Candidate registration", values["skills"], values["experience"],
                    values["location"], 1, values["message"], values["whatsapp_number"],
                    resume_filename, resume_content_type, resume_bytes, int(consent),
                ),
            )
            enquiry_id = cur.lastrowid

    notification = dict(values)
    if resume_bytes:
        notification["resume_content_base64"] = base64.b64encode(resume_bytes).decode("ascii")
    background_tasks.add_task(deliver_notification, notification)
    return {"success": True, "enquiry_id": enquiry_id, "message": "Your profile has been received."}
