"use client";

import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { FileSignature, Download, Plus, Target, Trash2, AlertCircle } from "lucide-react";
import Link from "next/link";
import { apiClient, extractDownloadFilename } from "@/lib/api";
import { useCVGeneration } from "@/context/CVGenerationContext";
import styles from "./page.module.css";

export default function DashboardPage() {
  const { data: session, status } = useSession();
  const { clearGeneratedCvIfMatches } = useCVGeneration();
  const [history, setHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchHistory() {
      if (status !== "authenticated") return;
      try {
        const token = (session as any)?.backendAccessToken;
        const res = await apiClient.get("/cv/history", {
          headers: { Authorization: `Bearer ${token}` },
        });
        setHistory(res.data);
      } catch (err) {
        console.error("Failed to fetch CV history", err);
      } finally {
        setLoading(false);
      }
    }
    fetchHistory();
  }, [session, status]);

  const handleDownload = async (cvId: string, companyName: string) => {
    if (downloadingId) return;
    setDownloadingId(cvId);
    try {
      const token = (session as any)?.backendAccessToken;
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/cv/${cvId}/download`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = extractDownloadFilename(
          res.headers.get("content-disposition"),
          companyName,
          session?.user?.name
        );
        a.click();
        window.URL.revokeObjectURL(url);
      }
    } catch (err) {
      console.error("Download failed", err);
    } finally {
      setDownloadingId(null);
    }
  };

  const handleDelete = async (cvId: string) => {
    if (deletingId) return;
    setDeletingId(cvId);
    setActionError(null);
    try {
      const token = (session as any)?.backendAccessToken;
      await apiClient.delete(`/cv/${cvId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setHistory((prev) => prev.filter((item) => item.id !== cvId));
      clearGeneratedCvIfMatches(cvId);
      setConfirmDeleteId(null);
    } catch (err: any) {
      console.error("Delete failed", err);
      setActionError(err.response?.data?.detail || "Failed to delete CV. Please try again.");
    } finally {
      setDeletingId(null);
    }
  };

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Tailored CVs</h1>
          <p className={styles.subtitle}>
            {loading
              ? "Loading your generated resumes…"
              : history.length > 0
                ? `${history.length} role-targeted resume${history.length > 1 ? "s" : ""} ready for download.`
                : "Paste a job description to generate your first role-targeted PDF resume."}
          </p>
        </div>
        <div className={styles.headerActions}>
          <Link href="/ats-checker" className={styles.secondaryBtn}>
            <Target size={16} strokeWidth={1.75} />
            <span>Check ATS Score</span>
          </Link>
          <Link href="/generate" className={styles.generateBtn}>
            <Plus size={16} strokeWidth={2} />
            <span>Tailor New CV</span>
          </Link>
        </div>
      </header>

      {actionError && (
        <div className={styles.errorBanner} role="alert">
          <AlertCircle size={16} strokeWidth={1.75} />
          <span>{actionError}</span>
        </div>
      )}

      <section>
        {loading ? (
          <div className={styles.skeletonList} aria-label="Loading CVs">
            {[0, 1, 2].map((i) => (
              <div key={i} className={styles.skeletonRow}>
                <div className={styles.skeletonLeft}>
                  <div className={styles.skeletonTitle} />
                  <div className={styles.skeletonSub} />
                </div>
                <div className={styles.skeletonRight}>
                  <div className={styles.skeletonBadge} />
                  <div className={styles.skeletonBtn} />
                </div>
              </div>
            ))}
          </div>
        ) : history.length > 0 ? (
          <div className={styles.cvList}>
            {history.map((cv: any) => {
              const score = cv.ats_score != null ? Math.round(cv.ats_score) : null;
              const tier =
                score != null
                  ? score >= 80
                    ? "high"
                    : score >= 60
                      ? "mid"
                      : "low"
                  : null;
              const isDownloading = downloadingId === cv.id;

              return (
                <div key={cv.id} className={styles.cvCard}>
                  <div className={styles.cvPrimary}>
                    <div className={styles.cvIconBox}>
                      <FileSignature size={18} strokeWidth={1.75} />
                    </div>
                    <div className={styles.cvText}>
                      <span className={styles.cvRole}>
                        {cv.job_title || "Tailored Resume"}
                      </span>
                      <span className={styles.cvMeta}>
                        {cv.company_name ? `${cv.company_name} · ` : ""}
                        <time className={styles.cvDate}>
                          {new Date(cv.created_at).toLocaleDateString("en-US", {
                            month: "short",
                            day: "numeric",
                            year: "numeric",
                          })}
                        </time>
                      </span>
                    </div>
                  </div>

                  <div className={styles.cvRight}>
                    {score != null && (
                      <span className={styles.atsBadge} data-score={tier}>
                        {score}% ATS
                      </span>
                    )}
                    <button
                      onClick={() => handleDownload(cv.id, cv.company_name)}
                      className={styles.downloadBtn}
                      disabled={isDownloading || deletingId === cv.id}
                      title="Download PDF"
                    >
                      {isDownloading ? (
                        <span className={styles.btnSpinner} />
                      ) : (
                        <Download size={15} strokeWidth={1.75} />
                      )}
                      <span>{isDownloading ? "Downloading…" : "PDF"}</span>
                    </button>

                    {confirmDeleteId === cv.id ? (
                      <div className={styles.confirmGroup}>
                        <button
                          onClick={() => handleDelete(cv.id)}
                          className={styles.confirmDeleteBtn}
                          disabled={deletingId === cv.id}
                          title="Confirm delete CV"
                        >
                          {deletingId === cv.id ? (
                            <span className={styles.btnSpinner} />
                          ) : (
                            <span>Delete</span>
                          )}
                        </button>
                        <button
                          onClick={() => setConfirmDeleteId(null)}
                          className={styles.cancelDeleteBtn}
                          disabled={deletingId === cv.id}
                        >
                          Cancel
                        </button>
                      </div>
                    ) : (
                      <button
                        onClick={() => setConfirmDeleteId(cv.id)}
                        className={styles.deleteBtn}
                        disabled={Boolean(deletingId)}
                        title="Delete CV"
                        aria-label={`Delete ${cv.job_title || "Tailored Resume"}`}
                      >
                        <Trash2 size={15} strokeWidth={1.75} />
                      </button>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className={styles.emptyState}>
            <div className={styles.emptyIconBox}>
              <FileSignature size={24} strokeWidth={1.75} />
            </div>
            <h2 className={styles.emptyTitle}>No tailored CVs yet</h2>
            <p className={styles.emptyDesc}>
              Paste a target job posting and we will align your work experience,
              skills, and summary into a clean single-column PDF.
            </p>
            <Link href="/generate" className={styles.generateBtn}>
              <Plus size={16} strokeWidth={2} />
              <span>Tailor Your First CV</span>
            </Link>
          </div>
        )}
      </section>
    </div>
  );
}
