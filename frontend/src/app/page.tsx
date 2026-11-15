"use client";

import Link from "next/link";
import { FileText, ArrowRight, Check, Target, FileCheck2, Layers } from "lucide-react";
import { ThemeToggle } from "@/components/ThemeToggle";
import styles from "./page.module.css";

const SAMPLE_KEYWORDS = [
  "Python",
  "FastAPI",
  "PostgreSQL",
  "Distributed Systems",
  "Docker",
  "CI/CD",
  "REST APIs",
  "System Design",
];

const SAMPLE_SECTIONS = [
  { name: "Work Experience", score: 96, weight: "40%" },
  { name: "Technical Skills", score: 94, weight: "25%" },
  { name: "ATS Formatting", score: 100, weight: "20%" },
  { name: "Education & Certs", score: 88, weight: "15%" },
];

export default function Home() {
  return (
    <div className={styles.container}>
      <header className={styles.nav}>
        <Link href="/" className={styles.logo}>
          <FileText size={20} strokeWidth={1.75} className={styles.logoIcon} />
          <span>CVBuilder</span>
          <span className={styles.logoTag}>ATS</span>
        </Link>
        <div className={styles.navActions}>
          <Link href="/ats-checker" className={styles.navLink}>
            ATS Score Checker
          </Link>
          <ThemeToggle />
          <Link href="/login" className={styles.signInBtn}>
            Sign In
          </Link>
        </div>
      </header>

      <main className={styles.main}>
        {/* Hero Copy + CTAs */}
        <section className={styles.hero}>
          <div className={styles.heroCopy}>
            <h1 className={styles.title}>
              Tailor your resume to any job description in 30 seconds
            </h1>
            <p className={styles.subtitle}>
              Import your base PDF resume once. Paste a target job posting to
              align your experience with exact role keywords and export a clean,
              single-column PDF built for Applicant Tracking Systems.
            </p>
            <div className={styles.ctaGroup}>
              <Link href="/login" className={styles.primaryCta}>
                <span>Tailor Your CV</span>
                <ArrowRight size={18} strokeWidth={2} className={styles.ctaIcon} />
              </Link>
              <Link href="/ats-checker" className={styles.secondaryCta}>
                Check Current Resume Score
              </Link>
            </div>
          </div>

          {/* Enlarged Product Showcase */}
          <div className={styles.productFrame}>
            <div className={styles.productWindow}>
              <div className={styles.windowHeader}>
                <div className={styles.windowTitle}>
                  <span className={styles.statusDot} />
                  <span>Senior Backend Engineer — Stripe · Tailored Output</span>
                </div>
                <div className={styles.matchPill}>
                  <span className={styles.matchNumber}>94%</span> ATS Match
                </div>
              </div>

              <div className={styles.workspaceGrid}>
                {/* Left Column: ATS Analysis & Keyword Alignment */}
                <div className={styles.analysisPane}>
                  <div className={styles.paneSection}>
                    <div className={styles.paneHeader}>
                      <span className={styles.paneLabel}>Section Scoring</span>
                      <span className={styles.paneMeta}>Senior Level</span>
                    </div>
                    <div className={styles.scoreRows}>
                      {SAMPLE_SECTIONS.map((sec) => (
                        <div key={sec.name} className={styles.scoreRow}>
                          <div className={styles.scoreRowTop}>
                            <span className={styles.scoreRowName}>{sec.name}</span>
                            <span className={styles.scoreRowVal}>{sec.score}%</span>
                          </div>
                          <div className={styles.scoreTrack}>
                            <div
                              className={styles.scoreFill}
                              style={{ width: `${sec.score}%` }}
                            />
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className={styles.paneSection}>
                    <div className={styles.paneHeader}>
                      <span className={styles.paneLabel}>Matched Job Keywords</span>
                      <span className={styles.paneMeta}>8 / 8 present</span>
                    </div>
                    <div className={styles.keywordGrid}>
                      {SAMPLE_KEYWORDS.map((kw) => (
                        <span key={kw} className={styles.keywordChip}>
                          <Check size={12} strokeWidth={2.25} />
                          {kw}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>

                {/* Right Column: Actual Single-Column ATS Resume Output */}
                <div className={styles.resumeSheet}>
                  <div className={styles.resumeHeader}>
                    <div>
                      <div className={styles.candidateName}>John Doe</div>
                      <div className={styles.candidateMeta}>
                        San Francisco, CA · john.doe@email.com · github.com/johndoe
                      </div>
                    </div>
                    <span className={styles.pdfTag}>Single-Column PDF</span>
                  </div>

                  <div className={styles.resumeBlock}>
                    <div className={styles.resumeSectionHeading}>Work Experience</div>
                    <div className={styles.roleHeader}>
                      <span className={styles.roleTitle}>
                        Senior Software Engineer · CloudScale
                      </span>
                      <span className={styles.roleDate}>2022 – Present</span>
                    </div>
                    <ul className={styles.resumeBullets}>
                      <li>
                        Architected high-throughput payment webhooks in{" "}
                        <strong>Python</strong> and <strong>FastAPI</strong>,
                        processing <strong>14,000 req/s</strong> at 99.99% uptime.
                      </li>
                      <li>
                        Reduced <strong>PostgreSQL</strong> query p99 latency by{" "}
                        <strong>42%</strong> via composite indexing and read-replica
                        connection pooling.
                      </li>
                      <li>
                        Automated zero-downtime <strong>Docker</strong> deployments
                        across multi-region <strong>CI/CD</strong> pipelines.
                      </li>
                    </ul>
                  </div>

                  <div className={styles.resumeBlock}>
                    <div className={styles.resumeSectionHeading}>Core Technical Skills</div>
                    <div className={styles.resumeSkillsText}>
                      Python, FastAPI, PostgreSQL, Distributed Systems, Docker,
                      Kubernetes, Redis, CI/CD, System Design
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* Concrete Workflow Breakdown */}
        <section className={styles.workflowSection}>
          <div className={styles.workflowHeader}>
            <h2 className={styles.sectionHeading}>
              Built around how ATS parsers actually read resumes
            </h2>
            <p className={styles.sectionSubheading}>
              No multi-column graphics, skill progress bars, or hallucinated
              credentials—just your real experience structured for machine and
              recruiter readability.
            </p>
          </div>

          <div className={styles.featuresGrid}>
            <div className={styles.featureCard}>
              <div className={styles.featureIcon}>
                <Layers size={20} strokeWidth={1.75} />
              </div>
              <h3 className={styles.featureTitle}>Parse once, reuse forever</h3>
              <p className={styles.featureDesc}>
                Upload your existing PDF or LinkedIn export to build a structured
                career profile you can edit and reuse for every job application.
              </p>
            </div>

            <div className={styles.featureCard}>
              <div className={styles.featureIcon}>
                <Target size={20} strokeWidth={1.75} />
              </div>
              <h3 className={styles.featureTitle}>Role-specific keyword alignment</h3>
              <p className={styles.featureDesc}>
                Extracts required and preferred skills from the job posting and
                rewrites your bullet points to surface matching terminology.
              </p>
            </div>

            <div className={styles.featureCard}>
              <div className={styles.featureIcon}>
                <FileCheck2 size={20} strokeWidth={1.75} />
              </div>
              <h3 className={styles.featureTitle}>Career-level ATS grading</h3>
              <p className={styles.featureDesc}>
                Test any PDF resume against an adaptive rubric calibrated for
                Entry, Mid, Senior, and Executive candidates before you apply.
              </p>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
