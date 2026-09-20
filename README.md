# JobSeek AI

AI-powered platform that generates personalized, ATS-optimized CVs from your resume and target job descriptions.

## Architecture

- **Frontend**: Next.js 15 + TypeScript (in `frontend/`)
- **Backend**: FastAPI + LangChain/LangGraph (in `backend/`)
- **Database**: PostgreSQL 16
- **LLM**: Google Gemini 2.0 Flash

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- Google API Key (for Gemini)

### 1. Start Database
```bash
docker compose up -d
```

### 2. Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Edit with your settings
alembic upgrade head   # Run migrations
uvicorn app.main:app --reload --port 8000
```

### 3. Frontend
```bash
cd frontend
npm install
cp .env.example .env.local  # Edit with your settings
npm run dev
```

## API Docs
Once the backend is running: http://localhost:8000/docs
