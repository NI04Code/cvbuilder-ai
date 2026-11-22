"use client";

import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { useRouter } from "next/navigation";
import { FileSignature, Mail, Send, Copy, Check, Download, Plus, Target, Trash2, AlertCircle, UserCircle, ArrowRight } from "lucide-react";
import Link from "next/link";
import {
  apiClient,
  DocumentType,
  downloadDocumentPdf,
  getDocumentEndpointConfig,
} from "@/lib/api";
import { useDocumentGeneration } from "@/context/DocumentGenerationContext";
import { isProfileOnboardingSkipped } from "@/lib/onboarding";
import styles from "./page.module.css";

type DocumentFilter = "all" | DocumentType;

const PAGE_SIZE = 20;

export default function DashboardPage() {
  const { data: session, status } = useSession();
  const router = useRouter();
  const { clearGeneratedDocIfMatches } = useDocumentGeneration();
  const [history, setHistory] = useState<any[]>([]);
  const [activeFilter, setActiveFilter] = useState<DocumentFilter>("all");
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [copyingId, setCopyingId] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const userId = session?.user?.id;
  const hasProfile = (session as any)?.hasProfile;
  const shouldRedirectToProfile =
    status === "authenticated" &&
    hasProfile === false &&
    Boolean(userId) &&
    !isProfileOnboardingSkipped(userId);

  useEffect(() => {
    if (shouldRedirectToProfile) {
      router.replace("/profile?onboarding=1");
      return;
    }

    async function fetchHistory() {
      if (status !== "authenticated") return;
      try {
        const token = (session as any)?.backendAccessToken;
        const res = await apiClient.get("/documents/history", {
          params: { limit: PAGE_SIZE, offset: 0 },
          headers: { Authorization: `Bearer ${token}` },
        });
        setHistory(res.data);
        setHasMore(Array.isArray(res.data) && res.data.length === PAGE_SIZE);
      } catch (err) {
        console.error("Failed to fetch document history", err);
      } finally {
        setLoading(false);
      }
    }
    fetchHistory();
  }, [session, status, shouldRedirectToProfile, router]);

  const handleLoadMore = async () => {
    if (loadingMore || !hasMore) return;
    setLoadingMore(true);
    setActionError(null);
    try {
      const token = (session as any)?.backendAccessToken;
      const res = await apiClient.get("/documents/history", {
        params: { limit: PAGE_SIZE, offset: history.length },
        headers: { Authorization: `Bearer ${token}` },
      });
      const nextItems: any[] = Array.isArray(res.data) ? res.data : [];
      setHistory((prev) => {
        const seen = new Set(prev.map((item) => item.id));
        return [...prev, ...nextItems.filter((item) => !seen.has(item.id))];
      });
      setHasMore(nextItems.length === PAGE_SIZE);
    } catch (err) {
      console.error("Failed to load more documents", err);
      setActionError("Failed to load more documents. Please try again.");
    } finally {
      setLoadingMore(false);
    }
  };

  const handleDownload = async (
    docId: string,
    companyName: string,
    documentType: DocumentType = "cv"
  ) => {
    if (downloadingId) return;
    setDownloadingId(docId);
    try {
      const token = (session as any)?.backendAccessToken;
      await downloadDocumentPdf({
        docId,
        documentType,
        token,
        fallbackCompany: companyName,
        fallbackUserName: session?.user?.name,
      });
    } catch (err) {
      console.error("Download failed", err);
    } finally {
      setDownloadingId(null);
    }
  };

  const handleDelete = async (docId: string, documentType: DocumentType = "cv") => {
    if (deletingId) return;
    setDeletingId(docId);
    setActionError(null);
    try {
      const token = (session as any)?.backendAccessToken;
      const { apiBase } = getDocumentEndpointConfig(documentType);
      await apiClient.delete(`${apiBase}/${docId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setHistory((prev) => prev.filter((item) => item.id !== docId));
      clearGeneratedDocIfMatches(docId);
      setConfirmDeleteId(null);
    } catch (err: any) {
      console.error("Delete failed", err);
      setActionError(err.response?.data?.detail || "Failed to delete document. Please try again.");
    } finally {
      setDeletingId(null);
    }
  };

  const handleCopyColdEmail = async (docId: string) => {
    if (copyingId) return;
    setCopyingId(docId);
    setActionError(null);
    try {
      const token = (session as any)?.backendAccessToken;
      const res = await apiClient.get(`/cold-emails/${docId}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const text = `Subject: ${res.data.subject}\n\n${res.data.email_body}`;
      await navigator.clipboard.writeText(text);
      setCopiedId(docId);
      setTimeout(() => setCopiedId((prev) => (prev === docId ? null : prev)), 2000);
    } catch (err: any) {
      console.error("Copy failed", err);
      setActionError(err.response?.data?.detail || "Failed to copy cold email.");
    } finally {
      setCopyingId(null);
    }
  };

  const cvCount = history.filter((item) => (item.document_type || "cv") === "cv").length;
  const coverLetterCount = history.filter((item) => item.document_type === "cover_letter").length;
  const coldEmailCount = history.filter((item) => item.document_type === "cold_email").length;
  const filteredHistory = history.filter((item) => {
    if (activeFilter === "all") return true;
    const itemType: DocumentType =
      item.document_type === "cold_email"
        ? "cold_email"
        : item.document_type === "cover_letter"
          ? "cover_letter"
          : "cv";
    return itemType === activeFilter;
  });

  if (shouldRedirectToProfile) {
    return (
      <div className={styles.container}>
        <div className={styles.skeletonList} aria-label="Redirecting to profile setup">
          {[0, 1].map((i) => (
            <div key={i} className={styles.skeletonRow}>
              <div className={styles.skeletonLeft}>
                <div className={styles.skeletonTitle} />
                <div className={styles.skeletonSub} />
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Generated Documents</h1>
          <p className={styles.subtitle}>
            {loading
              ? "Loading your generated CVs, cover letters, and cold emails…"
              : history.length > 0
                ? `${cvCount} tailored CV${cvCount === 1 ? "" : "s"} · ${coverLetterCount} cover letter${coverLetterCount === 1 ? "" : "s"} · ${coldEmailCount} cold email${coldEmailCount === 1 ? "" : "s"}.`
                : "Paste a job description to generate your first tailored CV, cover letter, or cold email."}
          </p>
        </div>
        <div className={styles.headerActions}>
          <Link href="/ats-checker" className={styles.secondaryBtn}>
            <Target size={16} strokeWidth={1.75} />
            <span>Check ATS Score</span>
          </Link>
          <Link href="/cold-email" className={styles.secondaryBtn}>
            <Send size={16} strokeWidth={1.75} />
            <span>New Cold Email</span>
          </Link>
          <Link href="/cover-letter" className={styles.secondaryBtn}>
            <Mail size={16} strokeWidth={1.75} />
            <span>New Cover Letter</span>
          </Link>
          <Link href="/generate" className={styles.generateBtn}>
            <Plus size={16} strokeWidth={2} />
            <span>Tailor New CV</span>
          </Link>
        </div>
      </header>

      {hasProfile === false && (
        <div className={styles.profilePromptBanner}>
          <div className={styles.profilePromptTextWrap}>
            <div className={styles.profilePromptIcon}>
              <UserCircle size={18} strokeWidth={1.75} />
            </div>
            <div>
              <p className={styles.profilePromptTitle}>Complete your base profile to generate documents</p>
              <p className={styles.profilePromptDesc}>
                Upload an existing resume PDF or enter your experience manually whenever you&apos;re ready.
              </p>
            </div>
          </div>
          <Link href="/profile?onboarding=1" className={styles.secondaryBtn}>
            <span>Create Profile</span>
            <ArrowRight size={15} strokeWidth={2} />
          </Link>
        </div>
      )}

      {!loading && history.length > 0 && (
        <div className={styles.filterBar}>
          <div className={styles.filterTabs} role="tablist" aria-label="Filter generated documents">
            <button
              type="button"
              role="tab"
              aria-selected={activeFilter === "all"}
              onClick={() => setActiveFilter("all")}
              className={`${styles.filterTab} ${activeFilter === "all" ? styles.filterTabActive : ""}`}
            >
              <span>All</span>
              <span className={styles.filterCount}>{history.length}</span>
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={activeFilter === "cv"}
              onClick={() => setActiveFilter("cv")}
              className={`${styles.filterTab} ${activeFilter === "cv" ? styles.filterTabActive : ""}`}
            >
              <span>Tailored CVs</span>
              <span className={styles.filterCount}>{cvCount}</span>
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={activeFilter === "cover_letter"}
              onClick={() => setActiveFilter("cover_letter")}
              className={`${styles.filterTab} ${activeFilter === "cover_letter" ? styles.filterTabActive : ""}`}
            >
              <span>Cover Letters</span>
              <span className={styles.filterCount}>{coverLetterCount}</span>
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={activeFilter === "cold_email"}
              onClick={() => setActiveFilter("cold_email")}
              className={`${styles.filterTab} ${activeFilter === "cold_email" ? styles.filterTabActive : ""}`}
            >
              <span>Cold Emails</span>
              <span className={styles.filterCount}>{coldEmailCount}</span>
            </button>
          </div>
        </div>
      )}

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
        ) : filteredHistory.length > 0 ? (
          <div className={styles.cvList}>
            {filteredHistory.map((cv: any) => {
              const docType: DocumentType =
                cv.document_type === "cold_email"
                  ? "cold_email"
                  : cv.document_type === "cover_letter"
                    ? "cover_letter"
                    : "cv";
              const isCoverLetter = docType === "cover_letter";
              const isColdEmail = docType === "cold_email";
              const score =
                !isCoverLetter && !isColdEmail && cv.ats_score != null
                  ? Math.round(cv.ats_score)
                  : null;
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
                    <div className={styles.cvIconBox} data-type={docType}>
                      {isColdEmail ? (
                        <Send size={18} strokeWidth={1.75} />
                      ) : isCoverLetter ? (
                        <Mail size={18} strokeWidth={1.75} />
                      ) : (
                        <FileSignature size={18} strokeWidth={1.75} />
                      )}
                    </div>
                    <div className={styles.cvText}>
                      <span className={styles.cvRole}>
                        {cv.job_title ||
                          (isColdEmail
                            ? "Cold Email"
                            : isCoverLetter
                              ? "Cover Letter"
                              : "Tailored Resume")}
                      </span>
                      <span className={styles.cvMeta}>
                        {cv.company_name ? `${cv.company_name} · ` : ""}
                        {isColdEmail && cv.recruiter_name ? `To ${cv.recruiter_name} · ` : ""}
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
                    <span className={styles.typeBadge} data-type={docType}>
                      {isColdEmail ? "Cold Email" : isCoverLetter ? "Cover Letter" : "CV"}
                    </span>
                    {score != null && (
                      <span className={styles.atsBadge} data-score={tier}>
                        {score}% ATS
                      </span>
                    )}
                    {isColdEmail ? (
                      <button
                        onClick={() => handleCopyColdEmail(cv.id)}
                        className={styles.downloadBtn}
                        disabled={copyingId === cv.id || deletingId === cv.id}
                        title="Copy cold email"
                      >
                        {copiedId === cv.id ? (
                          <Check size={15} strokeWidth={2} />
                        ) : (
                          <Copy size={15} strokeWidth={1.75} />
                        )}
                        <span>{copiedId === cv.id ? "Copied" : "Copy"}</span>
                      </button>
                    ) : (
                      <button
                        onClick={() => handleDownload(cv.id, cv.company_name, docType)}
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
                    )}

                    {confirmDeleteId === cv.id ? (
                      <div className={styles.confirmGroup}>
                        <button
                          onClick={() => handleDelete(cv.id, docType)}
                          className={styles.confirmDeleteBtn}
                          disabled={deletingId === cv.id}
                          title="Confirm delete document"
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
                        title="Delete document"
                        aria-label={`Delete ${cv.job_title || (isCoverLetter ? "Cover Letter" : "Tailored Resume")}`}
                      >
                        <Trash2 size={15} strokeWidth={1.75} />
                      </button>
                    )}
                  </div>
                </div>
              );
            })}

            {hasMore && (
              <div className={styles.paginationBar}>
                <button
                  type="button"
                  onClick={handleLoadMore}
                  disabled={loadingMore}
                  className={styles.loadMoreBtn}
                >
                  {loadingMore && <span className={styles.btnSpinner} />}
                  <span>{loadingMore ? "Loading…" : "Load more"}</span>
                </button>
              </div>
            )}
          </div>
        ) : history.length > 0 ? (
          <div className={styles.emptyState}>
            <div className={styles.emptyIconBox}>
              {activeFilter === "cold_email" ? (
                <Send size={24} strokeWidth={1.75} />
              ) : activeFilter === "cover_letter" ? (
                <Mail size={24} strokeWidth={1.75} />
              ) : (
                <FileSignature size={24} strokeWidth={1.75} />
              )}
            </div>
            <h2 className={styles.emptyTitle}>
              {activeFilter === "cold_email"
                ? "No cold emails yet"
                : activeFilter === "cover_letter"
                  ? "No cover letters yet"
                  : "No tailored CVs yet"}
            </h2>
            <p className={styles.emptyDesc}>
              {activeFilter === "cold_email"
                ? "Generate a concise, hook-driven cold email tailored to the recruiter and target role."
                : activeFilter === "cover_letter"
                  ? "Generate a concise, one-page cover letter tailored to your target role."
                  : "Paste a target job posting and align your resume bullets and skills into a clean PDF."}
            </p>
            <Link
              href={
                activeFilter === "cold_email"
                  ? "/cold-email"
                  : activeFilter === "cover_letter"
                    ? "/cover-letter"
                    : "/generate"
              }
              className={styles.generateBtn}
            >
              <Plus size={16} strokeWidth={2} />
              <span>
                {activeFilter === "cold_email"
                  ? "Write a Cold Email"
                  : activeFilter === "cover_letter"
                    ? "Write a Cover Letter"
                    : "Tailor a CV"}
              </span>
            </Link>
          </div>
        ) : (
          <div className={styles.emptyState}>
            <div className={styles.emptyIconBox}>
              <FileSignature size={24} strokeWidth={1.75} />
            </div>
            <h2 className={styles.emptyTitle}>No generated documents yet</h2>
            <p className={styles.emptyDesc}>
              Paste a target job posting to tailor a resume or generate a concise one-page cover letter PDF.
            </p>
            <Link href="/generate" className={styles.generateBtn}>
              <Plus size={16} strokeWidth={2} />
              <span>Create First Document</span>
            </Link>
          </div>
        )}
      </section>
    </div>
  );
}
