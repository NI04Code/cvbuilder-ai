"use client";

import { useEffect, useState } from "react";
import { useSession } from "next-auth/react";
import { FileSignature, Download, ArrowRight, Plus } from "lucide-react";
import Link from "next/link";
import { apiClient } from "@/lib/api";
import styles from "./page.module.css";
import { motion } from "framer-motion";

export default function DashboardPage() {
  const { data: session, status } = useSession();
  const [history, setHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

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
        a.download = `CV_${companyName || "Tailored"}.pdf`;
        a.click();
        window.URL.revokeObjectURL(url);
      }
    } catch (err) {
      console.error("Download failed", err);
    }
  };

  const firstName = session?.user?.name?.split(" ")[0] || "User";

  return (
    <div className={styles.container}>
      {/* Header */}
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>{firstName}&apos;s Dashboard</h1>
          <p className={styles.subtitle}>
            {history.length > 0
              ? `You have ${history.length} tailored CV${history.length > 1 ? "s" : ""}.`
              : "Generate your first ATS-optimized CV to get started."}
          </p>
        </div>
        <Link href="/generate" className={styles.generateBtn}>
          <Plus size={18} />
          Generate CV
        </Link>
      </header>

      {/* CV List */}
      <section>
        {loading ? (
          <div className={styles.loadingState}>
            <div className={styles.spinner} />
            <p>Loading your CVs...</p>
          </div>
        ) : history.length > 0 ? (
          <div className={styles.cvList}>
            {/* Table header */}
            <div className={styles.tableHeader}>
              <span className={styles.colRole}>Role</span>
              <span className={styles.colCompany}>Company</span>
              <span className={styles.colAts}>ATS Score</span>
              <span className={styles.colDate}>Date</span>
              <span className={styles.colActions}></span>
            </div>

            {/* CV Rows */}
            {history.map((cv: any, idx: number) => (
              <motion.div
                key={cv.id}
                className={styles.cvRow}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: idx * 0.04 }}
              >
                <span className={styles.colRole}>
                  <FileSignature size={16} className={styles.rowIcon} />
                  {cv.job_title || "-"}
                </span>
                <span className={styles.colCompany}>{cv.company_name || "—"}</span>
                <span className={styles.colAts}>
                  {cv.ats_score != null ? (
                    <span className={styles.atsBadge} data-score={cv.ats_score >= 80 ? "high" : cv.ats_score >= 60 ? "mid" : "low"}>
                      {cv.ats_score}%
                    </span>
                  ) : (
                    "—"
                  )}
                </span>
                <span className={styles.colDate}>
                  {new Date(cv.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" })}
                </span>
                <span className={styles.colActions}>
                  <button
                    onClick={() => handleDownload(cv.id, cv.company_name)}
                    className={styles.downloadBtn}
                    title="Download PDF"
                  >
                    <Download size={16} />
                  </button>
                </span>
              </motion.div>
            ))}
          </div>
        ) : (
          <motion.div
            className={styles.emptyState}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <FileSignature size={48} className={styles.emptyIcon} />
            <h3 className={styles.emptyTitle}>No CVs generated yet</h3>
            <p className={styles.emptyDesc}>
              Paste a job description and let AI tailor your profile into an ATS-optimized CV.
            </p>
            <Link href="/generate" className={styles.emptyBtn}>
              <Plus size={18} />
              Generate Your First CV
            </Link>
          </motion.div>
        )}
      </section>
    </div>
  );
}
