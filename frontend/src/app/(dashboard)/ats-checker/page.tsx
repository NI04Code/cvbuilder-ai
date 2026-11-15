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
  Briefcase,
} from "lucide-react";
import { apiClient } from "@/lib/api";
import { useIsInsideDashboard } from "@/context/CVGenerationContext";
import { ThemeToggle } from "@/components/ThemeToggle";
import styles from "./page.module.css";

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
  target_role?: string | null;
  sections: ATSSectionScore[];
  keyword_analysis: ATSKeywordAnalysis;
  formatting_issues: ATSFormattingIssue[];
  strengths: string[];
  improvements: string[];
  summary: string;
}

function ScoreGauge({ score }: { score: number }) {
  const radius = 58;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;

  const color =
    score >= 80
      ? "var(--success)"
      : score >= 60
        ? "var(--warning)"
        : "var(--danger)";

  return (
    <div className={styles.gaugeContainer}>
      <svg width="144" height="144" className={styles.gaugeSvg}>
        <circle cx="72" cy="72" r={radius} className={styles.gaugeTrack} />
        <circle
          cx="72"
          cy="72"
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
        <div className={styles.gaugeLabel}>/ 100</div>
      </div>
    </div>
  );
}

function scoreColor(score: number) {
  if (score >= 80) return "var(--success)";
  if (score >= 60) return "var(--warning)";
  return "var(--danger)";
}

function scoreTier(score: number): "high" | "mid" | "low" {
  if (score >= 80) return "high";
  if (score >= 60) return "mid";
  return "low";
}

export default function ATSCheckerPage() {
  const isDashboard = useIsInsideDashboard();
  const [isDragging, setIsDragging] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [targetRole, setTargetRole] = useState("");
  const [result, setResult] = useState<ATSCheckResult | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

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
    if (targetRole.trim()) {
      formData.append("target_role", targetRole.trim());
    }

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

  return (
    <div className={isDashboard ? styles.dashboardContainer : styles.container}>
      {!isDashboard && (
        <header className={styles.nav}>
          <Link href="/" className={styles.logo}>
            <FileText size={20} strokeWidth={1.75} className={styles.logoIcon} />
            <span>CVBuilder</span>
            <span className={styles.logoTag}>ATS</span>
          </Link>
          <div className={styles.navLinks}>
            <ThemeToggle />
            <Link href="/login" className={styles.navLink}>
              Sign In
            </Link>
          </div>
        </header>
      )}

      <div className={isDashboard ? styles.dashboardMain : styles.main}>
        <header className={isDashboard ? styles.dashboardHeader : styles.header}>
          <div>
            <h1 className={isDashboard ? styles.dashboardTitle : styles.title}>
              {isDashboard
                ? "ATS Compatibility Checker"
                : "Check your resume's ATS parse rate & keyword coverage"}
            </h1>
            <p className={isDashboard ? styles.dashboardSubtitle : styles.subtitle}>
              {isDashboard
                ? "Upload any PDF resume to evaluate section weights, keyword density, and formatting issues."
                : "Upload a PDF resume for an instant section-by-section grading calibrated to your career level."}
            </p>
          </div>
          {result && (
            <button className={styles.resetBtn} onClick={reset}>
              <RotateCcw size={15} strokeWidth={1.75} />
              <span>Check Another Resume</span>
            </button>
          )}
        </header>

        {error && (
          <div className={styles.errorMsg}>
            <AlertCircle size={18} strokeWidth={1.75} />
            <span>{error}</span>
          </div>
        )}

        {!result && !isAnalyzing && (
          <div className={styles.uploadWrapper}>
            <div className={styles.targetRoleBox}>
              <label htmlFor="ats-target-role" className={styles.targetRoleLabel}>
                <Briefcase size={15} strokeWidth={1.75} className={styles.targetRoleIcon} />
                <span>Target Job Role</span>
                <span className={styles.targetRoleOptional}>(Optional)</span>
              </label>
              <input
                id="ats-target-role"
                type="text"
                maxLength={120}
                value={targetRole}
                onChange={(e) => setTargetRole(e.target.value)}
                placeholder="e.g., Senior Backend Engineer, CPA Accountant, Registered Nurse"
                className={styles.targetRoleInput}
              />
              <p className={styles.targetRoleHint}>
                Grades credential strength, experience fit, and missing keywords against this role. Leave blank to auto-detect from your CV.
              </p>
            </div>
            <div
              className={`${styles.uploadZone} ${isDragging ? styles.uploadZoneDragging : ""}`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              <div className={styles.uploadIconBox}>
                <UploadCloud size={26} strokeWidth={1.75} />
              </div>
              <p className={styles.uploadTitle}>
                Drop your PDF resume here or click to browse
              </p>
              <p className={styles.uploadDesc}>
                Single or multi-page PDF up to 10 MB · Processed in memory and never stored
              </p>
              <span className={styles.uploadCta}>Select PDF Resume</span>
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,application/pdf"
                onChange={handleFileSelect}
                hidden
              />
            </div>
          </div>
        )}

        {isAnalyzing && (
          <div className={styles.loadingState}>
            <div className={styles.spinner} />
            <p className={styles.loadingText}>Grading your resume against ATS criteria…</p>
            <p className={styles.loadingHint}>
              Checking text extractability, career-level section weights, and domain keyword density.
            </p>
          </div>
        )}

        {result && (
          <div className={styles.results}>
            {/* Overall Score Card */}
            <div className={styles.scoreOverview}>
              <ScoreGauge score={result.overall_score} />
              <div className={styles.overviewInfo}>
                <div className={styles.overviewMetaRow}>
                  <span className={styles.overviewLevel}>
                    {result.candidate_level}
                  </span>
                  {result.target_role && (
                    <span className={styles.targetRoleBadge}>
                      Target: {result.target_role}
                    </span>
                  )}
                  <span
                    className={styles.densityBadge}
                    data-rating={result.keyword_analysis.keyword_density_rating}
                  >
                    Keyword Density: {result.keyword_analysis.keyword_density_rating}
                  </span>
                </div>
                <p className={styles.overviewSummary}>{result.summary}</p>
              </div>
            </div>

            {/* Section Breakdown */}
            <section className={styles.blockSection}>
              <h2 className={styles.sectionTitle}>
                <BarChart3 size={19} strokeWidth={1.75} className={styles.sectionTitleIcon} />
                <span>Section Breakdown</span>
              </h2>
              <div className={styles.sectionsGrid}>
                {result.sections.map((section, idx) => (
                  <div key={`${section.section_name}-${idx}`} className={styles.sectionCard}>
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
                      {!section.present && " · Missing from resume"}
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
                  </div>
                ))}
              </div>
            </section>

            {/* Keyword Analysis */}
            <section className={styles.keywordSection}>
              <h2 className={styles.sectionTitle}>
                <Search size={19} strokeWidth={1.75} className={styles.sectionTitleIcon} />
                <span>Keyword Coverage</span>
              </h2>
              <div className={styles.keywordColumns}>
                <div className={styles.keywordColumn}>
                  <h3 className={styles.keywordSubheading}>
                    Detected Keywords ({result.keyword_analysis.detected_keywords.length})
                  </h3>
                  <div className={styles.keywordTags}>
                    {result.keyword_analysis.detected_keywords.length > 0 ? (
                      result.keyword_analysis.detected_keywords.map((kw, idx) => (
                        <span
                          key={`detected-${kw}-${idx}`}
                          className={`${styles.keywordTag} ${styles.keywordTagPresent}`}
                        >
                          {kw}
                        </span>
                      ))
                    ) : (
                      <span className={styles.emptyNotice}>
                        No domain keywords detected
                      </span>
                    )}
                  </div>
                </div>
                <div className={styles.keywordColumn}>
                  <h3 className={styles.keywordSubheading}>
                    Recommended Additions ({result.keyword_analysis.missing_common_keywords.length})
                  </h3>
                  <div className={styles.keywordTags}>
                    {result.keyword_analysis.missing_common_keywords.length > 0 ? (
                      result.keyword_analysis.missing_common_keywords.map((kw, idx) => (
                        <span
                          key={`missing-${kw}-${idx}`}
                          className={`${styles.keywordTag} ${styles.keywordTagMissing}`}
                        >
                          {kw}
                        </span>
                      ))
                    ) : (
                      <span className={styles.emptyNotice}>
                        Strong domain keyword coverage
                      </span>
                    )}
                  </div>
                </div>
              </div>
            </section>

            {/* Formatting Issues */}
            {result.formatting_issues.length > 0 && (
              <section className={styles.formattingSection}>
                <h2 className={styles.sectionTitle}>
                  <AlertTriangle size={19} strokeWidth={1.75} className={styles.sectionTitleIcon} />
                  <span>Formatting & Parseability Issues</span>
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
              </section>
            )}

            {/* Strengths & Priority Improvements */}
            <div className={styles.twoColumnCards}>
              <div className={styles.listCard}>
                <h3 className={styles.listCardTitle}>
                  <ThumbsUp size={17} strokeWidth={1.75} className={styles.iconSuccess} />
                  <span>Key Strengths</span>
                </h3>
                <ul className={styles.listCardItems}>
                  {result.strengths.map((s, i) => (
                    <li key={i} className={styles.strengthItem}>
                      {s}
                    </li>
                  ))}
                </ul>
              </div>
              <div className={styles.listCard}>
                <h3 className={styles.listCardTitle}>
                  <TrendingUp size={17} strokeWidth={1.75} className={styles.iconWarning} />
                  <span>Priority Fixes</span>
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
          </div>
        )}
      </div>
    </div>
  );
}
