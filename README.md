# VidSwift Django Backend — Step 1

This is the first deployment-ready backend for VidSwift.

## What is included

- Django 6 API project
- CORS configured for the Netlify frontend URL via `FRONTEND_URL`
- `GET /api/health/` health check
- `POST /api/resolve/` URL validation + platform detection
- YouTube, TikTok, Instagram and Facebook host detection

The media resolver is intentionally not enabled yet. First deploy and test this API. After the API is live, Step 2 will add the authorized media-resolution layer and connect the existing Netlify frontend.

## Local setup

```bash
python -m venv .venv
```

Windows:
```bash
.venv\Scripts\activate
```

macOS/Linux:
```bash
source .venv/bin/activate
```

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Health check:
`http://127.0.0.1:8000/api/health/`

## Environment variables

Production:

- `DJANGO_SECRET_KEY` — a long random secret
- `FRONTEND_URL` — your exact Netlify origin, for example `https://your-site.netlify.app`
- `DEBUG=False`
- `ALLOWED_HOSTS` — optional comma-separated additional hosts

Do not put the Django secret key in the frontend HTML.

## Vercel

Push this folder to GitHub, import the repository into Vercel, and deploy. Current Vercel Django support detects `manage.py` and the Django WSGI entry point without the old custom `/api/index.py` pattern.

After deployment, test:
`https://YOUR-BACKEND.vercel.app/api/health/`

Expected response:
```json
{"ok":true,"service":"VidSwift Django API"}
```
