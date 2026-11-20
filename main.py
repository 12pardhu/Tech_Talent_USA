import os, sqlite3, smtplib
from email.message import EmailMessage
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, EmailStr, Field

ROOT = Path(__file__).parent
DB_PATH = os.getenv("DATABASE_PATH", str(ROOT / "enquiries.db"))
app = FastAPI(title="Tech Talent USA")
app.mount("/static", StaticFiles(directory=ROOT / "static"), name="static")

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""CREATE TABLE IF NOT EXISTS enquiries (
        id INTEGER PRIMARY KEY AUTOINCREMENT, company TEXT, contact TEXT,
        email TEXT, phone TEXT, job_title TEXT, skills TEXT, experience TEXT,
        location TEXT, positions INTEGER, message TEXT, created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    )""")
    conn.commit()
    return conn

class Enquiry(BaseModel):
    company: str = Field(min_length=2, max_length=160)
    contact: str = Field(min_length=2, max_length=120)
    email: EmailStr
    phone: str = Field(min_length=7, max_length=30)
    job_title: str = Field(min_length=2, max_length=160)
    skills: str = Field(min_length=2, max_length=1000)
    experience: str = Field(max_length=80)
    location: str = Field(max_length=160)
    positions: int = Field(ge=1, le=500)
    message: str = Field(default="", max_length=3000)

@app.get("/", response_class=HTMLResponse)
def home():
    return (ROOT / "static" / "index.html").read_text(encoding="utf-8")

@app.get("/health")
def health():
    return {"status":"ok","app":"Tech Talent USA"}

@app.post("/api/enquiries")
def submit_enquiry(data: Enquiry):
    conn = db()
    cur = conn.execute(
        "INSERT INTO enquiries(company,contact,email,phone,job_title,skills,experience,location,positions,message) VALUES(?,?,?,?,?,?,?,?,?,?)",
        (data.company,data.contact,str(data.email),data.phone,data.job_title,data.skills,data.experience,data.location,data.positions,data.message)
    )
    enquiry_id = cur.lastrowid
    conn.commit()
    conn.close()
    # Email notification is sent only when SMTP settings are supplied in Render.
    host, user, password = os.getenv("SMTP_HOST"), os.getenv("SMTP_USER"), os.getenv("SMTP_PASSWORD")
    if host and user and password:
        msg = EmailMessage()
        msg["Subject"] = f"New hiring enquiry: {data.job_title}"
        msg["From"] = os.getenv("SMTP_FROM", user)
        msg["To"] = os.getenv("CONTACT_EMAIL", "sample@gmail.com")
        msg.set_content("\n".join(f"{k}: {v}" for k,v in data.model_dump().items()))
        try:
            with smtplib.SMTP(host, int(os.getenv("SMTP_PORT","587"))) as server:
                server.starttls()
                server.login(user,password)
                server.send_message(msg)
        except Exception:
            # Keep the enquiry stored even if email delivery fails.
            pass
    return {"ok":True,"id":enquiry_id,"message":"Thank you. Your hiring enquiry has been received."}
