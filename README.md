# 🌍 NPDC — National Polar Data Center

A Django web portal for managing India's polar research datasets (Arctic, Antarctic, Southern Ocean, Himalaya).

---

## Prerequisites

| Software   | Version | Download |
|------------|---------|----------|
| Python     | 3.10+   | https://www.python.org/downloads/ |
| PostgreSQL | 13+     | https://www.postgresql.org/download/ |
| Git        | any     | https://git-scm.com/ |

---

## Setup (Step by Step)

### 1. Clone the project

```bash
git clone <repo-url> npdc
cd npdc
```

### 2. Create a virtual environment

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Windows (CMD):**
```cmd
python -m venv .venv
.venv\Scripts\activate
```

**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Create the `.env` file

```bash
copy .env.example .env        # Windows
cp .env.example .env           # macOS / Linux
```

Open `.env` and fill in your database details:

```env
# Django
DJANGO_SECRET_KEY=any-random-string-here
DEBUG=True

# PostgreSQL
DB_ENGINE=django.db.backends.postgresql
DB_NAME=metainfo
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432

# AI Chatbot (optional — leave blank to disable)
GROQ_API_KEY=
OPENROUTER_API_KEY=
```

### 5. Create the PostgreSQL database

Open `psql` or pgAdmin and run:

```sql
CREATE DATABASE metainfo;
```

If you have a legacy SQL dump file (e.g. `metainfo_23_feb2026.sql`), restore it:

```bash
psql -U postgres -d metainfo -f metainfo_23_feb2026.sql
```

### 6. Run Django migrations

```bash
python manage.py migrate
```

### 7. Create the cache table

```bash
python manage.py createcachetable
```

### 8. Import legacy data into Django

This copies data from the legacy PostgreSQL tables into Django's models:

```bash
python manage.py import_legacy_data
```

Or use the master setup script (imports users + datasets + links submitters):

```bash
python setup_complete.py
```

> This may take 5–10 minutes. You should see ~947 datasets imported.

### 9. Create an admin account

```bash
python manage.py createsuperuser
```

### 10. Start the server

```bash
python manage.py runserver
```

Open **http://localhost:8000** in your browser. ✅

---

## Verify Everything Works

```bash
python manage.py shell
```

```python
from data_submission.models import DatasetSubmission
print('Total published:', DatasetSubmission.objects.filter(status='published').count())
```

Expected: **~947 datasets**

---

## Project Structure

```
npdc/
├── npdc_site/          # Django settings, URLs, WSGI
├── data_submission/    # Dataset models, forms, views
├── users/              # User auth, profiles, dashboard
├── npdc_search/        # Search & AI-powered search
├── chatbot/            # AI chatbot assistant
├── activity_logs/      # User activity tracking
├── templates/          # HTML templates
├── static/             # CSS, JS, images
├── media/              # Uploaded files
├── setup_complete.py   # Master import script
└── requirements.txt    # Python dependencies
```

---

## Common Commands

| Task | Command |
|------|---------|
| Start server | `python manage.py runserver` |
| Run migrations | `python manage.py migrate` |
| Create admin | `python manage.py createsuperuser` |
| Import legacy data | `python manage.py import_legacy_data` |
| Open DB shell | `python manage.py dbshell` |
| Collect static files | `python manage.py collectstatic` |

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `ModuleNotFoundError` | Make sure venv is activated and run `pip install -r requirements.txt` |
| `psycopg2` install fails | Install Visual C++ Build Tools (Windows) or use `psycopg2-binary` |
| Website shows 0 datasets | Run `python manage.py import_legacy_data` |
| `django_cache_table` error | Run `python manage.py createcachetable` |
| Port 8000 in use | Use `python manage.py runserver 8001` |
| No module `dotenv` | Run `pip install python-dotenv` |

---

## Reset & Reimport

To wipe all data and reimport from scratch:

```bash
python manage.py flush --noinput
python manage.py import_legacy_data
```

Or with full setup:

```bash
python manage.py flush --noinput
python setup_complete.py
```
