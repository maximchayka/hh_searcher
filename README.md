# JobAutoApply

A web application for automated job search and auto-application via hh.ru API.

## Tech Stack

- **Backend:** FastAPI (Python 3.11)
- **Frontend:** React 18 + TypeScript + Vite
- **Database:** PostgreSQL 15
- **Queue/Scheduler:** Redis + Celery + Celery Beat
- **Containerization:** Docker + Docker Compose

## Project Structure

```
hh_searcher/
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── api/             # API route handlers
│   │   ├── core/            # Config, security, dependencies
│   │   ├── models/          # SQLAlchemy ORM models
│   │   ├── schemas/         # Pydantic schemas
│   │   ├── services/        # Business logic
│   │   ├── tasks/           # Celery tasks
│   │   └── main.py
│   ├── alembic/             # DB migrations
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                # React frontend
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/        # API clients
│   │   └── store/           # State management
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
└── .env.example
```

## Getting Started

### Prerequisites

- Docker & Docker Compose
- Node.js 18+ (for local frontend dev)
- Python 3.11+ (for local backend dev)

### Run with Docker Compose

```bash
cp .env.example .env
# Edit .env with your hh.ru OAuth credentials
docker compose up --build
```

The app will be available at:
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

### Local Development

**Backend:**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

## Features

- hh.ru OAuth 2.0 integration
- Resume import & management
- Advanced job search constructor with saved templates
- Mass vacancy selection & one-click apply
- Cover letter templates with variable substitution
- AI-powered cover letter generation (optional)
- Automated periodic job monitoring & auto-apply
- Anti-spam controls: daily limits, random delays, duplicate protection
- Application history & analytics

## Configuration

See `.env.example` for all required environment variables.

Key settings:
- `HH_CLIENT_ID` / `HH_CLIENT_SECRET` — hh.ru OAuth app credentials
- `DATABASE_URL` — PostgreSQL connection string
- `REDIS_URL` — Redis connection string
- `SECRET_KEY` — JWT secret key

## Legal Notice

This tool is for personal use only. Automated applications may violate
hh.ru Terms of Service. Use responsibly and at your own risk. Ensure
compliance with hh.ru API usage policies.
