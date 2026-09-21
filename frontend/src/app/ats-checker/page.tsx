"use client";

import { useState, useRef, DragEvent, ChangeEvent } from "react";
import Link from "next/link";
import {
  FileText,
  UploadCloud,
  RotateCcw,
  AlertCircle,
  BarChart3,
  Search,
  AlertTriangle,
  ThumbsUp,
  TrendingUp,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { apiClient } from "@/lib/api";
import styles from "./page.module.css";

// ── Types matching the backend ATSCheckResult schema ────────────────────

interface ATSSectionScore {
  section_name: string;
  score: number;
  present: boolean;
  weight: number;
  feedback: string;
  suggestions: string[];
}

interface ATSKeywordAnalysis {
  detected_keywords: string[];
  missing_common_keywords: string[];
  keyword_density_rating: string;
}

interface ATSFormattingIssue {
  issue: string;
  severity: string;
  suggestion: string;
}

interface ATSCheckResult {
  overall_score: number;
  candidate_level: string;
  sections: ATSSectionScore[];
  keyword_analysis: ATSKeywordAnalysis;
  formatting_issues: ATSFormattingIssue[];
  strengths: string[];
  improvements: string[];
  summary: string;
}

// ── Score Gauge Component ───────────────────────────────────────────────

function ScoreGauge({ score }: { score: number }) {
  const radius = 65;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;

  const color =
    score >= 80 ? "#34d399" : score >= 60 ? "#fbbf24" : "#f87171";

  return (
    <div className={styles.gaugeContainer}>
      <svg width="160" height="160" className={styles.gaugeSvg}>
        <circle cx="80" cy="80" r={radius} className={styles.gaugeTrack} />
        <circle
          cx="80"
          cy="80"
          r={radius}
          className={styles.gaugeFill}
          stroke={color}
          strokeDasharray={circumference}
          strokeDashoffset={offset}
        />
      </svg>
      <div className={styles.gaugeScoreText}>
        <div className={styles.gaugeNumber} style={{ color }}>
          {score}
        </div>
        <div className={styles.gaugeLabel}>ATS Score</div>
      </div>
    </div>
  );
}

// ── Score color helper ──────────────────────────────────────────────────

function scoreColor(score: number) {
  if (score >= 80) return "#34d399";
  if (score >= 60) return "#fbbf24";
  return "#f87171";
}

function scoreTier(score: number): "high" | "mid" | "low" {
  if (score >= 80) return "high";
  if (score >= 60) return "mid";
  return "low";
}

// ── Main Page Component ─────────────────────────────────────────────────

export default function ATSCheckerPage() {
  const [isDragging, setIsDragging] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<ATSCheckResult | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // ── Upload handlers ─────────────────────────────────────────────

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };
  const handleDragLeave = () => setIsDragging(false);
  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files?.[0]) analyzeFile(e.dataTransfer.files[0]);
  };
  const handleFileSelect = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) analyzeFile(e.target.files[0]);
  };

  const analyzeFile = async (file: File) => {
    setError(null);
    setResult(null);

    if (file.type !== "application/pdf") {
      setError("Please upload a PDF file.");
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      setError("File is too large. Maximum size is 10 MB.");
      return;
    }

    setIsAnalyzing(true);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await apiClient.post("/ats-checker/analyze", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setResult(response.data);
    } catch (err: any) {
      console.error("ATS analysis error:", err);
      setError(
        err.response?.data?.detail ||
          "An error occurred while analyzing your CV. Please try again."
      );
    } finally {
      setIsAnalyzing(false);
    }
  };

  const reset = () => {
    setResult(null);
    setError(null);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  // ── Render ──────────────────────────────────────────────────────

  return (
    <div className={styles.container}>
      {/* Nav */}
      <nav className={styles.nav}>
        <Link href="/" className={styles.logo}>
          <FileText size={24} className={styles.logoIcon} />
          CVBuilder <span className="gradient-text">AI</span>
        </Link>
        <div className={styles.navLinks}>
          <Link href="/login" className={styles.navLink}>
            Sign In
          </Link>
        </div>
      </nav>

      {/* Main */}
      <main className={styles.main}>
        <header className={styles.header}>
          <h1 className={styles.title}>
            Free <span className="gradient-text">ATS Checker</span>
          </h1>
          <p className={styles.subtitle}>
            Upload your CV and get an instant, detailed ATS compatibility
            report — no sign-up required.
          </p>
        </header>

        {/* Error */}
        <AnimatePresence>
          {error && (
            <motion.div
              className={styles.errorMsg}
              initial={{ opacity: 0, y: -8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
            >
              <AlertCircle size={20} />
              {error}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Upload / Loading / Results */}
        {!result && !isAnalyzing && (
          <motion.div
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
          >
            <div
              className={`${styles.uploadZone} ${isDragging ? styles.uploadZoneDragging : ""}`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <UploadCloud size={48} className={styles.uploadIcon} />
              <p className={styles.uploadTitle}>
                Drop your CV here or click to browse
              </p>
              <p className={styles.uploadDesc}>PDF files only, up to 10 MB</p>
              <p className={styles.uploadHint}>
                Your file is processed in memory and never stored on our servers.
              </p>
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,application/pdf"
                onChange={handleFileSelect}
                hidden
              />
            </div>
          </motion.div>
        )}

        {isAnalyzing && (
          <motion.div
            className={styles.loadingState}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
          >
            <div className={styles.spinner} />
            <p className={styles.loadingText}>Analyzing your CV…</p>
            <p className={styles.loadingHint}>
              Evaluating formatting, keywords, section quality, and ATS
              compatibility.
            </p>
          </motion.div>
        )}

        {result && (
          <motion.div
            className={styles.results}
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            {/* Reset */}
            <button className={styles.resetBtn} onClick={reset}>
              <RotateCcw size={16} />
              Check another CV
            </button>

            {/* Overall Score */}
            <div className={`${styles.scoreOverview} glass-card`}>
              <ScoreGauge score={result.overall_score} />
              <div className={styles.overviewInfo}>
                <span className={styles.overviewLevel}>
                  {result.candidate_level}
                </span>
                <p className={styles.overviewSummary}>{result.summary}</p>
              </div>
            </div>

            {/* Section Breakdown */}
            <div>
              <h2 className={styles.sectionTitle}>
                <BarChart3 size={22} className={styles.sectionTitleIcon} />
                Section Breakdown
              </h2>
              <div className={styles.sectionsGrid}>
                {result.sections.map((section, idx) => (
                  <motion.div
                    key={section.section_name}
                    className={`${styles.sectionCard} glass-card`}
                    initial={{ opacity: 0, y: 12 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: idx * 0.05 }}
                  >
                    <div className={styles.sectionCardHeader}>
                      <span className={styles.sectionCardName}>
                        {section.section_name}
                      </span>
                      <span
                        className={styles.sectionCardScore}
                        data-score={scoreTier(section.score)}
                      >
                        {section.score}%
                      </span>
                    </div>
                    <div className={styles.sectionProgressBar}>
                      <div
                        className={styles.sectionProgressFill}
                        style={{
                          width: `${section.score}%`,
                          background: scoreColor(section.score),
                        }}
                      />
                    </div>
                    <span className={styles.sectionCardWeight}>
                      Weight: {Math.round(section.weight * 100)}%
                      {!section.present && " · Not detected"}
                    </span>
                    <p className={styles.sectionCardFeedback}>
                      {section.feedback}
                    </p>
                    {section.suggestions.length > 0 && (
                      <ul className={styles.sectionCardSuggestions}>
                        {section.suggestions.map((s, i) => (
                          <li key={i}>{s}</li>
                        ))}
                      </ul>
                    )}
                  </motion.div>
                ))}
              </div>
            </div>

            {/* Keyword Analysis */}
            <div className={`${styles.keywordSection} glass-card`}>
              <h2 className={styles.sectionTitle}>
                <Search size={22} className={styles.sectionTitleIcon} />
                Keyword Analysis
              </h2>
              <div className={styles.keywordColumns}>
                <div className={styles.keywordColumn}>
                  <h4>Detected Keywords</h4>
                  <div className={styles.keywordTags}>
                    {result.keyword_analysis.detected_keywords.length > 0 ? (
                      result.keyword_analysis.detected_keywords.map((kw) => (
                        <span
                          key={kw}
                          className={`${styles.keywordTag} ${styles.keywordTagPresent}`}
                        >
                          {kw}
                        </span>
                      ))
                    ) : (
                      <span style={{ color: "#64748b", fontSize: "0.85rem" }}>
                        No significant keywords detected
                      </span>
                    )}
                  </div>
                </div>
                <div className={styles.keywordColumn}>
                  <h4>Suggested Missing Keywords</h4>
                  <div className={styles.keywordTags}>
                    {result.keyword_analysis.missing_common_keywords.length >
                    0 ? (
                      result.keyword_analysis.missing_common_keywords.map(
                        (kw) => (
                          <span
                            key={kw}
                            className={`${styles.keywordTag} ${styles.keywordTagMissing}`}
                          >
                            {kw}
                          </span>
                        )
                      )
                    ) : (
                      <span style={{ color: "#64748b", fontSize: "0.85rem" }}>
                        Great keyword coverage!
                      </span>
                    )}
                  </div>
                </div>
              </div>
              <span
                className={styles.densityBadge}
                data-rating={result.keyword_analysis.keyword_density_rating}
              >
                Keyword Density:{" "}
                {result.keyword_analysis.keyword_density_rating}
              </span>
            </div>

            {/* Formatting Issues */}
            {result.formatting_issues.length > 0 && (
              <div className={`${styles.formattingSection} glass-card`}>
                <h2 className={styles.sectionTitle}>
                  <AlertTriangle
                    size={22}
                    className={styles.sectionTitleIcon}
                  />
                  Formatting Issues
                </h2>
                <div className={styles.issuesList}>
                  {result.formatting_issues.map((issue, i) => (
                    <div key={i} className={styles.issueItem}>
                      <span
                        className={styles.issueSeverity}
                        data-severity={issue.severity}
                      >
                        {issue.severity}
                      </span>
                      <div className={styles.issueContent}>
                        <p>{issue.issue}</p>
                        <span>{issue.suggestion}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Strengths & Improvements */}
            <div className={styles.twoColumnCards}>
              <div className={`${styles.listCard} glass-card`}>
                <h3 className={styles.listCardTitle}>
                  <ThumbsUp size={18} style={{ color: "#34d399" }} />
                  Strengths
                </h3>
                <ul className={styles.listCardItems}>
                  {result.strengths.map((s, i) => (
                    <li key={i} className={styles.strengthItem}>
                      {s}
                    </li>
                  ))}
                </ul>
              </div>
              <div className={`${styles.listCard} glass-card`}>
                <h3 className={styles.listCardTitle}>
                  <TrendingUp size={18} style={{ color: "#fbbf24" }} />
                  Improvements
                </h3>
                <ul className={styles.listCardItems}>
                  {result.improvements.map((s, i) => (
                    <li key={i} className={styles.improvementItem}>
                      {s}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </motion.div>
        )}
      </main>
    </div>
  );
}
