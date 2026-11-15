# Backend Agent Rules & Engineering Guidelines

This document defines the mandatory coding standards, architectural boundaries, and security rules for AI agents working in the `backend/` workspace (FastAPI, SQLAlchemy 2.x Async, Pydantic v2, LangGraph/LangChain, WeasyPrint, PyMuPDF).

---

## 1. Architecture & Separation of Concerns

Keep a strict boundary between layers under `app/`:

- **`app/api/` (Routes / Controllers)**: Handle HTTP request parsing, dependency injection (`Depends(get_db)`, `Depends(get_current_user)`), rate limiting, and HTTP status/response mapping. Keep route handlers thin—delegate business logic, AI workflows, and PDF processing to dedicated modules.
- **`app/schemas/` (Pydantic v2 Models)**: Define all request payloads, response contracts, and structured LLM outputs. Never expose SQLAlchemy ORM models directly in API responses.
- **`app/models/` (SQLAlchemy 2.x ORM)**: Define database tables, relationships, indexes, and constraints only.
- **`app/agents/` (LangGraph & LLM Workflows)**: Encapsulate prompt engineering, state graphs (`StateGraph`), and structured LLM invocations. Always obtain LLM clients via `app/agents/llm.py` (`get_llm`, `get_structured_llm`) to preserve automatic model fallbacks.
- **`app/services/` (Domain & Document Services)**: House CPU- or I/O-bound business services such as PDF parsing (`PyMuPDF`) and PDF rendering (`Jinja2` + `WeasyPrint`).
- **`app/security/` (Auth, Crypto & Rate Limiting)**: Centralize JWT encoding/decoding, password hashing, user authentication dependencies, and `slowapi` rate limiters.
- **`app/utils/` (Pure Helpers & Safe File I/O)**: Shared, stateless utilities such as filename sanitization and path resolution.

---

## 2. Clean Code & Python Best Practices

1. **Modern Type Annotations (Python 3.12+)**:
   - Require explicit type hints on all function signatures and return values.
   - Use built-in generic types (`list[str]`, `dict[str, Any]`) and union syntax (`str | None`) instead of legacy `typing.List`, `typing.Dict`, or `typing.Optional`.
   - Use `TypedDict` for LangGraph state definitions.
2. **Pydantic v2 Idioms**:
   - Use `model_validate()`, `model_dump()`, `model_dump_json()`, `@field_validator(..., mode="after")`, and `model_config = {"from_attributes": True}`.
   - Do **not** use deprecated Pydantic v1 methods (`.dict()`, `.json()`, `.from_orm()`, `@validator`, `class Config`).
3. **Async-First & Non-Blocking Execution**:
   - Use `AsyncSession` and `await` for all database operations.
   - **Never block the FastAPI event loop.** Offload synchronous, CPU-heavy, or blocking operations (e.g., `WeasyPrint` PDF generation, `PyMuPDF` parsing, synchronous LangGraph `.invoke()`) using `await asyncio.to_thread(...)`.
4. **SQLAlchemy 2.0 Style**:
   - Use 2.0 `select(...)` statements with `await db.execute(...)`, `.scalar_one_or_none()`, and `.scalars().all()`. Never use legacy `session.query()`.
   - Always use timezone-aware UTC timestamps: `datetime.now(timezone.utc)` (never `datetime.utcnow()`).
5. **Readability & Maintainability**:
   - Keep functions focused on a single responsibility.
   - Prefer early returns / guard clauses over deeply nested conditionals.
   - Replace magic numbers and hardcoded strings with named constants, `Literal` types, or settings in `app/config.py`.
   - Use structured module-level loggers (`logger = logging.getLogger(__name__)`) instead of `print()`.

---

## 3. Security Rules (Mandatory)

Every backend change must uphold the following security invariants:

### 3.1 Authentication, Authorization & IDOR Prevention
- All endpoints accessing user data must require `current_user: User = Depends(get_current_user)`.
- **Strict Ownership Scoping (Anti-IDOR)**: Every query or mutation on user-owned records (`Profile`, `GeneratedCV`, uploaded files, generated PDFs) **must** filter by `Model.user_id == current_user.id` in the SQL `WHERE` clause. Never fetch a resource by primary key (`id`) alone.
- Verify token `type` (`"access"` vs `"refresh"`), validate UUID subjects, and confirm `user.is_active` before granting access.

### 3.2 Input Validation & Injection Defense
- Enforce explicit bounds on all Pydantic request fields (`min_length`, `max_length`, `ge`, `le`, regex patterns, or `Literal` enums) to prevent oversized payloads and resource exhaustion.
- **SQL Injection**: Use parameterized SQLAlchemy ORM expressions exclusively. Never interpolate user input into raw SQL strings.
- **XSS / Template Injection in PDFs**: Always keep Jinja2 autoescaping enabled when rendering HTML templates for `WeasyPrint`, and sanitize untrusted rich text with `bleach` where applicable. Treat `WeasyPrint` URL fetching carefully—never allow untrusted user input to reference arbitrary local `file://` or internal network URLs (SSRF/LFI).
- **Prompt Injection & LLM Safety**:
  - Keep system instructions strictly inside `SystemMessage` and untrusted user data (`job_description`, parsed resume text) inside `HumanMessage`.
  - Enforce schema-constrained decoding via `get_structured_llm(Schema)` so LLM outputs are validated by Pydantic before use.
  - Never fabricate or hallucinate candidate facts, metrics, or credentials not grounded in the user's profile.

### 3.3 File Upload & Filesystem Security
- **MIME & Size Enforcement**: Validate file content type (`application/pdf`) and read uploads in chunks while enforcing `MAX_FILE_SIZE` (`settings.max_upload_size_bytes`); immediately delete partial files and raise `HTTP 413` if exceeded.
- **Path Traversal Prevention**:
  - Always strip directory components with `os.path.basename(...)` and sanitize filenames to a strict allowlist of characters (`[a-zA-Z0-9._-]`).
  - Isolate files inside per-user subdirectories (`uploads/<user_id>/`, `generated/<user_id>/`).
  - Do not leak internal server filesystem paths or storage UUID suffixes in user-facing download filenames.

### 3.4 Rate Limiting, Secrets & Error Handling
- **Rate Limiting**: Apply `@limiter.limit(...)` to all authentication routes and expensive AI/PDF generation endpoints (requires `request: Request` in the endpoint signature).
- **Secret Management**: Load all credentials, API keys (`GOOGLE_API_KEY`, `GROQ_API_KEY`), database URLs, and `JWT_SECRET_KEY` via `app.config.settings` (`pydantic-settings`). Never hardcode secrets, commit `.env` files, or log sensitive tokens/PII.
- **Safe Error Responses**: Never leak stack traces, raw database errors, or internal file paths to clients. Log detailed exceptions server-side with `logger.error(...)` and return sanitized `HTTPException` details to the caller.

---

## 4. Pre-Completion Verification Checklist

Before finalizing any backend changes, verify:
- [ ] All new/modified endpoints enforce `get_current_user` (unless explicitly public) and scope queries by `current_user.id`.
- [ ] Request and response models use Pydantic v2 schemas with strict field constraints and type annotations.
- [ ] Blocking I/O or CPU work (PDF generation/parsing, sync LLM calls) runs in `asyncio.to_thread(...)`.
- [ ] No secrets, raw stack traces, or unsanitized file paths are exposed.
- [ ] Imports are clean, unused code is removed, and existing endpoints remain backward-compatible.

