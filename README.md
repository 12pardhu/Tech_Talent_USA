# Tech Talent USA

A candidate-focused technology career website for professionals exploring opportunities in the United States.

## Phase 1 — Website experience

- Candidate-focused homepage and clear profile-submission calls to action.
- Career areas and a simple candidate journey explanation.
- Candidate registration with required-field validation, completion feedback, optional PDF/DOCX resume upload (5 MB maximum), and submission status.
- WhatsApp, phone, and email contact options.
- Frequently asked questions and a plain-language privacy notice.
- Responsive navigation and layouts for desktop, tablet, and mobile.
- Search/social-sharing metadata and accessibility improvements.
- Server-side consent validation, a honeypot field, basic submission rate limiting, upload checks, and security response headers.

## Run locally

Install dependencies and start the API:

```bash
pip install -r requirements.txt
python -m uvicorn main:app --reload
```

Open `http://127.0.0.1:8000`.

## Environment

- `DATABASE_URL`: PostgreSQL connection string for the production database.
- `RESEND_API_KEY`: Resend API key for candidate notification emails.
- `CONTACT_EMAIL`: destination inbox for candidate notifications.
- `RESEND_FROM`: optional verified sender, once the sending domain is configured.

Never commit credentials or share database connection strings in chat.

## Preview environment

The Phase 1 preview runs from the `phase-1-website-experience` branch at:

https://tech-talent-usa-phase1-preview.onrender.com

The preview service intentionally does not use production database credentials or email secrets. When no database URL is configured, it uses a temporary SQLite store for safe form-flow testing. Preview submissions may be lost when the service restarts or redeploys, and preview email notifications are not sent. Use fictional test details only.

## Production

Production remains on the `main` branch. Do not merge Phase 1 into `main` or deploy it to the production service until the preview has been reviewed and explicitly approved.
