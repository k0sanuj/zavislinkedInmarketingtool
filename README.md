# Zavis LinkedIn Marketing Tool

A PhantomBuster-like platform for scraping LinkedIn company data and employee contacts in the healthcare industry. Built with a Palantir ontology-based database architecture.

## What It Does

1. **Connect a data source** — Google Sheet, CSV upload, or manual URL list containing clinic/company names
2. **Resolve LinkedIn URLs** — Automatically searches Google and LinkedIn to find each company's LinkedIn page
3. **Scrape employee data** — Extracts employee profiles (name, title, location, LinkedIn URL) from each company
4. **AI role matching** — Uses LLM (Claude or GPT) to match employees against target job titles
5. **Report results** — Shows which companies were found, close matches, and companies not found
6. **Schedule recurring runs** — Run once or schedule daily/weekly/monthly scraping

## Architecture

| Component | Technology |
|-----------|-----------|
| Backend API | Python + FastAPI |
| Database | PostgreSQL (Palantir Ontology schema) |
| Task Queue | Celery + Redis |
| LinkedIn Scraping | httpx + BeautifulSoup |
| Google Sheets | gspread |
| AI Matching | Anthropic Claude / OpenAI GPT |
| Frontend | React + Vite |

## Quick Start

### With Docker (recommended)

```bash
cp .env.example .env
# Edit .env with your credentials
docker-compose up -d
```

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Manual Setup

#### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set up PostgreSQL and Redis, then:
alembic upgrade head
uvicorn app.main:app --reload
```

#### Celery Worker (for async scraping)

```bash
cd backend
celery -A app.tasks.celery_app worker --loglevel=info
```

#### Celery Beat (for scheduled jobs)

```bash
cd backend
celery -A app.tasks.celery_app beat --loglevel=info
```

#### Frontend

```bash
cd frontend
npm install
npm run dev
```

## Prerequisites / External Setup Required

1. **PostgreSQL** — database for the ontology
2. **Redis** — message broker for Celery task queue
3. **Google Cloud Service Account** — for Google Sheets API access:
   - Create a project in Google Cloud Console
   - Enable Google Sheets API and Google Drive API
   - Create a service account and download `credentials.json`
   - Share your Google Sheets with the service account email
4. **LinkedIn Cookies** — for authenticated scraping:
   - Log into LinkedIn Sales Navigator in your browser
   - Extract `li_at` and `JSESSIONID` cookies from browser DevTools
   - Enter these when connecting an account in the UI
5. **AI API Key** (optional) — for role matching:
   - Anthropic API key (`ANTHROPIC_API_KEY`) or
   - OpenAI API key (`OPENAI_API_KEY`)

## Database: Palantir Ontology Model

The database follows Palantir ontology principles where every entity is a typed Object with properties, and relationships are first-class Link Types:

```
ScraperJob ──uses──> DataSource ──contains──> Company ──resolved_to──> CompanyLinkedIn
    │                                                                       │
    ├──authenticated_by──> LinkedInAccount                           has_employees
    │                                                                       │
    └──scheduled_by──> Schedule                                       Employee
                                                                           │
                                                                    evaluated_by
                                                                           │
                                                                     MatchResult
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/linkedin-accounts` | Connect LinkedIn account |
| GET | `/api/v1/linkedin-accounts` | List accounts |
| POST | `/api/v1/data-sources` | Create data source (Google Sheet) |
| POST | `/api/v1/data-sources/upload-csv` | Upload CSV data source |
| POST | `/api/v1/scraper-jobs` | Create scraper job |
| POST | `/api/v1/scraper-jobs/{id}/launch` | Launch scraping |
| POST | `/api/v1/scraper-jobs/{id}/pause` | Pause job |
| GET | `/api/v1/scraper-jobs/{id}/summary` | Get results summary |
| GET | `/api/v1/scraper-jobs/{id}/employees` | Get scraped employees |
| POST | `/api/v1/ai/suggest-roles` | AI role suggestions |
