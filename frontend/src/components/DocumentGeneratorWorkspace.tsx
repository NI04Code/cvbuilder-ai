"use client";

import { useState, useEffect } from "react";
import { FileSignature, Mail, Send, Download, Copy, Eye, AlertCircle, Check, ArrowRight } from "lucide-react";
import { useSession } from "next-auth/react";
import { apiClient, DocumentType, downloadDocumentPdf } from "@/lib/api";
import { useDocumentGeneration } from "@/context/DocumentGenerationContext";
import styles from "@/app/(dashboard)/generate/page.module.css";
import Link from "next/link";

interface DocumentGeneratorWorkspaceProps {
  initialMode?: DocumentType;
}

export function DocumentGeneratorWorkspace({
  initialMode = "cv",
}: DocumentGeneratorWorkspaceProps) {
  const { data: session, status, update } = useSession();
  const {
    isGeneratingCv,
    isGeneratingCoverLetter,
    isGeneratingColdEmail,
    cvError,
    coverLetterError,
    coldEmailError,
    formData,
    generatedCv,
    generatedCoverLetter,
    generatedColdEmail,
    setFormData,
    startGeneration,
  } = useDocumentGeneration();

  const [mode, setMode] = useState<DocumentType>(initialMode);
  const [hasProfile, setHasProfile] = useState<boolean | null>(null);
  const [isDownloading, setIsDownloading] = useState(false);
  const [copiedColdEmail, setCopiedColdEmail] = useState(false);

  useEffect(() => {
    setMode(initialMode);
  }, [initialMode]);

  useEffect(() => {
    if (status !== "authenticated") return;
    if ((session as any)?.hasProfile === true) {
      setHasProfile(true);
      return;
    }

    const token = (session as any)?.backendAccessToken;
    apiClient
      .get("/profile/", { headers: { Authorization: `Bearer ${token}` } })
      .then(() => {
        setHasProfile(true);
        update({ hasProfile: true });
      })
      .catch(() => {
        setHasProfile(false);
      });
  }, [status, session, update]);

  const isCoverLetterMode = mode === "cover_letter";
  const isColdEmailMode = mode === "cold_email";
  const isGenerating = isColdEmailMode
    ? isGeneratingColdEmail
    : isCoverLetterMode
      ? isGeneratingCoverLetter
      : isGeneratingCv;
  const error = isColdEmailMode
    ? coldEmailError
    : isCoverLetterMode
      ? coverLetterError
      : cvError;
  const activeDoc = isColdEmailMode
    ? generatedColdEmail
    : isCoverLetterMode
      ? generatedCoverLetter
      : generatedCv;

  const handleCopyColdEmail = async () => {
    if (!generatedColdEmail) return;
    const text = `Subject: ${generatedColdEmail.subject}\n\n${generatedColdEmail.email_body}`;
    await navigator.clipboard.writeText(text);
    setCopiedColdEmail(true);
    setTimeout(() => setCopiedColdEmail(false), 2000);
  };

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    await startGeneration(mode);
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setFormData((prev) => ({
      ...prev,
      [e.target.name]: e.target.value,
    }));
  };

  const handleDownloadPdf = async () => {
    if (!activeDoc || isDownloading) return;
    setIsDownloading(true);
    try {
      const token = (session as any)?.backendAccessToken;
      await downloadDocumentPdf({
        docId: activeDoc.id,
        documentType: mode,
        token,
        fallbackCompany: formData.company_name || activeDoc.company_name,
        fallbackUserName: session?.user?.name,
      });
    } finally {
      setIsDownloading(false);
    }
  };

  if (hasProfile === false) {
    return (
      <div className={styles.profileRequiredCard}>
        <div className={styles.emptyIconBox}>
          <AlertCircle size={22} strokeWidth={1.75} />
        </div>
        <h2 className={styles.emptyCardTitle}>Base Profile Required</h2>
        <p className={styles.emptyCardDesc}>
          Import a PDF resume or fill in your career profile before generating role-targeted CVs or cover letters.
        </p>
        <Link href="/profile" className={styles.primaryLinkBtn}>
          <span>Set Up Base Profile</span>
          <ArrowRight size={16} strokeWidth={2} />
        </Link>
      </div>
    );
  }

  const charCount = formData.job_description.trim().length;
  const tailored = generatedCv?.tailored_content;
  const coverLetterText: string | null = generatedCoverLetter?.cover_letter_text || null;
  const coverLetterParagraphs = coverLetterText
    ? coverLetterText
        .split(/\n\s*\n/)
        .map((p) => p.trim())
        .filter(Boolean)
    : [];
  const coldEmailParagraphs: string[] = generatedColdEmail?.email_body
    ? String(generatedColdEmail.email_body)
        .split(/\n\s*\n/)
        .map((p) => p.trim())
        .filter(Boolean)
    : [];

  return (
    <div className={styles.container}>
      {/* Left Panel: Job Input Form */}
      <div className={styles.leftPanel}>
        <header className={styles.header}>
          <h1 className={styles.title}>
            {isColdEmailMode
              ? "Write Recruiter Cold Email"
              : isCoverLetterMode
                ? "Write Tailored Cover Letter"
                : "Tailor CV to Job Posting"}
          </h1>
          <p className={styles.subtitle}>
            {isColdEmailMode
              ? "Generate a concise, hook-driven outreach message tailored to the recruiter and role."
              : isCoverLetterMode
                ? "Generate a concise one-page cover letter grounded in your profile for this role."
                : "Paste the target job description to align your profile bullets and skills with required keywords."}
          </p>
        </header>

        {error && (
          <div className={styles.errorMsg}>
            <AlertCircle size={18} strokeWidth={1.75} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleGenerate} className={styles.form}>
          <div className={styles.inlineFields}>
            <div className={styles.formGroup}>
              <label htmlFor="job_title" className={styles.label}>
                Target Role
              </label>
              <input
                type="text"
                id="job_title"
                name="job_title"
                value={formData.job_title}
                onChange={handleChange}
                placeholder="e.g. Senior Backend Engineer"
                className={styles.input}
              />
            </div>
            <div className={styles.formGroup}>
              <label htmlFor="company_name" className={styles.label}>
                Company
              </label>
              <input
                type="text"
                id="company_name"
                name="company_name"
                value={formData.company_name}
                onChange={handleChange}
                placeholder="e.g. Stripe"
                className={styles.input}
              />
            </div>
          </div>

          {isColdEmailMode && (
            <div className={styles.formGroup}>
              <label htmlFor="recruiter_name" className={styles.label}>
                Recruiter Name
              </label>
              <input
                type="text"
                id="recruiter_name"
                name="recruiter_name"
                value={formData.recruiter_name}
                onChange={handleChange}
                placeholder="e.g. Sarah Jenkins (optional)"
                className={styles.input}
              />
            </div>
          )}

          <div className={styles.formGroup}>
            <div className={styles.labelRow}>
              <label htmlFor="job_description" className={styles.label}>
                Job Description
              </label>
              <span
                className={styles.charCounter}
                data-ready={charCount >= 50 && charCount <= 2500 ? "true" : "false"}
              >
                {charCount} / 2,500 chars (min 50)
              </span>
            </div>
            <textarea
              id="job_description"
              name="job_description"
              value={formData.job_description}
              onChange={handleChange}
              maxLength={2500}
              placeholder="Paste the responsibilities, requirements, and qualifications from the job posting…"
              className={styles.textarea}
              required
            />
          </div>

          <button
            type="submit"
            className={styles.generateBtn}
            disabled={isGenerating || charCount < 50 || charCount > 2500}
          >
            {isGenerating ? (
              <>
                <span className={styles.btnSpinner} />
                <span>
                  {isColdEmailMode
                    ? "Drafting Cold Email…"
                    : isCoverLetterMode
                      ? "Drafting Cover Letter…"
                      : "Tailoring Resume to Job Posting…"}
                </span>
              </>
            ) : (
              <>
                {isColdEmailMode ? (
                  <Send size={18} strokeWidth={1.75} />
                ) : isCoverLetterMode ? (
                  <Mail size={18} strokeWidth={1.75} />
                ) : (
                  <FileSignature size={18} strokeWidth={1.75} />
                )}
                <span>
                  {isColdEmailMode
                    ? "Generate Cold Email"
                    : isCoverLetterMode
                      ? "Generate Cover Letter"
                      : "Generate Tailored CV"}
                </span>
              </>
            )}
          </button>
        </form>
      </div>

      {/* Right Panel: Live Document Preview */}
      <div className={styles.rightPanel}>
        <div className={styles.previewHeader}>
          <div className={styles.previewTitle}>
            <Eye size={18} strokeWidth={1.75} />
            <span>
              {activeDoc
                ? `${
                    activeDoc.job_title ||
                    (isColdEmailMode
                      ? "Cold Email"
                      : isCoverLetterMode
                        ? "Cover Letter"
                        : "Tailored CV")
                  }${activeDoc.company_name ? ` · ${activeDoc.company_name}` : ""}`
                : isColdEmailMode
                  ? "Cold Email Preview"
                  : isCoverLetterMode
                    ? "Cover Letter Preview"
                    : "Tailored Output Preview"}
            </span>
          </div>
          {activeDoc && (
            <div className={styles.actions}>
              {isColdEmailMode ? (
                <>
                  <div className={styles.coverLetterBadge}>Outreach Message</div>
                  <button
                    type="button"
                    className={styles.downloadBtn}
                    onClick={handleCopyColdEmail}
                  >
                    {copiedColdEmail ? (
                      <Check size={15} strokeWidth={2} />
                    ) : (
                      <Copy size={15} strokeWidth={1.75} />
                    )}
                    <span>{copiedColdEmail ? "Copied!" : "Copy Email"}</span>
                  </button>
                </>
              ) : (
                <>
                  {isCoverLetterMode ? (
                    <div className={styles.coverLetterBadge}>1-Page PDF</div>
                  ) : (
                    activeDoc.ats_score != null && (
                      <div className={styles.atsScore} title="Estimated ATS Match Score">
                        {Math.round(activeDoc.ats_score)}% ATS Match
                      </div>
                    )
                  )}
                  <button
                    className={styles.downloadBtn}
                    onClick={handleDownloadPdf}
                    disabled={isDownloading}
                  >
                    {isDownloading ? (
                      <span className={styles.btnSpinner} />
                    ) : (
                      <Download size={15} strokeWidth={1.75} />
                    )}
                    <span>{isDownloading ? "Downloading…" : "Download PDF"}</span>
                  </button>
                </>
              )}
            </div>
          )}
        </div>

        <div className={styles.previewContent}>
          {isGenerating ? (
            <div className={styles.loadingState}>
              <div className={styles.spinner} />
              <p className={styles.loadingTitle}>
                {isColdEmailMode
                  ? "Crafting a concise, hook-driven cold email…"
                  : isCoverLetterMode
                    ? "Drafting a concise, tailored cover letter…"
                    : "Matching your profile against job requirements…"}
              </p>
              <p className={styles.loadingHint}>
                {isColdEmailMode
                  ? "Connecting your strongest relevant win to the role requirements for a high-reply recruiter hook."
                  : isCoverLetterMode
                    ? "Aligning relevant achievements from your profile and formatting your one-page letter PDF."
                    : "Extracting target keywords, rewriting experience bullets, and formatting your single-column PDF."}
              </p>
            </div>
          ) : isColdEmailMode ? (
            generatedColdEmail && coldEmailParagraphs.length > 0 ? (
              <div className={styles.documentPreview}>
                <div className={styles.paperSheet}>
                  <div className={styles.coverLetterMeta}>
                    <span className={styles.coverLetterSubject}>
                      Subject: {generatedColdEmail.subject}
                    </span>
                    {generatedColdEmail.recruiter_name && (
                      <span className={styles.docItemDate}>
                        To: {generatedColdEmail.recruiter_name}
                        {generatedColdEmail.company_name
                          ? ` (${generatedColdEmail.company_name})`
                          : ""}
                      </span>
                    )}
                  </div>
                  <div className={styles.coverLetterBody}>
                    {coldEmailParagraphs.map((paragraph, idx) => (
                      <p key={idx} className={styles.coverLetterParagraph}>
                        {paragraph}
                      </p>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <div className={styles.emptyPreview}>
                <div className={styles.emptyIconBox}>
                  <Send size={22} strokeWidth={1.75} />
                </div>
                <h3 className={styles.emptyPreviewTitle}>Live Cold Email Preview</h3>
                <p className={styles.emptyPreviewDesc}>
                  Enter the job posting and optional recruiter name on the left to generate a concise outreach email with a strong opening hook.
                </p>
              </div>
            )
          ) : isCoverLetterMode ? (
            generatedCoverLetter && coverLetterParagraphs.length > 0 ? (
              <div className={styles.documentPreview}>
                <div className={styles.paperSheet}>
                  {(generatedCoverLetter.job_title || generatedCoverLetter.company_name) && (
                    <div className={styles.coverLetterMeta}>
                      <span className={styles.coverLetterSubject}>
                        Re: Application
                        {generatedCoverLetter.job_title ? ` for ${generatedCoverLetter.job_title}` : ""}
                        {generatedCoverLetter.company_name
                          ? ` at ${generatedCoverLetter.company_name}`
                          : ""}
                      </span>
                    </div>
                  )}
                  <div className={styles.coverLetterBody}>
                    {coverLetterParagraphs.map((paragraph, idx) => (
                      <p key={idx} className={styles.coverLetterParagraph}>
                        {paragraph}
                      </p>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              <div className={styles.emptyPreview}>
                <div className={styles.emptyIconBox}>
                  <Mail size={22} strokeWidth={1.75} />
                </div>
                <h3 className={styles.emptyPreviewTitle}>Live Cover Letter Preview</h3>
                <p className={styles.emptyPreviewDesc}>
                  Paste a job description on the left to generate a concise, one-page cover letter ready to export as PDF.
                </p>
              </div>
            )
          ) : generatedCv && tailored ? (
            <div className={styles.documentPreview}>
              {/* Matched Keywords Bar */}
              {tailored.keywords_matched?.length > 0 && (
                <div className={styles.matchedKeywordsBox}>
                  <span className={styles.matchedKeywordsLabel}>
                    Matched Keywords ({tailored.keywords_matched.length})
                  </span>
                  <div className={styles.keywordChips}>
                    {tailored.keywords_matched.map((kw: string) => (
                      <span key={kw} className={styles.keywordChip}>
                        <Check size={12} strokeWidth={2.25} />
                        {kw}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {/* Actual Paper Document Preview */}
              <div className={styles.paperSheet}>
                {normalizePreviewOrder(tailored.section_order).map((section) => {
                  if (section === "summary" && tailored.professional_summary) {
                    return (
                      <section key="summary" className={styles.docSection}>
                        <h3 className={styles.docHeading}>Professional Summary</h3>
                        <p className={styles.docParagraph}>{tailored.professional_summary}</p>
                      </section>
                    );
                  }

                  if (section === "experience" && tailored.work_experiences?.length > 0) {
                    return (
                      <section key="experience" className={styles.docSection}>
                        <h3 className={styles.docHeading}>Professional Experience</h3>
                        <div className={styles.docList}>
                          {tailored.work_experiences.map((exp: any, i: number) => (
                            <div key={i} className={styles.docItem}>
                              <div className={styles.docItemHeader}>
                                <span className={styles.docItemTitle}>
                                  {exp.title} · {exp.company}
                                </span>
                                <span className={styles.docItemDate}>
                                  {exp.start_date || ""} – {exp.end_date || "Present"}
                                </span>
                              </div>
                              {exp.bullets?.length > 0 && (
                                <ul className={styles.docBullets}>
                                  {exp.bullets.map((b: string, j: number) => (
                                    <li key={j}>{b}</li>
                                  ))}
                                </ul>
                              )}
                            </div>
                          ))}
                        </div>
                      </section>
                    );
                  }

                  if (section === "education" && tailored.education?.length > 0) {
                    return (
                      <section key="education" className={styles.docSection}>
                        <h3 className={styles.docHeading}>Education</h3>
                        <div className={styles.docList}>
                          {tailored.education.map((edu: any, i: number) => (
                            <div key={i} className={styles.docItemHeader}>
                              <span className={styles.docItemTitle}>
                                {edu.degree}
                                {edu.field ? ` in ${edu.field}` : ""} · {edu.institution}
                              </span>
                              <span className={styles.docItemDate}>{edu.end_date || ""}</span>
                            </div>
                          ))}
                        </div>
                      </section>
                    );
                  }

                  if (section === "leadership" && tailored.leadership_activities?.length > 0) {
                    return (
                      <section key="leadership" className={styles.docSection}>
                        <h3 className={styles.docHeading}>Leadership &amp; Activity</h3>
                        <div className={styles.docList}>
                          {tailored.leadership_activities.map((act: any, i: number) => (
                            <div key={i} className={styles.docItem}>
                              <div className={styles.docItemHeader}>
                                <span className={styles.docItemTitle}>
                                  {act.title}
                                  {act.organization ? ` · ${act.organization}` : ""}
                                </span>
                                <span className={styles.docItemDate}>
                                  {act.start_date ? `${act.start_date} – ` : ""}
                                  {act.end_date || "Present"}
                                </span>
                              </div>
                              {act.bullets?.length > 0 && (
                                <ul className={styles.docBullets}>
                                  {act.bullets.map((b: string, j: number) => (
                                    <li key={j}>{b}</li>
                                  ))}
                                </ul>
                              )}
                            </div>
                          ))}
                        </div>
                      </section>
                    );
                  }

                  if (section === "certifications" && tailored.certifications?.length > 0) {
                    return (
                      <section key="certifications" className={styles.docSection}>
                        <h3 className={styles.docHeading}>Certifications</h3>
                        <ul className={styles.docBullets}>
                          {tailored.certifications.map((cert: any, i: number) => (
                            <li key={i}>
                              {/^https?:\/\//i.test(cert.url || "") ? (
                                <a
                                  href={cert.url}
                                  target="_blank"
                                  rel="noreferrer"
                                  style={{ color: "inherit", textDecoration: "none", fontWeight: 700 }}
                                >
                                  {cert.name}
                                </a>
                              ) : (
                                <strong>{cert.name}</strong>
                              )}
                              {cert.issuer ? ` – ${cert.issuer}` : ""}
                              {cert.date ? ` (${cert.date})` : ""}
                            </li>
                          ))}
                        </ul>
                      </section>
                    );
                  }

                  if (section === "projects" && tailored.projects?.length > 0) {
                    return (
                      <section key="projects" className={styles.docSection}>
                        <h3 className={styles.docHeading}>Projects</h3>
                        <div className={styles.docList}>
                          {tailored.projects.map((proj: any, i: number) => (
                            <div key={i} className={styles.docItem}>
                              <div className={styles.docItemHeader}>
                                <span className={styles.docItemTitle}>
                                  {/^https?:\/\//i.test(proj.url || "") ? (
                                    <a
                                      href={proj.url}
                                      target="_blank"
                                      rel="noreferrer"
                                      style={{ color: "inherit", textDecoration: "none" }}
                                    >
                                      {proj.name}
                                    </a>
                                  ) : (
                                    proj.name
                                  )}
                                </span>
                              </div>
                              {proj.description && (
                                <p className={styles.docParagraph}>{proj.description}</p>
                              )}
                              {proj.technologies?.length > 0 && (
                                <p className={styles.docParagraph}>
                                  <strong>Technologies:</strong> {proj.technologies.join(", ")}
                                </p>
                              )}
                            </div>
                          ))}
                        </div>
                      </section>
                    );
                  }

                  if (section === "skills" && tailored.skills?.length > 0) {
                    const isCategorized =
                      typeof tailored.skills[0] === "object" && tailored.skills[0] !== null;
                    return (
                      <section key="skills" className={styles.docSection}>
                        <h3 className={styles.docHeading}>Technical Skills</h3>
                        {isCategorized ? (
                          <div className={styles.docList}>
                            {tailored.skills.slice(0, 3).map((group: any, i: number) =>
                              group?.items?.length > 0 ? (
                                <p key={i} className={styles.docParagraph}>
                                  <strong>{group.category}:</strong> {group.items.join(", ")}
                                </p>
                              ) : null
                            )}
                          </div>
                        ) : (
                          <p className={styles.docParagraph}>{tailored.skills.join(" · ")}</p>
                        )}
                      </section>
                    );
                  }

                  return null;
                })}
              </div>
            </div>
          ) : generatedCv ? (
            <div className={styles.emptyPreview}>
              <div className={styles.emptyIconBox}>
                <FileSignature size={22} strokeWidth={1.75} />
              </div>
              <h3 className={styles.emptyPreviewTitle}>Tailored PDF Ready</h3>
              <p className={styles.emptyPreviewDesc}>
                Your tailored CV for {generatedCv.job_title || "this role"} is ready to download.
              </p>
              <button className={styles.downloadBtn} onClick={handleDownloadPdf}>
                <Download size={15} strokeWidth={1.75} />
                <span>Download PDF</span>
              </button>
            </div>
          ) : (
            <div className={styles.emptyPreview}>
              <div className={styles.emptyIconBox}>
                <FileSignature size={22} strokeWidth={1.75} />
              </div>
              <h3 className={styles.emptyPreviewTitle}>Live Resume Preview</h3>
              <p className={styles.emptyPreviewDesc}>
                Paste a job description on the left to inspect matched keywords, rewritten bullet points, and export your PDF.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function normalizePreviewOrder(rawOrder?: string[]): string[] {
  const core: string[] = [];
  for (const s of rawOrder || []) {
    if ((s === "experience" || s === "education") && !core.includes(s)) {
      core.push(s);
    }
  }
  for (const req of ["experience", "education"]) {
    if (!core.includes(req)) core.push(req);
  }
  return ["summary", ...core, "leadership", "certifications", "projects", "skills"];
}

