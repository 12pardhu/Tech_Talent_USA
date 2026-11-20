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
    import smtplib
    from email.message import EmailMessage
    host, user, password = os.getenv("SMTP_HOST"), os.getenv("SMTP_USER"), os.getenv("SMTP_PASSWORD")
    if not (host and user and password):
        return
    message = EmailMessage()
    message["Subject"] = f"New hiring enquiry: {payload['job_title']}"
    message["From"] = os.getenv("SMTP_FROM", user)
    message["To"] = os.getenv("CONTACT_EMAIL", "sample@gmail.com")
    message.set_content("\\n".join(f"{key}: {value}" for key, value in payload.items()))
    try:
        with smtplib.SMTP(host, int(os.getenv("SMTP_PORT", "587")), timeout=10) as server:
            server.starttls()
            server.login(user, password)
            server.send_message(message)
    except Exception:
        logger.exception("Hiring enquiry notification could not be delivered")

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
