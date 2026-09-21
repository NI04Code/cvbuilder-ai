# CVBuilder AI — Frontend Web Application

The frontend of **CVBuilder AI** is a modern, responsive web application built with **Next.js 16 (App Router)**, **React 19**, and **TypeScript**. It delivers a high-performance dashboard for uploading resumes, managing candidate profiles, and generating tailored ATS CVs in real time.

---

## 1. Summary

The frontend application provides:
- **Landing Page**: Modern dark-theme marketing landing page with glassmorphism styling, animated hero, and feature highlights.
- **Social OAuth Authentication**: Seamless sign-in via Google and GitHub powered by NextAuth.js v5.
- **Backend Token Synchronization**: Automated session synchronization with the FastAPI backend, including access token refresh and token rotation.
- **Profile Management**: Tabbed interface enabling candidates to either auto-parse resumes via drag-and-drop PDF upload or manually edit work history, education, skills, and projects.
- **Dual-Panel CV Generator**: Side-by-side view where users paste job descriptions and immediately receive ATS match scores and downloadable PDF CVs.
- **Generated CV History**: Centralized dashboard to view, inspect, and download previously tailored CVs.

---

## 2. Tech Stack

- **Framework**: Next.js 16.3.1 (App Router)
- **Library**: React 19.2.8
- **Language**: TypeScript 5
- **Authentication**: NextAuth.js v5 (`next-auth@5.0.0-beta.32`)
- **Animation**: Framer Motion 13
- **Icons**: Lucide React
- **HTTP Client**: Axios
- **Styling**: Vanilla CSS Modules + CSS Custom Properties (Tokens in `globals.css`)

---

## 3. Architecture & Pages

```
frontend/src/
├── app/
│   ├── (auth)/
│   │   └── login/             # /login — Social login (Google / GitHub)
│   ├── (dashboard)/
│   │   ├── layout.tsx         # Dashboard layout with sidebar navigation & user profile
│   │   ├── dashboard/         # /dashboard — History of generated CVs & download links
│   │   ├── profile/           # /profile — PDF upload dropzone & manual profile editor
│   │   └── generate/          # /generate — Job description form & tailored CV preview
│   ├── api/auth/[...nextauth]/# NextAuth.js API route handler
│   ├── globals.css            # Design tokens, color schemes, and glassmorphism utilities
│   ├── layout.tsx             # Root HTML layout with SessionProvider and Inter font
│   └── page.tsx               # Public landing page
├── components/
│   ├── Providers.tsx          # Client-side NextAuth SessionProvider wrapper
│   └── SessionWatcher.tsx     # Monitors expired sessions and triggers clean logout
├── lib/
│   └── api.ts                 # Configured Axios client pointing to FastAPI
├── auth.config.ts             # Route authorization and redirection rules
├── auth.ts                    # NextAuth provider config & backend JWT sync callbacks
└── middleware.ts              # Edge middleware protecting dashboard routes
```

### Authentication Flow with FastAPI Backend

1. When a user clicks **Continue with Google/GitHub**, NextAuth completes the OAuth handshake.
2. In `src/auth.ts`, the `jwt` callback sends user data to the backend via `POST /api/auth/verify`.
3. The backend stores or updates the user and returns a pair of backend JWTs (`access_token` and `refresh_token`).
4. When the access token reaches expiration, `refreshAccessToken()` calls `POST /api/auth/refresh` on the backend for seamless token rotation.
5. `SessionWatcher` gracefully redirects the user to `/login?error=SessionExpired` if the refresh token expires.

---

## 4. Environment Variables

Create a `.env.local` file in `frontend/` by copying `.env.example`:

```bash
cp .env.example .env.local
```

| Variable | Required | Description |
|---|---|---|
| `AUTH_SECRET` | **Yes** | Secret used to encrypt NextAuth session cookies. Generate with `openssl rand -hex 32` or `npx auth secret`. |
| `AUTH_GOOGLE_ID` | Optional | Google Cloud OAuth 2.0 Client ID. |
| `AUTH_GOOGLE_SECRET` | Optional | Google Cloud OAuth 2.0 Client Secret. |
| `AUTH_GITHUB_ID` | Optional | GitHub OAuth App Client ID. |
| `AUTH_GITHUB_SECRET` | Optional | GitHub OAuth App Client Secret. |
| `NEXT_PUBLIC_API_URL` | **Yes** | Base URL for the FastAPI backend (e.g. `http://localhost:8000/api`). |

> [!NOTE]
> At least one OAuth provider (Google or GitHub) must be configured with valid credentials to enable user sign-in.

---

## 5. Local Development

### Prerequisites
- Node.js 18.17+ or 20+
- npm, pnpm, or yarn
- Backend service running on `http://localhost:8000`

### Step-by-Step Instructions

1. **Install Dependencies**:
   ```bash
   npm install
   ```

2. **Configure Environment Variables**:
   ```bash
   cp .env.example .env.local
   # Fill in AUTH_SECRET, OAuth credentials, and NEXT_PUBLIC_API_URL
   ```

3. **Start Development Server**:
   ```bash
   npm run dev
   ```
   Open [http://localhost:3000](http://localhost:3000) in your browser.

4. **Lint and Validate**:
   ```bash
   npm run lint
   ```

5. **Build for Production**:
   ```bash
   npm run build
   npm run start
   ```
