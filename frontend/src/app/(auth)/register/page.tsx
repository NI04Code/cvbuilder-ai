"use client";

import { signIn } from "next-auth/react";
import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import { AxiosError } from "axios";
import { FileText, AlertCircle } from "lucide-react";
import { ThemeToggle } from "@/components/ThemeToggle";
import { apiClient } from "@/lib/api";
import styles from "../login/page.module.css";
import Link from "next/link";

function extractApiError(err: unknown): string {
  const axiosErr = err as AxiosError<{
    detail?: string | Array<{ msg?: string }>;
  }>;
  const detail = axiosErr.response?.data?.detail;
  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }
  if (Array.isArray(detail) && detail.length > 0) {
    const messages = detail
      .map((item) => item?.msg)
      .filter((msg): msg is string => Boolean(msg));
    if (messages.length > 0) {
      return messages.join(" ");
    }
  }
  return "Unable to create account right now. Please try again.";
}

export default function RegisterPage() {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);

    const trimmedName = name.trim();
    const trimmedEmail = email.trim();

    if (!trimmedName) {
      setError("Please enter your name.");
      return;
    }
    if (password.length < 8 || password.length > 72) {
      setError("Password must be between 8 and 72 characters.");
      return;
    }
    if (!/[A-Za-z]/.test(password) || !/\d/.test(password)) {
      setError("Password must contain at least one letter and one digit.");
      return;
    }
    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setIsSubmitting(true);
    try {
      await apiClient.post("/auth/register", {
        name: trimmedName,
        email: trimmedEmail,
        password,
      });

      const signInResult = await signIn("credentials", {
        email: trimmedEmail,
        password,
        redirect: false,
      });

      if (signInResult?.error) {
        router.push("/login");
        return;
      }

      router.push("/profile?onboarding=1");
      router.refresh();
    } catch (err) {
      setError(extractApiError(err));
      setIsSubmitting(false);
    }
  };

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

        <h1 className={styles.title}>Create your account</h1>
        <p className={styles.subtitle}>
          Register with email and password to build tailored resumes and track ATS checks.
        </p>

        {error && (
          <div className={styles.errorBanner}>
            <AlertCircle size={16} strokeWidth={1.75} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} className={styles.form}>
          <div className={styles.formGroup}>
            <label htmlFor="name" className={styles.label}>
              Full name
            </label>
            <input
              id="name"
              type="text"
              required
              maxLength={255}
              autoComplete="name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Jane Doe"
              className={styles.input}
              disabled={isSubmitting}
            />
          </div>

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
              disabled={isSubmitting}
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
              minLength={8}
              maxLength={72}
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="At least 8 characters, with a letter & digit"
              className={styles.input}
              disabled={isSubmitting}
            />
          </div>

          <div className={styles.formGroup}>
            <label htmlFor="confirmPassword" className={styles.label}>
              Confirm password
            </label>
            <input
              id="confirmPassword"
              type="password"
              required
              minLength={8}
              maxLength={72}
              autoComplete="new-password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Re-enter your password"
              className={styles.input}
              disabled={isSubmitting}
            />
          </div>

          <button
            type="submit"
            className={styles.submitBtn}
            disabled={isSubmitting}
          >
            {isSubmitting && <span className={styles.spinner} />}
            <span>{isSubmitting ? "Creating account…" : "Create account"}</span>
          </button>
        </form>

        <div className={styles.footerStack}>
          <p className={styles.footerTextCompact}>
            Already have an account?{" "}
            <Link href="/login" className={styles.footerLink}>
              Sign in
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
