"use client";

import { getSession, signIn } from "next-auth/react";
import { useState, Suspense, FormEvent } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { FileText, AlertCircle } from "lucide-react";
import { ThemeToggle } from "@/components/ThemeToggle";
import { isProfileOnboardingSkipped } from "@/lib/onboarding";
import styles from "./page.module.css";
import Link from "next/link";

function LoginContent() {
  const [isLoading, setIsLoading] = useState<string | null>(null);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [formError, setFormError] = useState<string | null>(null);
  const searchParams = useSearchParams();
  const router = useRouter();
  const error = searchParams.get("error");

  const handleOAuthLogin = async (provider: string) => {
    setFormError(null);
    setIsLoading(provider);
    try {
      await signIn(provider, { callbackUrl: "/dashboard" });
    } catch (err) {
      console.error("Login error:", err);
      setIsLoading(null);
    }
  };

  const handleCredentialsLogin = async (e: FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setIsLoading("credentials");
    try {
      const result = await signIn("credentials", {
        email: email.trim(),
        password,
        redirect: false,
      });
      if (result?.error) {
        setFormError("Invalid email or password.");
        setIsLoading(null);
        return;
      }
      const nextSession = await getSession();
      const userId = nextSession?.user?.id;
      const shouldOnboard =
        (nextSession as any)?.hasProfile === false &&
        !isProfileOnboardingSkipped(userId);
      router.push(shouldOnboard ? "/profile?onboarding=1" : "/dashboard");
      router.refresh();
    } catch (err) {
      console.error("Login error:", err);
      setFormError("Unable to sign in right now. Please try again.");
      setIsLoading(null);
    }
  };

  const bannerMessage =
    formError ||
    (error === "SessionExpired"
      ? "Your session expired. Sign in again to continue."
      : error === "CredentialsSignin"
        ? "Invalid email or password."
        : null);

  return (
    <div className={styles.container}>
      <div className={styles.card}>
        <div className={styles.topRow}>
          <Link href="/" className={styles.logo}>
            <FileText size={22} strokeWidth={1.75} className={styles.logoIcon} />
            <span className={styles.logoText}>CVBuilder</span>
            <span className={styles.logoTag}>ATS</span>
          </Link>
          <ThemeToggle />
        </div>

        <h1 className={styles.title}>Sign in to your workspace</h1>
        <p className={styles.subtitle}>
          Import your base resume once and generate role-targeted PDFs.
        </p>

        {bannerMessage && (
          <div className={styles.errorBanner}>
            <AlertCircle size={16} strokeWidth={1.75} />
            <span>{bannerMessage}</span>
          </div>
        )}

        <form onSubmit={handleCredentialsLogin} className={styles.form}>
          <div className={styles.formGroup}>
            <label htmlFor="email" className={styles.label}>
              Email
            </label>
            <input
              id="email"
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              className={styles.input}
              disabled={!!isLoading}
            />
          </div>

          <div className={styles.formGroup}>
            <label htmlFor="password" className={styles.label}>
              Password
            </label>
            <input
              id="password"
              type="password"
              required
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className={styles.input}
              disabled={!!isLoading}
            />
          </div>

          <button
            type="submit"
            className={styles.submitBtn}
            disabled={!!isLoading}
          >
            {isLoading === "credentials" && <span className={styles.spinner} />}
            <span>{isLoading === "credentials" ? "Signing in…" : "Sign in"}</span>
          </button>
        </form>

        <div className={styles.divider}>
          <span>or continue with</span>
        </div>

        <div className={styles.providerList}>
          <button
            type="button"
            className={styles.providerButton}
            onClick={() => handleOAuthLogin("google")}
            disabled={!!isLoading}
          >
            {isLoading === "google" ? (
              <span className={styles.spinner} />
            ) : (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
                <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
                <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.16v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.16C1.43 8.55 1 10.22 1 12s.43 3.45 1.16 4.93l3.68-2.84z" fill="#FBBC05"/>
                <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.16 7.07l3.68 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
              </svg>
            )}
            <span>{isLoading === "google" ? "Redirecting to Google…" : "Continue with Google"}</span>
          </button>

          <button
            type="button"
            className={styles.providerButton}
            onClick={() => handleOAuthLogin("github")}
            disabled={!!isLoading}
          >
            {isLoading === "github" ? (
              <span className={styles.spinner} />
            ) : (
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
                <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
              </svg>
            )}
            <span>{isLoading === "github" ? "Redirecting to GitHub…" : "Continue with GitHub"}</span>
          </button>
        </div>

        <div className={styles.footerStack}>
          <p className={styles.footerTextCompact}>
            Don&apos;t have an account?{" "}
            <Link href="/register" className={styles.footerLink}>
              Create one
            </Link>
          </p>
          <p className={styles.footerTextCompact}>
            Just testing a resume?{" "}
            <Link href="/ats-checker" className={styles.footerLink}>
              Run a free ATS check without signing in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<div className={styles.container} />}>
      <LoginContent />
    </Suspense>
  );
}
