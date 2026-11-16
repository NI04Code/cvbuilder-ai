"use client";

import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { FileSignature, Mail, Download, Plus, Target, Trash2, AlertCircle } from "lucide-react";
import Link from "next/link";
import {
  apiClient,
  DocumentType,
  downloadDocumentPdf,
  getDocumentEndpointConfig,
} from "@/lib/api";
import { useDocumentGeneration } from "@/context/DocumentGenerationContext";
import styles from "./page.module.css";

type DocumentFilter = "all" | DocumentType;

export default function DashboardPage() {
  const { data: session, status } = useSession();
  const { clearGeneratedDocIfMatches } = useDocumentGeneration();
  const [history, setHistory] = useState<any[]>([]);
  const [activeFilter, setActiveFilter] = useState<DocumentFilter>("all");
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
        const res = await apiClient.get("/documents/history", {
          headers: { Authorization: `Bearer ${token}` },
        });
        setHistory(res.data);
      } catch (err) {
        console.error("Failed to fetch document history", err);
      } finally {
        setLoading(false);
      }
    }
    fetchHistory();
  }, [session, status]);

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

  const cvCount = history.filter((item) => (item.document_type || "cv") === "cv").length;
  const coverLetterCount = history.filter((item) => item.document_type === "cover_letter").length;
  const filteredHistory = history.filter((item) => {
    if (activeFilter === "all") return true;
    const itemType: DocumentType = item.document_type === "cover_letter" ? "cover_letter" : "cv";
    return itemType === activeFilter;
  });

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Generated Documents</h1>
          <p className={styles.subtitle}>
            {loading
              ? "Loading your generated CVs and cover letters…"
              : history.length > 0
                ? `${cvCount} tailored CV${cvCount === 1 ? "" : "s"} · ${coverLetterCount} cover letter${coverLetterCount === 1 ? "" : "s"} ready for download.`
                : "Paste a job description to generate your first tailored CV or cover letter."}
          </p>
        </div>
        <div className={styles.headerActions}>
          <Link href="/ats-checker" className={styles.secondaryBtn}>
            <Target size={16} strokeWidth={1.75} />
            <span>Check ATS Score</span>
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
                cv.document_type === "cover_letter" ? "cover_letter" : "cv";
              const isCoverLetter = docType === "cover_letter";
              const score =
                !isCoverLetter && cv.ats_score != null ? Math.round(cv.ats_score) : null;
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
                      {isCoverLetter ? (
                        <Mail size={18} strokeWidth={1.75} />
                      ) : (
                        <FileSignature size={18} strokeWidth={1.75} />
                      )}
                    </div>
                    <div className={styles.cvText}>
                      <span className={styles.cvRole}>
                        {cv.job_title || (isCoverLetter ? "Cover Letter" : "Tailored Resume")}
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
                    <span className={styles.typeBadge} data-type={docType}>
                      {isCoverLetter ? "Cover Letter" : "CV"}
                    </span>
                    {score != null && (
                      <span className={styles.atsBadge} data-score={tier}>
                        {score}% ATS
                      </span>
                    )}
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
          </div>
        ) : history.length > 0 ? (
          <div className={styles.emptyState}>
            <div className={styles.emptyIconBox}>
              {activeFilter === "cover_letter" ? (
                <Mail size={24} strokeWidth={1.75} />
              ) : (
                <FileSignature size={24} strokeWidth={1.75} />
              )}
            </div>
            <h2 className={styles.emptyTitle}>
              {activeFilter === "cover_letter" ? "No cover letters yet" : "No tailored CVs yet"}
            </h2>
            <p className={styles.emptyDesc}>
              {activeFilter === "cover_letter"
                ? "Generate a concise, one-page cover letter tailored to your target role."
                : "Paste a target job posting and align your resume bullets and skills into a clean PDF."}
            </p>
            <Link
              href={activeFilter === "cover_letter" ? "/cover-letter" : "/generate"}
              className={styles.generateBtn}
            >
              <Plus size={16} strokeWidth={2} />
              <span>
                {activeFilter === "cover_letter" ? "Write a Cover Letter" : "Tailor a CV"}
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
