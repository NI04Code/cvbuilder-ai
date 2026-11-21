# Backend Agent Rules & Engineering Guidelines

This document defines the mandatory coding standards, architectural boundaries, testing workflow, and security rules for AI agents working in the `backend/` workspace (FastAPI, SQLAlchemy 2.x Async, Pydantic v2, LangGraph/LangChain, PyMuPDF, Jinja2).

> **Living Documentation Rule**: Update `AGENTS.md` whenever any feature, module, layer, endpoint, or convention is added, updated, refactored, or deleted. Always create or update unit tests **first** before modifying production code.

---

## 1. Architecture & Separation of Concerns

The backend follows a strict **3-layer architecture** (`api` → `services` → `database`) backed by `core/`, `security/`, `utils/`, `models/`, `schemas/`, and `agents/`:

- **`app/api/` (Layer 1 — HTTP Controllers)**: Handle HTTP request parsing, Pydantic validation, pagination params (`limit`/`offset`), auth dependencies (`Depends(get_current_user)`, `verify_internal_auth_secret`), rate limiting (`@limiter.limit`), upload HTTP checks (MIME, size, `%PDF-` magic bytes), and HTTP responses (`FileResponse`, status codes). Keep route handlers thin—never place business logic or SQLAlchemy `select`/`execute` calls here.
- **`app/services/` (Layer 2 — Business Logic & Orchestration)**: House all business logic, AI agent orchestration, PDF generation orchestration, date sorting, orphan file cleanup, and domain exception raising (`BadRequestError`, `UnauthorizedError`, `NotFoundError`, `GenerationError`). Services must **never** contain raw SQLAlchemy `select(...)`/`db.execute(...)` queries or FastAPI HTTP response construction.
- **`app/database/` (Layer 3 — Session & Repositories)**: Owns all database connectivity and queries:
  - `session.py`: Async engine, `async_session_factory`, `Base`, `get_db()`, and `check_db_connection()`.
  - `user_repo.py`, `profile_repo.py`, `document_repo.py`: All SQLAlchemy 2.x `select`, `add`, `delete`, `flush`, `commit`, and `refresh` operations.
- **`app/core/` (Cross-Cutting Application Primitives)**:
  - `settings.py`: `pydantic-settings` configuration (`Settings`, `settings`), including `validate_production_secrets()`.
  - `logging.py`: Centralized logging (`configure_logging`) with `X-Request-ID` `ContextVar` correlation (`request_id_var`).
  - `exceptions.py`: Domain exceptions (`ServiceError`, `BadRequestError`, `UnauthorizedError`, `NotFoundError`, `GenerationError`) and `register_exception_handlers(app)` (including the global `500` catch-all logger/handler).
  - `middleware.py`: `register_middleware(app)` for CORS, `X-Request-ID` propagation, and HTTP security headers.
- **`app/models/` (SQLAlchemy 2.x ORM)**: Define database tables, relationships, indexes, and constraints only. Keep `User` relationships as `lazy="raise"` to prevent accidental eager/N+1 loading on auth lookups.
- **`app/schemas/` (Pydantic v2 Models)**: Define all request payloads, response contracts, input sanitizers, and structured LLM outputs. Never expose SQLAlchemy ORM models directly in API responses.
- **`app/agents/` (LangGraph & LLM Workflows)**: Encapsulate prompt engineering, `StateGraph` workflows, nodes (`app/agents/node/`), and helpers (`app/agents/helper/`). Always obtain LLM clients via `app/agents/helper/llm_factory.py` (`get_llm`, `get_structured_llm`) to preserve explicit timeouts, retries, and `.with_fallbacks(...)`.
- **`app/security/` (Auth, Crypto, Sanitization & Rate Limiting)**:
  - `jwt.py`: Access/refresh JWT creation/decoding and `get_current_user` (delegating DB lookup to `user_repo`).
  - `encryption.py`: Fernet symmetric encryption (`encrypt_secret`, `decrypt_secret`) for sensitive tokens stored at rest (`OAuthAccount.access_token`).
  - `sanitizer.py`: Input sanitization (`bleach`-based `sanitize_text`), `sanitize_filename`, and `is_pdf_magic_bytes`.
  - `rate_limiter.py`: `slowapi` IP-based `limiter`.
- **`app/utils/` (Reusable Pure Utilities & Safe File I/O)**:
  - `pdf_builder.py`: Stateless A4 PDF rendering using Jinja2 (`autoescape=True`) and `pymupdf.Story`.
  - `file_handler.py`: Non-blocking `aiofiles` upload saving, standardized filename builders, and path-traversal-guarded file deletion.
  - `url.py`: External URL scheme validation (`sanitize_external_url`, blocking `javascript:`, `data:`, `vbscript:`, `file:`) and display helpers.

### System Health & Readiness Endpoints
- `GET /health`: Lightweight liveness probe returning `{"status": "healthy"}`.
- `GET /health/ready`: Readiness probe running `check_db_connection(db)` (`SELECT 1`). Logs failures server-side and returns a generic `503` `{"status": "unavailable"}` without disclosing internal dependency names or errors.

---

## 2. Clean Code & Python Best Practices

1. **Modern Type Annotations (Python 3.12+)**:
   - Require explicit type hints on all function signatures and return values.
   - Use built-in generic types (`list[str]`, `dict[str, Any]`) and union syntax (`str | None`) instead of legacy `typing.List`, `typing.Dict`, or `typing.Optional`.
   - Use `TypedDict` for LangGraph state definitions.
2. **Pydantic v2 Idioms**:
   - Use `model_validate()`, `model_dump()`, `model_dump_json()`, `@field_validator(..., mode="after"|"before")`, and `model_config = {"from_attributes": True}`.
   - Do **not** use deprecated Pydantic v1 methods (`.dict()`, `.json()`, `.from_orm()`, `@validator`, `class Config`).
3. **Async-First & Non-Blocking Execution**:
   - Use `AsyncSession` and `await` for all database operations, and `aiofiles` for async disk writes.
   - **Never block the FastAPI event loop.** Offload synchronous, CPU-heavy, or blocking operations (e.g., `PyMuPDF` parsing/rendering, synchronous LangGraph `.invoke()`, `os`/disk deletion) using `await asyncio.to_thread(...)`.
4. **SQLAlchemy 2.0 Style**:
   - Place all `select(...)` statements inside `app/database/*_repo.py` with `await db.execute(...)`, `.scalar_one_or_none()`, and `.scalars().all()`. Never use legacy `session.query()`.
   - Always use timezone-aware UTC timestamps: `datetime.now(timezone.utc)` (never `datetime.utcnow()`).
5. **Readability & Maintainability**:
   - Keep functions focused on a single responsibility and prefer early returns / guard clauses.
   - Replace magic numbers and hardcoded strings with named constants, `Literal` types, or settings in `app/core/settings.py`.
   - Use structured module-level loggers (`logger = logging.getLogger(__name__)`) instead of `print()`.

---

## 3. Testing Workflow & Mirrored Structure (Mandatory)

1. **Test-First Requirement**: For any new feature, bug fix, or refactor, write or update unit tests **first** before modifying implementation files.
2. **1:1 Mirrored Directory Layout**:
   - Tests under `backend/tests/app/` must mirror `backend/app/` module-for-module (e.g., `app/services/cv_service.py` → `tests/app/services/test_cv_service.py`, `app/database/user_repo.py` → `tests/app/database/test_user_repo.py`).
   - Shared fixtures and entity/schema factories live in `backend/tests/conftest.py`.
3. **Mock External Infrastructure**:
   - Unit tests must run completely isolated from live Postgres, Redis, or LLM APIs: mock `AsyncSession` (`AsyncMock(spec=AsyncSession)`), repository/service functions, `ChatGroq`/LangGraph `.invoke()`, and use `tmp_path` for file I/O.
4. **Running Tests & Coverage**:
   ```powershell
   cd backend
   uv run pytest --cov=app --cov-report=term-missing
   ```

---

## 4. Security Rules (Mandatory)

Every backend change must uphold the following security invariants:

### 4.1 Authentication, Authorization & IDOR Prevention
- All endpoints accessing user data must require `current_user: User = Depends(get_current_user)`.
- Server-to-server `POST /api/auth/verify` calls from NextAuth must pass `verify_internal_auth_secret` (`X-Internal-Auth-Secret` verified with `hmac.compare_digest`).
- **Strict Ownership Scoping (Anti-IDOR)**: Every query or mutation on user-owned records (`Profile`, `GeneratedCV`, `GeneratedCoverLetter`, uploaded/generated PDFs) **must** filter by `Model.user_id == user_id` in the SQL `WHERE` clause via `app/database/` repositories. Never fetch a resource by primary key (`id`) alone.
- Verify token `type` (`"access"` vs `"refresh"`), validate UUID subjects, and confirm `user.is_active` before granting access.
- Encrypt third-party OAuth `access_token` values at rest using `app.security.encryption.encrypt_secret` before persisting to `OAuthAccount`.

### 4.2 Input Validation & Injection Defense
- Enforce explicit bounds on all Pydantic request fields (`min_length`, `max_length`, `ge`, `le`, regex patterns, or `Literal` enums) and sanitize user-supplied text with `app.security.sanitizer.sanitize_text`.
- **SQL Injection**: Use parameterized SQLAlchemy ORM expressions exclusively inside `app/database/`. Never interpolate user input into raw SQL strings.
- **XSS / Template & URL Injection in PDFs**: Always keep Jinja2 `autoescape=True` in `app/utils/pdf_builder.py` and validate external links with `sanitize_external_url` (blocking `javascript:`, `data:`, `vbscript:`, `file:`).
- **Prompt Injection & LLM Safety**:
  - Keep system instructions strictly inside `SystemMessage` and untrusted user data (`job_description`, parsed resume text) inside `HumanMessage`.
  - Enforce schema-constrained decoding via `get_structured_llm(Schema)` so LLM outputs are validated by Pydantic before use.
  - Never fabricate or hallucinate candidate facts, metrics, or credentials not grounded in the user's profile.

### 4.3 File Upload & Filesystem Security
- **MIME, Magic-Byte & Size Enforcement**: Validate both `content_type == "application/pdf"` and `%PDF-` magic bytes (`is_pdf_magic_bytes`), enforce `MAX_FILE_SIZE` (`10 MB`), clean up partial/orphan files on overflow or parse failure, and return `HTTP 413` if exceeded.
- **Path Traversal Prevention**:
  - Strip directory components with `os.path.basename(...)`, sanitize filenames to `[a-zA-Z0-9._- ]`, and verify `target.is_relative_to(user_dir)` before deleting generated files.
  - Isolate files inside per-user subdirectories (`uploads/<user_id>/`, `generated/<user_id>/`).
  - Do not leak internal server filesystem paths or storage UUID suffixes in user-facing download filenames.

### 4.4 Rate Limiting, Secrets & Error Handling
- **Rate Limiting**: Apply `@limiter.limit(...)` to authentication routes, public `/api/ats-checker/analyze`, and expensive AI/PDF generation endpoints (requires `request: Request` in the endpoint signature).
- **Secret Management**: Load all credentials, API keys (`GOOGLE_API_KEY`, `GROQ_API_KEY`), `DATABASE_URL`, `JWT_SECRET_KEY`, `INTERNAL_AUTH_SECRET`, and `OAUTH_TOKEN_ENCRYPTION_KEY` via `app.core.settings`. Never hardcode secrets, commit `.env` files, or log sensitive tokens/PII. Production startup must pass `settings.validate_production_secrets()`.
- **Safe Error Responses**: Never leak stack traces, raw database errors, or internal file paths to clients. Log exceptions server-side with request-ID correlation and return sanitized error responses via `app/core/exceptions.py`.

---

## 5. Pre-Completion Verification Checklist

Before finalizing any backend changes, verify:
- [ ] Unit tests were written/updated **first** in the matching mirrored `backend/tests/app/...` path, and `uv run pytest --cov=app --cov-report=term-missing` passes.
- [ ] `backend/AGENTS.md` is updated to reflect any added, modified, refactored, or deleted features/architecture.
- [ ] Layer boundaries hold (`api` → `services` → `database`; zero raw SQLAlchemy queries in `api/` or `services/`).
- [ ] All new/modified endpoints enforce `get_current_user` (unless explicitly public), scope queries by `current_user.id`, and paginate list endpoints (`limit`/`offset`).
- [ ] Blocking I/O or CPU work (PDF generation/parsing, sync LLM calls) runs in `asyncio.to_thread(...)`, and file uploads use `aiofiles` with magic-byte & size checks.
- [ ] No secrets, plaintext OAuth tokens, raw stack traces, or unsanitized file paths are exposed.
