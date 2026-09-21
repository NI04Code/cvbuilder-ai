# CVBuilder AI

**CVBuilder AI** is a full-stack, AI-powered platform that parses resumes, manages structured candidate profiles, and generates personalized, ATS-optimized CVs tailored to specific job descriptions.

---

## Architecture Overview

CVBuilder AI is structured as a monorepo consisting of:

- **Frontend**: [Next.js 16](https://nextjs.org/) (App Router), React 19, TypeScript, [NextAuth.js v5](https://authjs.dev/), Framer Motion, and CSS Modules. Located in [`frontend/`](frontend/).
- **Backend**: [FastAPI](https://fastapi.tiangolo.com/), [LangChain](https://www.langchain.com/) / [LangGraph](https://langchain-ai.github.io/langgraph/), SQLAlchemy 2.0 (asyncpg), Alembic, and [WeasyPrint](https://weasyprint.org/). Located in [`backend/`](backend/).
- **Database**: PostgreSQL 16 with JSONB support (configured in [`docker-compose.yml`](docker-compose.yml)).
- **LLM**: Google Gemini 2.0 via `langchain-google-genai` for structured profile extraction and CV tailoring.

```
cvbuilder-ai/
├── backend/               # FastAPI + LangGraph + WeasyPrint REST API
│   ├── alembic/           # Database schema migrations
│   ├── app/               # Application logic (agents, api, models, schemas, services)
│   ├── requirements.txt   # Python dependencies
│   ├── .env.example       # Backend environment variables template
│   └── README.md          # Backend system design & architecture documentation
│
├── frontend/              # Next.js 16 + React 19 web application
│   ├── src/               # Application code (app router, components, lib, auth)
│   ├── package.json       # Node.js dependencies
│   ├── .env.example       # Frontend environment variables template
│   └── README.md          # Frontend architecture & page structure documentation
│
└── docker-compose.yml     # PostgreSQL 16 container definition
```

---

## Core Features

- **Automated Resume Ingestion**: Upload PDF resumes and extract structured profiles (contact info, work history, education, skills, certifications, projects) using Google Gemini and LangGraph.
- **Interactive Profile Dashboard**: Review, edit, and supplement parsed resume data through a tabbed dashboard.
- **Targeted ATS Tailoring**: Analyze job descriptions for key requirements and rewrite experience bullets to emphasize relevant skills without hallucinating data.
- **ATS-Compliant PDF Generation**: Generate clean, single-column PDF resumes using Jinja2 and WeasyPrint that pass Applicant Tracking Systems with ease.
- **Secure Authentication**: Social sign-in via Google and GitHub with NextAuth.js v5, synchronized with FastAPI JWT tokens and automated token rotation.

---

## Quick Start Guide

### Prerequisites
- [Python 3.11+](https://www.python.org/downloads/)
- [Node.js 18.17+ or 20+](https://nodejs.org/)
- [Docker & Docker Compose](https://www.docker.com/)
- [Google AI Gemini API Key](https://aistudio.google.com/)

---

### Step 1: Start Database

Start the PostgreSQL 16 database using Docker Compose:

```bash
docker compose up -d
```
*PostgreSQL will be accessible at `localhost:5433` (database: `cvbuilder_db`, user: `cvbuilder`, password: `cvbuilder_secret`).*

---

### Step 2: Setup & Run Backend

1. Navigate to the `backend/` directory:
   ```bash
   cd backend
   ```

2. Create and activate a Python virtual environment:
   ```bash
   python -m venv .venv
   
   # Linux / macOS
   source .venv/bin/activate

   # Windows (PowerShell)
   .venv\Scripts\Activate.ps1
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables:
   ```bash
   cp .env.example .env
   ```
   *Edit `.env` and set your `GOOGLE_API_KEY` and ensure `DATABASE_URL` matches your Postgres instance.*

5. Run database migrations:
   ```bash
   alembic upgrade head
   ```

6. Start the development server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

- API Documentation: [http://localhost:8000/docs](http://localhost:8000/docs)
- Health Check: [http://localhost:8000/health](http://localhost:8000/health)

*For detailed system design, LangGraph workflows, and database schema, see [`backend/README.md`](backend/README.md).*

---

### Step 3: Setup & Run Frontend

1. Navigate to the `frontend/` directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Configure environment variables:
   ```bash
   cp .env.example .env.local
   ```
   *Edit `.env.local` to set `AUTH_SECRET` (`openssl rand -hex 32`), your OAuth credentials, and verify `NEXT_PUBLIC_API_URL=http://localhost:8000/api`.*

4. Start the Next.js development server:
   ```bash
   npm run dev
   ```

- Web App: [http://localhost:3000](http://localhost:3000)

*For detailed frontend architecture, NextAuth token sync, and page routing, see [`frontend/README.md`](frontend/README.md).*

---

## Documentation Links

- **Backend Architecture & System Design**: [`backend/README.md`](backend/README.md)
- **Frontend Architecture & Setup**: [`frontend/README.md`](frontend/README.md)
