# CVBuilder AI — Backend Service

The backend of **CVBuilder AI** is a high-performance asynchronous REST API built with **FastAPI**, **LangChain/LangGraph**, and **SQLAlchemy**. It powers resume parsing, profile management, ATS-tailored CV generation using Google Gemini, and PDF document generation.

---

## 1. Summary

CVBuilder AI's backend acts as the core orchestration and intelligence engine:
- **Authentication & OAuth Bridge**: Verifies NextAuth OAuth tokens, syncs user records, and issues rotated JWT access/refresh token pairs.
- **Intelligent Resume Ingestion**: Extracts text from PDF resumes using PyMuPDF and parses unstructured text into normalized profile data using Google Gemini structured outputs.
- **Candidate Profile Storage**: Stores candidate profiles in PostgreSQL with JSONB columns for flexible querying and manual updates.
- **Job Analysis & CV Tailoring**: Uses LangGraph to analyze job descriptions, extract ATS keywords, and tailor resume bullet points to the target role without hallucinating experiences.
- **ATS-Friendly PDF Rendering**: Uses Jinja2 templates and WeasyPrint to generate clean, single-column, ATS-parsable PDF resumes.
- **Security & Reliability**: Features IP-based rate limiting via SlowAPI, HTML sanitization via Bleach, strict security headers, and user-isolated file storage.

---

## 2. System Design & Architecture

### High-Level Architecture

```
[ Frontend (Next.js) ]
         │ (HTTP / JSON / JWT)
         ▼
┌─────────────────────────────────────────────────────────────┐
│ FastAPI Application (app.main:app)                          │
│                                                             │
│  ├── Middleware (CORS, Rate Limiter, Security Headers)      │
│  │                                                          │
│  ├── API Routers (/api)                                     │
│  │    ├── /auth     ──> Token verification, JWT issuance    │
│  │    ├── /resume   ──> PDF upload & parsing orchestration  │
│  │    ├── /profile  ──> Candidate profile CRUD              │
│  │    └── /cv       ──> Tailoring & PDF download            │
│  │                                                          │
│  ├── AI Agents (LangGraph + Gemini)                         │
│  │    ├── resume_agent: PDF text -> Gemini -> ResumeProfile │
│  │    └── cv_agent: Job desc + Profile -> TailoredCV        │
│  │                                                          │
│  ├── Services & Utilities                                   │
│  │    ├── pdf_builder: Jinja2 + WeasyPrint HTML to PDF      │
│  │    ├── auth_service: User upsert & OAuth link            │
│  │    └── file_handler: User-isolated file storage          │
│  │                                                          │
│  └── Persistence (SQLAlchemy 2.0 Async + asyncpg)           │
│       └── Models: User, OAuthAccount, Profile, GeneratedCV  │
└─────────────────────────────────────────────────────────────┘
         │
         ▼
[ PostgreSQL 16 Database ]
```

---

### Directory Structure

```
backend/
├── alembic/                  # Database migration scripts
│   └── versions/             # Migration revision files
├── alembic.ini               # Alembic configuration
├── app/
│   ├── agents/               # LangGraph AI state machines
│   │   ├── resume_agent.py   # PDF text extraction & structured profile parsing
│   │   └── cv_agent.py       # Job description analysis & CV tailoring
│   ├── api/                  # FastAPI router endpoints
│   │   ├── auth.py           # /api/auth (verify, refresh, me)
│   │   ├── cv.py             # /api/cv (generate, history, download)
│   │   ├── profile.py        # /api/profile (get, update)
│   │   └── resume.py         # /api/resume (upload)
│   ├── models/               # SQLAlchemy ORM models
│   │   ├── user.py           # User & OAuthAccount models
│   │   ├── profile.py        # Profile model with JSONB resume sections
│   │   └── generated_cv.py   # GeneratedCV model with tailored content & ATS score
│   ├── schemas/              # Pydantic v2 validation & LLM schemas
│   │   ├── cv.py             # TailoredCV, JobRequirements, CVResponse
│   │   ├── profile.py        # ResumeProfile, WorkExperience, Education, etc.
│   │   └── user.py           # UserResponse, OAuthVerifyRequest, TokenResponse
│   ├── security/             # Security & protection mechanisms
│   │   ├── jwt.py            # Access/refresh token generation & validation
│   │   ├── rate_limiter.py   # SlowAPI rate limiting configuration
│   │   └── sanitizer.py      # Input sanitation (bleach) & path traversal guards
│   ├── services/             # Core business logic
│   │   ├── auth_service.py   # OAuth user creation and credential linking
│   │   └── pdf_builder.py    # Jinja2 template rendering + WeasyPrint PDF compiler
│   ├── templates/            # HTML/CSS templates for generated CVs
│   │   └── cv_template.html  # Strict ATS-compliant single-column template
│   ├── utils/
│   │   └── file_handler.py   # Secure file upload validation and directory routing
│   ├── config.py             # Pydantic Settings loaded from .env
│   ├── database.py           # Async SQLAlchemy engine & session factory
│   └── main.py               # Application entrypoint & middleware configuration
├── requirements.txt          # Python dependencies
└── .env.example              # Environment variables template
```

---

### LangGraph Agent Workflows

#### 1. Resume Parsing Workflow (`resume_agent.py`)
```mermaid
stateDiagram-v2
    [*] --> extract_text: Upload PDF file path
    extract_text --> router: Extracted text
    router --> parse_with_llm: Valid text extracted
    router --> [*]: Error (unreadable or empty PDF)
    parse_with_llm --> [*]: Structured ResumeProfile schema returned
```
- **Node `extract_text`**: Uses PyMuPDF (`fitz`) to extract raw text content from the uploaded document.
- **Node `parse_with_llm`**: Invokes Google Gemini using `.with_structured_output(ResumeProfile)` to reliably extract personal info, work experience, education, skills, certifications, and projects.

#### 2. CV Tailoring Workflow (`cv_agent.py`)
```mermaid
stateDiagram-v2
    [*] --> analyze_job: Job Description + Candidate Profile
    analyze_job --> router: Extracted JobRequirements
    router --> generate_cv: Job requirements parsed
    router --> [*]: Error analyzing job description
    generate_cv --> [*]: TailoredCV with ATS score & tailored bullets
```
- **Node `analyze_job`**: Extracts hard skills, soft skills, responsibilities, and target ATS keywords.
- **Node `generate_cv`**: Re-aligns candidate achievements, enhances bullet points to incorporate relevant keywords, adjusts section order (e.g. fresh graduates vs senior professionals), and scores overall ATS alignment (0-100).
- **Constraint**: The prompt strictly prohibits hallucination or inventing unearned candidate experience.

---

### Database Schema (PostgreSQL)

- **`users`**: Core user accounts (`id`, `email`, `name`, `avatar_url`, `is_active`, timestamps).
- **`oauth_accounts`**: OAuth provider links (`provider`, `provider_account_id`, `access_token`, `user_id` FK).
- **`profiles`**: Structured candidate data linked 1-to-1 to users (`personal_info`, `work_experiences`, `education`, `skills`, `certifications`, `projects` stored as `JSONB`, plus `raw_resume_text`).
- **`generated_cvs`**: Generated versions linked to users (`job_title`, `company_name`, `job_description`, `tailored_content` JSONB, `pdf_file_path`, `ats_score`, timestamps).

---

## 3. Environment Variables

Create a `.env` file in the `backend/` directory by copying `.env.example`:

```bash
cp .env.example .env
```

| Variable | Type | Default / Example | Description |
|---|---|---|---|
| `DATABASE_URL` | String | `postgresql+asyncpg://cvbuilder:cvbuilder_secret@localhost:5433/cvbuilder_db` | Async PostgreSQL connection string. |
| `JWT_SECRET_KEY` | String | *Required in production* | Secret key used to sign and verify JWT tokens. |
| `JWT_ALGORITHM` | String | `HS256` | Algorithm for signing JWTs. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Integer | `15` | Expiry duration for access tokens. |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Integer | `7` | Expiry duration for refresh tokens. |
| `FRONTEND_URL` | String | `http://localhost:3000` | Allowed origin for CORS middleware. |
| `GOOGLE_API_KEY` | String | *Required* | Google AI Gemini API Key for LLM operations. |
| `UPLOAD_DIR` | String | `uploads` | Directory for temporary resume uploads. |
| `GENERATED_DIR` | String | `generated` | Directory for generated PDF CVs. |
| `MAX_UPLOAD_SIZE_MB` | Integer | `10` | Maximum allowed file upload size in MB. |

---

## 4. Setup & Local Development

### Prerequisites
- Python 3.11+
- PostgreSQL 16 (or Docker Compose running postgres)
- Google Gemini API key
- System libraries for WeasyPrint (Cairo, Pango, GDK-PixBuf):
  - **macOS**: `brew install pango cairo libffi`
  - **Ubuntu/Debian**: `sudo apt-get install libpango-1.0-0 libharfbuzz0b libpangoft2-1.0-0 libffi-dev`
  - **Windows**: Install GTK3 runtime or run via WSL2/Docker.

### Step-by-Step Instructions

1. **Create and Activate Virtual Environment**:
   ```bash
   python -m venv .venv
   
   # Linux/macOS
   source .venv/bin/activate

   # Windows (PowerShell)
   .venv\Scripts\Activate.ps1
   ```

2. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment Variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your DATABASE_URL and GOOGLE_API_KEY
   ```

4. **Run Database Migrations**:
   ```bash
   alembic upgrade head
   ```

5. **Start FastAPI Development Server**:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

6. **Interactive API Documentation**:
   - Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
   - ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)
   - Health check: [http://localhost:8000/health](http://localhost:8000/health)
