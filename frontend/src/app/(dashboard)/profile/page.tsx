"use client";

import { useEffect, useState, useRef, DragEvent, ChangeEvent, ReactNode, useCallback, Suspense } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import {
  UserCircle,
  Briefcase,
  GraduationCap,
  Settings,
  FileText,
  UploadCloud,
  Pencil,
  Save,
  Plus,
  Trash2,
  GripVertical,
  ArrowUp,
  ArrowDown,
  ArrowDownWideNarrow,
  ArrowRight,
  AlertCircle,
  CheckCircle,
  Award,
  FolderOpen,
  ExternalLink,
  Users,
} from "lucide-react";
import { useSession } from "next-auth/react";
import { apiClient } from "@/lib/api";
import { clearProfileOnboardingSkipped, markProfileOnboardingSkipped } from "@/lib/onboarding";
import styles from "./page.module.css";

type TabId = "profile" | "import";
type ReorderableSection = "work_experiences" | "certifications" | "projects";
type SortableDateSection = "work_experiences" | "certifications";
type ManualOrderPrefs = Record<SortableDateSection, boolean>;

const DEFAULT_MANUAL_ORDER: ManualOrderPrefs = {
  work_experiences: false,
  certifications: false,
};

function ProfilePageContent() {
  const { data: session, status, update } = useSession();
  const router = useRouter();
  const searchParams = useSearchParams();
  const isOnboarding = searchParams.get("onboarding") === "1";
  const [profile, setProfile] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<TabId>("profile");
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [formData, setFormData] = useState<any>(null);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [manualOrder, setManualOrder] = useState<ManualOrderPrefs>(DEFAULT_MANUAL_ORDER);
  const [dragSource, setDragSource] = useState<{ section: ReorderableSection; idx: number } | null>(
    null
  );
  const [dragOverTarget, setDragOverTarget] = useState<{
    section: ReorderableSection;
    idx: number;
  } | null>(null);

  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const token = (session as any)?.backendAccessToken;

  const applyInitialDateSort = useCallback((rawProfile: any, prefs: ManualOrderPrefs) => {
    const next = deepClone(rawProfile);
    if (!prefs.work_experiences && Array.isArray(next.work_experiences)) {
      next.work_experiences = sortWorkExperiencesDesc(next.work_experiences);
    }
    if (!prefs.certifications && Array.isArray(next.certifications)) {
      next.certifications = sortCertificationsDesc(next.certifications);
    }
    return next;
  }, []);

  const fetchProfile = useCallback(async () => {
    if (status !== "authenticated") return;
    try {
      const response = await apiClient.get("/profile/", {
        headers: { Authorization: `Bearer ${token}` },
      });
      const prefs = readManualOrderPref(response.data?.user_id);
      const prepared = applyInitialDateSort(response.data, prefs);
      setManualOrder(prefs);
      setProfile(prepared);
      setFormData(deepClone(prepared));
    } catch (err: any) {
      if (err.response?.status === 404) {
        setProfile(null);
      }
    } finally {
      setLoading(false);
    }
  }, [status, token, applyInitialDateSort]);

  useEffect(() => {
    fetchProfile();
  }, [fetchProfile]);

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(true);
  };
  const handleDragLeave = () => setIsDragging(false);
  const handleDrop = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files?.[0]) handleFileUpload(e.dataTransfer.files[0]);
  };
  const handleFileSelect = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files?.[0]) handleFileUpload(e.target.files[0]);
  };

  const handleFileUpload = async (file: File) => {
    setMessage(null);
    if (file.type !== "application/pdf") {
      setMessage({ type: "error", text: "Please upload a PDF file." });
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      setMessage({ type: "error", text: "File size exceeds the 10 MB limit." });
      return;
    }
    setIsUploading(true);
    const fd = new FormData();
    fd.append("file", file);
    try {
      const uploadResponse = await apiClient.post("/resume/upload", fd, {
        headers: { "Content-Type": "multipart/form-data", Authorization: `Bearer ${token}` },
      });
      writeManualOrderPref(uploadResponse.data?.user_id || profile?.user_id, DEFAULT_MANUAL_ORDER);
      clearProfileOnboardingSkipped(session?.user?.id);
      await update({ hasProfile: true });
      await fetchProfile();
      setMessage({ type: "success", text: "Resume parsed into your base profile." });
      setActiveTab("profile");
    } catch (err: any) {
      setMessage({ type: "error", text: err.response?.data?.detail || "Failed to parse resume." });
    } finally {
      setIsUploading(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    setMessage(null);
    try {
      const payload: any = {};
      if (formData.personal_info) payload.personal_info = formData.personal_info;
      if (formData.summary !== undefined) payload.summary = formData.summary;
      if (formData.work_experiences) {
        const normalizedWork = formData.work_experiences.map((exp: any) => ({
          ...exp,
          start_date: formatDateForSave(exp.start_date),
          end_date: formatDateForSave(exp.end_date),
        }));
        payload.work_experiences = manualOrder.work_experiences
          ? normalizedWork
          : sortWorkExperiencesDesc(normalizedWork);
      }
      if (formData.education) {
        payload.education = formData.education.map((edu: any) => ({
          ...edu,
          start_date: formatDateForSave(edu.start_date),
          end_date: formatDateForSave(edu.end_date),
        }));
      }
      if (formData.leadership_activities) {
        payload.leadership_activities = formData.leadership_activities.map((act: any) => ({
          ...act,
          start_date: formatDateForSave(act.start_date),
          end_date: formatDateForSave(act.end_date),
        }));
      }
      if (formData.skills) payload.skills = formData.skills;
      if (formData.certifications) {
        const normalizedCerts = formData.certifications.map((cert: any) => ({
          ...cert,
          date: formatDateForSave(cert.date),
        }));
        payload.certifications = manualOrder.certifications
          ? normalizedCerts
          : sortCertificationsDesc(normalizedCerts);
      }
      if (formData.projects) payload.projects = formData.projects;

      const response = await apiClient.put("/profile/", payload, {
        headers: { Authorization: `Bearer ${token}` },
      });
      writeManualOrderPref(response.data?.user_id || profile?.user_id, manualOrder);
      setProfile(response.data);
      setFormData(deepClone(response.data));
      setEditing(false);
      setDragSource(null);
      setDragOverTarget(null);
      setMessage({ type: "success", text: "Profile changes saved." });
      clearProfileOnboardingSkipped(session?.user?.id);
      await update({ hasProfile: true });
    } catch (err: any) {
      setMessage({ type: "error", text: err.response?.data?.detail || "Failed to save profile." });
    } finally {
      setSaving(false);
    }
  };

  const handleSkipOnboarding = () => {
    markProfileOnboardingSkipped(session?.user?.id);
    router.push("/dashboard");
  };

  const startEditing = () => {
    if (!formData) {
      setFormData({
        personal_info: {
          name: session?.user?.name || "",
          email: session?.user?.email || "",
          phone: "",
          location: "",
          linkedin_url: "",
          portfolio_url: "",
          other_url: "",
        },
        summary: "",
        work_experiences: [],
        education: [],
        leadership_activities: [],
        skills: { technical: [], soft: [], languages: [], tools: [] },
        certifications: [],
        projects: [],
      });
    }
    setEditing(true);
    setMessage(null);
  };

  const cancelEditing = () => {
    setFormData(profile ? deepClone(profile) : null);
    setManualOrder(readManualOrderPref(profile?.user_id));
    setDragSource(null);
    setDragOverTarget(null);
    setEditing(false);
    setMessage(null);
  };

  if (loading || status === "loading") {
    return (
      <div className={styles.loadingState}>
        <div className={styles.spinner} />
        <p>Loading your base profile…</p>
      </div>
    );
  }

  if (!profile && !editing) {
    return (
      <div className={styles.container}>
        <header className={styles.header}>
          <div>
            <h1 className={styles.title}>
              {isOnboarding ? "Set Up Your Base Career Profile" : "Base Career Profile"}
            </h1>
            <p className={styles.subtitle}>
              Import an existing PDF resume or enter your work history manually. You can skip this for now and complete it later.
            </p>
          </div>
          <div className={styles.saveBar}>
            <button type="button" className={styles.cancelBtn} onClick={handleSkipOnboarding}>
              <span>Skip for now</span>
              <ArrowRight size={15} strokeWidth={1.75} />
            </button>
          </div>
        </header>

        <div className={styles.emptyState}>
          <div className={styles.emptyCards}>
            <button
              type="button"
              className={styles.emptyCard}
              onClick={() => setActiveTab("import")}
            >
              <div className={styles.emptyCardIcon}>
                <UploadCloud size={22} strokeWidth={1.75} />
              </div>
              <span className={styles.emptyCardTitle}>Import from PDF Resume</span>
              <span className={styles.emptyCardDesc}>
                Upload your existing resume or LinkedIn PDF export to extract your experience automatically.
              </span>
            </button>

            <button
              type="button"
              className={styles.emptyCard}
              onClick={startEditing}
            >
              <div className={styles.emptyCardIcon}>
                <Pencil size={22} strokeWidth={1.75} />
              </div>
              <span className={styles.emptyCardTitle}>Enter Details Manually</span>
              <span className={styles.emptyCardDesc}>
                Build your base profile from scratch with structured work experience, education, and skills.
              </span>
            </button>
          </div>
        </div>

        {activeTab === "import" && (
          <ImportTab
            isDragging={isDragging}
            isUploading={isUploading}
            fileInputRef={fileInputRef}
            message={message}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            onFileSelect={handleFileSelect}
          />
        )}
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Base Career Profile</h1>
          <p className={styles.subtitle}>
            {editing
              ? "Update your contact details, work history, and skills below."
              : "Your canonical experience used when tailoring resumes to job descriptions."}
          </p>
        </div>

        {activeTab === "profile" && (
          <div className={styles.saveBar}>
            {!editing ? (
              <>
                <button className={styles.editBtn} onClick={startEditing}>
                  <Pencil size={15} strokeWidth={1.75} />
                  <span>Edit Profile</span>
                </button>
                {isOnboarding && (
                  <Link href="/dashboard" className={styles.saveBtn}>
                    <span>Continue to Dashboard</span>
                    <ArrowRight size={15} strokeWidth={1.75} />
                  </Link>
                )}
              </>
            ) : (
              <>
                {!profile && (
                  <button type="button" className={styles.cancelBtn} onClick={handleSkipOnboarding}>
                    <span>Skip for now</span>
                  </button>
                )}
                <button className={styles.cancelBtn} onClick={cancelEditing}>
                  Cancel
                </button>
                <button className={styles.saveBtn} onClick={handleSave} disabled={saving}>
                  <Save size={15} strokeWidth={1.75} />
                  <span>{saving ? "Saving…" : "Save Changes"}</span>
                </button>
              </>
            )}
          </div>
        )}
      </header>

      {/* Concentric Tab Switcher (Rule 14: outer radius 12px - 4px padding = 8px inner tab radius) */}
      <div className={styles.tabs}>
        <button
          className={`${styles.tab} ${activeTab === "profile" ? styles.tabActive : ""}`}
          onClick={() => setActiveTab("profile")}
        >
          <UserCircle size={16} strokeWidth={1.75} />
          <span>Structured Profile</span>
        </button>
        <button
          className={`${styles.tab} ${activeTab === "import" ? styles.tabActive : ""}`}
          onClick={() => setActiveTab("import")}
        >
          <UploadCloud size={16} strokeWidth={1.75} />
          <span>Re-import PDF</span>
        </button>
      </div>

      {message && (
        <div className={message.type === "success" ? styles.successMsg : styles.errorMsg}>
          {message.type === "success" ? (
            <CheckCircle size={18} strokeWidth={1.75} />
          ) : (
            <AlertCircle size={18} strokeWidth={1.75} />
          )}
          <span>{message.text}</span>
        </div>
      )}

      {activeTab === "profile" && (
        <div className={styles.sectionsStack}>
          {/* Contact Information */}
          <section className={styles.section}>
            <div className={styles.sectionHeader}>
              <h2 className={styles.sectionTitle}>
                <UserCircle size={19} strokeWidth={1.75} className={styles.sectionIcon} />
                <span>Contact Details</span>
              </h2>
            </div>
            {editing ? (
              <div className={styles.grid}>
                {["name", "email", "phone", "location", "linkedin_url", "portfolio_url", "other_url"].map((key) => (
                  <div key={key} className={styles.field}>
                    <label className={styles.fieldLabel}>{formatLabel(key)}</label>
                    <input
                      className={styles.input}
                      type={key.includes("url") ? "url" : key === "email" ? "email" : "text"}
                      value={formData?.personal_info?.[key] || ""}
                      placeholder={getPlaceholder(key)}
                      onChange={(e) => updateField("personal_info", key, e.target.value)}
                    />
                  </div>
                ))}
              </div>
            ) : (
              <div className={styles.contactGrid}>
                {["name", "email", "phone", "location", "linkedin_url", "portfolio_url", "other_url"].map((key) => {
                  const val = profile?.personal_info?.[key];
                  const safeHref = key.includes("url") ? toSafeHref(val) : null;
                  return (
                    <div key={key} className={styles.contactItem}>
                      <span className={styles.fieldLabel}>{formatLabel(key)}</span>
                      <div className={styles.contactValue}>
                        {val ? (
                          safeHref ? (
                            <a href={safeHref} target="_blank" rel="noreferrer" className={styles.externalLink}>
                              <span>{val}</span>
                              <ExternalLink size={13} strokeWidth={1.75} />
                            </a>
                          ) : (
                            val
                          )
                        ) : (
                          <span className={styles.emptyValue}>Not set</span>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </section>

          {/* Summary */}
          <section className={styles.section}>
            <div className={styles.sectionHeader}>
              <h2 className={styles.sectionTitle}>
                <FileText size={19} strokeWidth={1.75} className={styles.sectionIcon} />
                <span>Professional Summary</span>
              </h2>
            </div>
            {editing ? (
              <textarea
                className={styles.textarea}
                value={formData?.summary || ""}
                placeholder="Summarize your core domain expertise, years of experience, and key achievements…"
                onChange={(e) => setFormData({ ...formData, summary: e.target.value })}
              />
            ) : (
              <p className={styles.summaryText}>
                {profile?.summary || "No summary provided."}
              </p>
            )}
          </section>

          {/* Work Experience */}
          <section className={styles.section}>
            <div className={styles.sectionHeader}>
              <h2 className={styles.sectionTitle}>
                <Briefcase size={19} strokeWidth={1.75} className={styles.sectionIcon} />
                <span>Work Experience</span>
              </h2>
              {editing && (formData?.work_experiences || []).length > 1 && (
                <button
                  type="button"
                  className={styles.sortBtn}
                  onClick={() => sortSectionByDate("work_experiences")}
                  title="Sort experiences by latest date first"
                >
                  <ArrowDownWideNarrow size={14} strokeWidth={1.75} />
                  <span>Sort by Latest</span>
                </button>
              )}
            </div>
            {editing ? (
              <div className={styles.itemsStack}>
                <button
                  type="button"
                  className={styles.addBtn}
                  onClick={() =>
                    addListItem(
                      "work_experiences",
                      {
                        title: "",
                        company: "",
                        start_date: "",
                        end_date: "",
                        location: "",
                        bullets: [],
                      },
                      true
                    )
                  }
                >
                  <Plus size={16} strokeWidth={2} />
                  <span>Add Work Experience</span>
                </button>
                {(formData?.work_experiences || []).map((exp: any, idx: number, arr: any[]) => (
                  <SortableEditCard
                    key={idx}
                    section="work_experiences"
                    idx={idx}
                    total={arr.length}
                    title={
                      exp.title || exp.company
                        ? `${exp.title || "Role"}${exp.company ? ` · ${exp.company}` : ""}`
                        : "Position Details"
                    }
                    removeTitle="Remove position"
                    dragSource={dragSource}
                    dragOverTarget={dragOverTarget}
                    onDragStart={handleCardDragStart}
                    onDragOver={handleCardDragOver}
                    onDrop={handleCardDrop}
                    onDragEnd={handleCardDragEnd}
                    onMove={reorderListItem}
                    onRemove={() => removeListItem("work_experiences", idx)}
                  >
                    <div className={styles.inlineRow}>
                      <input
                        className={styles.input}
                        placeholder="Job Title"
                        value={exp.title || ""}
                        onChange={(e) => updateListItem("work_experiences", idx, "title", e.target.value)}
                      />
                      <input
                        className={styles.input}
                        placeholder="Company"
                        value={exp.company || ""}
                        onChange={(e) => updateListItem("work_experiences", idx, "company", e.target.value)}
                      />
                    </div>
                    <div className={styles.inlineRow}>
                      <MonthYearInput
                        label="Start Date"
                        value={exp.start_date || ""}
                        onChange={(val) => updateListItem("work_experiences", idx, "start_date", val)}
                      />
                      <EndDateField
                        label="End Date"
                        value={exp.end_date || ""}
                        onChange={(val) => updateListItem("work_experiences", idx, "end_date", val)}
                      />
                    </div>
                    <textarea
                      className={styles.textarea}
                      placeholder="Key achievements and impact (each bullet seperated by Enter)"
                      value={(exp.bullets || []).join("\n")}
                      onChange={(e) =>
                        updateListItem("work_experiences", idx, "bullets", e.target.value.split("\n"))
                      }
                    />
                  </SortableEditCard>
                ))}
              </div>
            ) : (profile?.work_experiences || []).length > 0 ? (
              <div className={styles.itemsStack}>
                {profile.work_experiences.map((exp: any, idx: number) => (
                  <div key={idx} className={styles.listItem}>
                    <div className={styles.listItemHeader}>
                      <div>
                        <div className={styles.itemTitle}>{exp.title}</div>
                        <div className={styles.itemSubtitle}>{exp.company}</div>
                      </div>
                      <div className={styles.itemDate}>
                        {exp.start_date || ""} – {exp.end_date || "Present"}
                      </div>
                    </div>
                    {exp.bullets?.length > 0 && (
                      <ul className={styles.bulletList}>
                        {exp.bullets.map((b: string, bIdx: number) => (
                          <li key={bIdx}>{b}</li>
                        ))}
                      </ul>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className={styles.emptySectionText}>No work experience added yet.</p>
            )}
          </section>

          {/* Education */}
          <section className={styles.section}>
            <div className={styles.sectionHeader}>
              <h2 className={styles.sectionTitle}>
                <GraduationCap size={19} strokeWidth={1.75} className={styles.sectionIcon} />
                <span>Education</span>
              </h2>
            </div>
            {editing ? (
              <div className={styles.itemsStack}>
                {(formData?.education || []).map((edu: any, idx: number) => (
                  <div key={idx} className={styles.listItemEdit}>
                    <div className={styles.listItemEditHeader}>
                      <span className={styles.listItemEditTitle}>
                        {edu.institution || edu.degree || "Academic Entry"}
                      </span>
                      <button
                        type="button"
                        className={styles.removeBtn}
                        onClick={() => removeListItem("education", idx)}
                        title="Remove education"
                      >
                        <Trash2 size={15} strokeWidth={1.75} />
                      </button>
                    </div>
                    <input
                      className={styles.input}
                      placeholder="Institution"
                      value={edu.institution || ""}
                      onChange={(e) => updateListItem("education", idx, "institution", e.target.value)}
                    />
                    <div className={styles.inlineRow}>
                      <input
                        className={styles.input}
                        placeholder="Degree (e.g. B.S.)"
                        value={edu.degree || ""}
                        onChange={(e) => updateListItem("education", idx, "degree", e.target.value)}
                      />
                      <input
                        className={styles.input}
                        placeholder="Field of Study"
                        value={edu.field || ""}
                        onChange={(e) => updateListItem("education", idx, "field", e.target.value)}
                      />
                    </div>
                    <div className={styles.inlineRow}>
                      <MonthYearInput
                        label="Start Date"
                        value={edu.start_date || ""}
                        onChange={(val) => updateListItem("education", idx, "start_date", val)}
                      />
                      <EndDateField
                        label="End Date"
                        value={edu.end_date || ""}
                        onChange={(val) => updateListItem("education", idx, "end_date", val)}
                      />
                    </div>
                    <input
                      className={styles.input}
                      placeholder="GPA (optional, e.g. 3.8/4.0)"
                      value={edu.gpa || ""}
                      onChange={(e) => updateListItem("education", idx, "gpa", e.target.value)}
                    />
                    <CommaSeparatedInput
                      values={edu.relevant_coursework || []}
                      placeholder="Relevant coursework (comma-separated)"
                      ariaLabel="Relevant coursework"
                      onChange={(next) =>
                        updateListItem("education", idx, "relevant_coursework", next)
                      }
                    />
                  </div>
                ))}
                <button
                  type="button"
                  className={styles.addBtn}
                  onClick={() =>
                    addListItem("education", {
                      institution: "",
                      degree: "",
                      field: "",
                      start_date: "",
                      end_date: "",
                      gpa: "",
                      relevant_coursework: [],
                    })
                  }
                >
                  <Plus size={16} strokeWidth={2} />
                  <span>Add Education</span>
                </button>
              </div>
            ) : (profile?.education || []).length > 0 ? (
              <div className={styles.itemsStack}>
                {profile.education.map((edu: any, idx: number) => (
                  <div key={idx} className={styles.listItem}>
                    <div className={styles.listItemHeader}>
                      <div>
                        <div className={styles.itemTitle}>{edu.institution}</div>
                        <div className={styles.itemSubtitle}>
                          {edu.degree} {edu.field ? `in ${edu.field}` : ""}
                        </div>
                      </div>
                      <div className={styles.itemDate}>
                        {edu.start_date ? `${edu.start_date} – ` : ""}
                        {edu.end_date || ""}
                      </div>
                    </div>
                    {edu.gpa && <div className={styles.gpaMeta}>GPA: {edu.gpa}</div>}
                    {edu.relevant_coursework?.length > 0 && (
                      <div className={styles.courseworkWrap}>
                        <div className={styles.tagList}>
                          {edu.relevant_coursework.map((c: string, cIdx: number) => (
                            <span key={cIdx} className={styles.tag}>
                              {c}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className={styles.emptySectionText}>No education added yet.</p>
            )}
          </section>

          {/* Leadership & Activity */}
          <section className={styles.section}>
            <div className={styles.sectionHeader}>
              <h2 className={styles.sectionTitle}>
                <Users size={19} strokeWidth={1.75} className={styles.sectionIcon} />
                <span>Leadership &amp; Activity</span>
              </h2>
            </div>
            {editing ? (
              <div className={styles.itemsStack}>
                {(formData?.leadership_activities || []).map((act: any, idx: number) => (
                  <div key={idx} className={styles.listItemEdit}>
                    <div className={styles.listItemEditHeader}>
                      <span className={styles.listItemEditTitle}>
                        {act.title || act.organization
                          ? `${act.title || "Role"}${act.organization ? ` · ${act.organization}` : ""}`
                          : "Activity Details"}
                      </span>
                      <button
                        type="button"
                        className={styles.removeBtn}
                        onClick={() => removeListItem("leadership_activities", idx)}
                        title="Remove activity"
                      >
                        <Trash2 size={15} strokeWidth={1.75} />
                      </button>
                    </div>
                    <div className={styles.inlineRow}>
                      <input
                        className={styles.input}
                        placeholder="Role / Title (e.g. Teaching Assistant)"
                        value={act.title || ""}
                        onChange={(e) =>
                          updateListItem("leadership_activities", idx, "title", e.target.value)
                        }
                      />
                      <input
                        className={styles.input}
                        placeholder="Organization"
                        value={act.organization || ""}
                        onChange={(e) =>
                          updateListItem("leadership_activities", idx, "organization", e.target.value)
                        }
                      />
                    </div>
                    <div className={styles.inlineRow}>
                      <MonthYearInput
                        label="Start Date"
                        value={act.start_date || ""}
                        onChange={(val) =>
                          updateListItem("leadership_activities", idx, "start_date", val)
                        }
                      />
                      <EndDateField
                        label="End Date"
                        value={act.end_date || ""}
                        onChange={(val) =>
                          updateListItem("leadership_activities", idx, "end_date", val)
                        }
                      />
                    </div>
                    <input
                      className={styles.input}
                      placeholder="Location (optional)"
                      value={act.location || ""}
                      onChange={(e) =>
                        updateListItem("leadership_activities", idx, "location", e.target.value)
                      }
                    />
                    <textarea
                      className={styles.textarea}
                      placeholder="Key contributions and impact (each bullet seperated by Enter)"
                      value={(act.bullets || []).join("\n")}
                      onChange={(e) =>
                        updateListItem(
                          "leadership_activities",
                          idx,
                          "bullets",
                          e.target.value.split("\n")
                        )
                      }
                    />
                  </div>
                ))}
                <button
                  type="button"
                  className={styles.addBtn}
                  onClick={() =>
                    addListItem("leadership_activities", {
                      title: "",
                      organization: "",
                      start_date: "",
                      end_date: "",
                      location: "",
                      bullets: [],
                    })
                  }
                >
                  <Plus size={16} strokeWidth={2} />
                  <span>Add Leadership / Activity</span>
                </button>
              </div>
            ) : (profile?.leadership_activities || []).length > 0 ? (
              <div className={styles.itemsStack}>
                {profile.leadership_activities.map((act: any, idx: number) => (
                  <div key={idx} className={styles.listItem}>
                    <div className={styles.listItemHeader}>
                      <div>
                        <div className={styles.itemTitle}>{act.title}</div>
                        <div className={styles.itemSubtitle}>
                          {act.organization}
                          {act.location ? ` · ${act.location}` : ""}
                        </div>
                      </div>
                      <div className={styles.itemDate}>
                        {act.start_date ? `${act.start_date} – ` : ""}
                        {act.end_date || "Present"}
                      </div>
                    </div>
                    {act.bullets?.length > 0 && (
                      <ul className={styles.bulletList}>
                        {act.bullets.map((b: string, bIdx: number) => (
                          <li key={bIdx}>{b}</li>
                        ))}
                      </ul>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <p className={styles.emptySectionText}>No leadership or activities added yet.</p>
            )}
          </section>

          {/* Skills */}
          <section className={styles.section}>
            <div className={styles.sectionHeader}>
              <h2 className={styles.sectionTitle}>
                <Settings size={19} strokeWidth={1.75} className={styles.sectionIcon} />
                <span>Skills</span>
              </h2>
            </div>
            {editing ? (
              <div className={styles.skillsStack}>
                {["technical", "soft", "tools", "languages"].map((category) => (
                  <SkillTagEditor
                    key={category}
                    label={formatLabel(category)}
                    tags={formData?.skills?.[category] || []}
                    onChange={(tags) => {
                      setFormData({
                        ...formData,
                        skills: { ...(formData?.skills || {}), [category]: tags },
                      });
                    }}
                  />
                ))}
              </div>
            ) : (
              <div className={styles.skillsStack}>
                {["technical", "soft", "tools", "languages"].map((category) => {
                  const items = profile?.skills?.[category] || [];
                  if (items.length === 0) return null;
                  return (
                    <div key={category} className={styles.skillGroup}>
                      <span className={styles.fieldLabel}>{formatLabel(category)}</span>
                      <div className={styles.tagList}>
                        {items.map((s: string, i: number) => (
                          <span key={i} className={styles.tag}>
                            {s}
                          </span>
                        ))}
                      </div>
                    </div>
                  );
                })}
                {!profile?.skills && (
                  <p className={styles.emptySectionText}>No skills added yet.</p>
                )}
              </div>
            )}
          </section>

          {/* Certifications */}
          <section className={styles.section}>
            <div className={styles.sectionHeader}>
              <h2 className={styles.sectionTitle}>
                <Award size={19} strokeWidth={1.75} className={styles.sectionIcon} />
                <span>Certifications</span>
              </h2>
              {editing && (formData?.certifications || []).length > 1 && (
                <button
                  type="button"
                  className={styles.sortBtn}
                  onClick={() => sortSectionByDate("certifications")}
                  title="Sort certifications by latest date first"
                >
                  <ArrowDownWideNarrow size={14} strokeWidth={1.75} />
                  <span>Sort by Latest</span>
                </button>
              )}
            </div>
            {editing ? (
              <div className={styles.itemsStack}>
                <button
                  type="button"
                  className={styles.addBtn}
                  onClick={() =>
                    addListItem(
                      "certifications",
                      {
                        name: "",
                        issuer: "",
                        date: "",
                        credential_id: "",
                        url: "",
                      },
                      true
                    )
                  }
                >
                  <Plus size={16} strokeWidth={2} />
                  <span>Add Certification</span>
                </button>
                {(formData?.certifications || []).map((cert: any, idx: number, arr: any[]) => (
                  <SortableEditCard
                    key={idx}
                    section="certifications"
                    idx={idx}
                    total={arr.length}
                    title={cert.name || "Certification"}
                    removeTitle="Remove certification"
                    dragSource={dragSource}
                    dragOverTarget={dragOverTarget}
                    onDragStart={handleCardDragStart}
                    onDragOver={handleCardDragOver}
                    onDrop={handleCardDrop}
                    onDragEnd={handleCardDragEnd}
                    onMove={reorderListItem}
                    onRemove={() => removeListItem("certifications", idx)}
                  >
                    <input
                      className={styles.input}
                      placeholder="Certification Name"
                      value={cert.name || ""}
                      onChange={(e) => updateListItem("certifications", idx, "name", e.target.value)}
                    />
                    <div className={styles.inlineRow}>
                      <div className={styles.field}>
                        <label className={styles.fieldLabel}>Issuing Organization</label>
                        <input
                          className={styles.input}
                          placeholder="e.g., Amazon Web Services"
                          value={cert.issuer || ""}
                          onChange={(e) => updateListItem("certifications", idx, "issuer", e.target.value)}
                        />
                      </div>
                      <MonthYearInput
                        label="Date Obtained"
                        value={cert.date || ""}
                        onChange={(val) => updateListItem("certifications", idx, "date", val)}
                      />
                    </div>
                    <div className={styles.inlineRow}>
                      <input
                        className={styles.input}
                        placeholder="Credential ID (optional)"
                        value={cert.credential_id || ""}
                        onChange={(e) =>
                          updateListItem("certifications", idx, "credential_id", e.target.value)
                        }
                      />
                      <input
                        className={styles.input}
                        type="url"
                        placeholder="Certificate URL (optional, e.g. https://credly.com/...)"
                        value={cert.url || ""}
                        onChange={(e) =>
                          updateListItem("certifications", idx, "url", e.target.value)
                        }
                      />
                    </div>
                  </SortableEditCard>
                ))}
              </div>
            ) : (profile?.certifications || []).length > 0 ? (
              <div className={styles.itemsStack}>
                {profile.certifications.map((cert: any, idx: number) => {
                  const safeCertHref = toSafeHref(cert.url);
                  return (
                    <div key={idx} className={styles.listItem}>
                      <div className={styles.listItemHeader}>
                        <div>
                          <div className={styles.itemTitle}>
                            {safeCertHref ? (
                              <a href={safeCertHref} target="_blank" rel="noreferrer" className={styles.externalLink}>
                                <span>{cert.name}</span>
                                <ExternalLink size={12} strokeWidth={1.75} />
                              </a>
                            ) : (
                              cert.name
                            )}
                          </div>
                          {cert.issuer && <div className={styles.itemSubtitle}>{cert.issuer}</div>}
                        </div>
                        <div className={styles.itemDate}>{cert.date || ""}</div>
                      </div>
                      {cert.credential_id && (
                        <div className={styles.credentialCode}>ID: {cert.credential_id}</div>
                      )}
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className={styles.emptySectionText}>No certifications added yet.</p>
            )}
          </section>

          {/* Projects */}
          <section className={styles.section}>
            <div className={styles.sectionHeader}>
              <h2 className={styles.sectionTitle}>
                <FolderOpen size={19} strokeWidth={1.75} className={styles.sectionIcon} />
                <span>Projects</span>
              </h2>
            </div>
            {editing ? (
              <div className={styles.itemsStack}>
                <button
                  type="button"
                  className={styles.addBtn}
                  onClick={() =>
                    addListItem(
                      "projects",
                      {
                        name: "",
                        description: "",
                        technologies: [],
                        url: "",
                      },
                      true
                    )
                  }
                >
                  <Plus size={16} strokeWidth={2} />
                  <span>Add Project</span>
                </button>
                {(formData?.projects || []).map((proj: any, idx: number, arr: any[]) => (
                  <SortableEditCard
                    key={idx}
                    section="projects"
                    idx={idx}
                    total={arr.length}
                    title={proj.name || "Project"}
                    removeTitle="Remove project"
                    dragSource={dragSource}
                    dragOverTarget={dragOverTarget}
                    onDragStart={handleCardDragStart}
                    onDragOver={handleCardDragOver}
                    onDrop={handleCardDrop}
                    onDragEnd={handleCardDragEnd}
                    onMove={reorderListItem}
                    onRemove={() => removeListItem("projects", idx)}
                  >
                    <input
                      className={styles.input}
                      placeholder="Project Name"
                      value={proj.name || ""}
                      onChange={(e) => updateListItem("projects", idx, "name", e.target.value)}
                    />
                    <textarea
                      className={styles.textarea}
                      placeholder="What you built and its measurable outcome…"
                      value={proj.description || ""}
                      onChange={(e) =>
                        updateListItem("projects", idx, "description", e.target.value)
                      }
                    />
                    <CommaSeparatedInput
                      values={proj.technologies || []}
                      placeholder="Technologies (comma-separated)"
                      ariaLabel="Project technologies"
                      onChange={(next) => updateListItem("projects", idx, "technologies", next)}
                    />
                    <input
                      className={styles.input}
                      placeholder="Project URL (optional)"
                      value={proj.url || ""}
                      onChange={(e) => updateListItem("projects", idx, "url", e.target.value)}
                    />
                  </SortableEditCard>
                ))}
              </div>
            ) : (profile?.projects || []).length > 0 ? (
              <div className={styles.itemsStack}>
                {profile.projects.map((proj: any, idx: number) => {
                  const safeProjHref = toSafeHref(proj.url);
                  return (
                    <div key={idx} className={styles.listItem}>
                      <div className={styles.listItemHeader}>
                        <div>
                          <div className={styles.itemTitle}>{proj.name}</div>
                          {safeProjHref && (
                            <a
                              href={safeProjHref}
                              target="_blank"
                              rel="noreferrer"
                              className={styles.externalLink}
                            >
                              <span>{proj.url}</span>
                              <ExternalLink size={12} strokeWidth={1.75} />
                            </a>
                          )}
                        </div>
                      </div>
                      {proj.description && (
                        <p className={styles.projectDesc}>{proj.description}</p>
                      )}
                      {proj.technologies?.length > 0 && (
                        <div className={styles.tagList}>
                          {proj.technologies.map((t: string, tIdx: number) => (
                            <span key={tIdx} className={styles.tag}>
                              {t}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            ) : (
              <p className={styles.emptySectionText}>No projects added yet.</p>
            )}
          </section>

          {editing && (
            <div className={styles.saveBar}>
              <button className={styles.cancelBtn} onClick={cancelEditing}>
                Cancel
              </button>
              <button className={styles.saveBtn} onClick={handleSave} disabled={saving}>
                <Save size={15} strokeWidth={1.75} />
                <span>{saving ? "Saving…" : "Save Changes"}</span>
              </button>
            </div>
          )}
        </div>
      )}

      {activeTab === "import" && (
        <ImportTab
          isDragging={isDragging}
          isUploading={isUploading}
          fileInputRef={fileInputRef}
          message={message}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          onDrop={handleDrop}
          onFileSelect={handleFileSelect}
        />
      )}
    </div>
  );

  function updateField(section: string, key: string, value: string) {
    setFormData({
      ...formData,
      [section]: { ...(formData?.[section] || {}), [key]: value },
    });
  }

  function updateListItem(section: string, idx: number, key: string, value: any) {
    const items = [...(formData?.[section] || [])];
    items[idx] = { ...items[idx], [key]: value };
    setFormData({ ...formData, [section]: items });
  }

  function addListItem(section: string, template: any, prepend = false) {
    const existing = formData?.[section] || [];
    setFormData({
      ...formData,
      [section]: prepend ? [template, ...existing] : [...existing, template],
    });
  }

  function removeListItem(section: string, idx: number) {
    const items = [...(formData?.[section] || [])];
    items.splice(idx, 1);
    setFormData({ ...formData, [section]: items });
    setDragSource(null);
    setDragOverTarget(null);
  }

  function reorderListItem(section: ReorderableSection, fromIdx: number, toIdx: number) {
    const items = [...(formData?.[section] || [])];
    if (
      fromIdx === toIdx ||
      fromIdx < 0 ||
      toIdx < 0 ||
      fromIdx >= items.length ||
      toIdx >= items.length
    ) {
      return;
    }
    if (document.activeElement instanceof HTMLElement) {
      document.activeElement.blur();
    }
    const [moved] = items.splice(fromIdx, 1);
    items.splice(toIdx, 0, moved);
    setFormData({ ...formData, [section]: items });
    if (section === "work_experiences" || section === "certifications") {
      setManualOrder((prev) => ({ ...prev, [section]: true }));
    }
  }

  function sortSectionByDate(section: SortableDateSection) {
    const items = [...(formData?.[section] || [])];
    const sorted =
      section === "work_experiences"
        ? sortWorkExperiencesDesc(items)
        : sortCertificationsDesc(items);
    setFormData({ ...formData, [section]: sorted });
    setManualOrder((prev) => ({ ...prev, [section]: false }));
  }

  function handleCardDragStart(
    e: DragEvent<HTMLDivElement>,
    section: ReorderableSection,
    idx: number
  ) {
    e.dataTransfer.effectAllowed = "move";
    e.dataTransfer.setData("text/plain", `${section}:${idx}`);
    setDragSource({ section, idx });
    setDragOverTarget({ section, idx });
  }

  function handleCardDragOver(
    e: DragEvent<HTMLDivElement>,
    section: ReorderableSection,
    idx: number
  ) {
    if (!dragSource || dragSource.section !== section) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    if (!dragOverTarget || dragOverTarget.section !== section || dragOverTarget.idx !== idx) {
      setDragOverTarget({ section, idx });
    }
  }

  function handleCardDrop(
    e: DragEvent<HTMLDivElement>,
    section: ReorderableSection,
    targetIdx: number
  ) {
    if (!dragSource || dragSource.section !== section) return;
    e.preventDefault();
    reorderListItem(section, dragSource.idx, targetIdx);
    setDragSource(null);
    setDragOverTarget(null);
  }

  function handleCardDragEnd() {
    setDragSource(null);
    setDragOverTarget(null);
  }
}

function SortableEditCard({
  section,
  idx,
  total,
  title,
  removeTitle,
  dragSource,
  dragOverTarget,
  onDragStart,
  onDragOver,
  onDrop,
  onDragEnd,
  onMove,
  onRemove,
  children,
}: {
  section: ReorderableSection;
  idx: number;
  total: number;
  title: string;
  removeTitle: string;
  dragSource: { section: ReorderableSection; idx: number } | null;
  dragOverTarget: { section: ReorderableSection; idx: number } | null;
  onDragStart: (e: DragEvent<HTMLDivElement>, section: ReorderableSection, idx: number) => void;
  onDragOver: (e: DragEvent<HTMLDivElement>, section: ReorderableSection, idx: number) => void;
  onDrop: (e: DragEvent<HTMLDivElement>, section: ReorderableSection, idx: number) => void;
  onDragEnd: () => void;
  onMove: (section: ReorderableSection, fromIdx: number, toIdx: number) => void;
  onRemove: () => void;
  children: ReactNode;
}) {
  const cardRef = useRef<HTMLDivElement>(null);
  const isDragging = dragSource?.section === section && dragSource.idx === idx;
  const isDropTarget =
    dragOverTarget?.section === section &&
    dragOverTarget.idx === idx &&
    dragSource?.section === section &&
    dragSource.idx !== idx;

  const setCardDraggable = (enabled: boolean) => {
    if (cardRef.current) {
      cardRef.current.draggable = enabled;
    }
  };

  return (
    <div
      ref={cardRef}
      className={`${styles.listItemEdit} ${isDragging ? styles.listItemEditDragging : ""} ${
        isDropTarget ? styles.listItemEditDropTarget : ""
      }`}
      onDragStart={(e) => onDragStart(e, section, idx)}
      onDragOver={(e) => onDragOver(e, section, idx)}
      onDrop={(e) => {
        setCardDraggable(false);
        onDrop(e, section, idx);
      }}
      onDragEnd={() => {
        setCardDraggable(false);
        onDragEnd();
      }}
    >
      <div className={styles.listItemEditHeader}>
        <div className={styles.listItemEditTitleGroup}>
          <button
            type="button"
            className={styles.dragHandle}
            onMouseDown={() => setCardDraggable(true)}
            onMouseUp={() => setCardDraggable(false)}
            aria-label={`Drag to reorder ${title}`}
            title="Drag to reorder"
          >
            <GripVertical size={15} strokeWidth={1.75} />
          </button>
          <span className={styles.listItemEditTitle}>{title}</span>
        </div>
        <div className={styles.listItemEditActions}>
          <button
            type="button"
            className={styles.reorderBtn}
            onClick={() => onMove(section, idx, idx - 1)}
            disabled={idx === 0}
            aria-label={`Move ${title} up`}
            title="Move up"
          >
            <ArrowUp size={14} strokeWidth={1.75} />
          </button>
          <button
            type="button"
            className={styles.reorderBtn}
            onClick={() => onMove(section, idx, idx + 1)}
            disabled={idx >= total - 1}
            aria-label={`Move ${title} down`}
            title="Move down"
          >
            <ArrowDown size={14} strokeWidth={1.75} />
          </button>
          <button
            type="button"
            className={styles.removeBtn}
            onClick={onRemove}
            title={removeTitle}
            aria-label={removeTitle}
          >
            <Trash2 size={15} strokeWidth={1.75} />
          </button>
        </div>
      </div>
      {children}
    </div>
  );
}

function ImportTab({
  isDragging,
  isUploading,
  fileInputRef,
  onDragOver,
  onDragLeave,
  onDrop,
  onFileSelect,
}: any) {
  return (
    <div
      className={`${styles.dropzone} ${isDragging ? styles.dropzoneActive : ""}`}
      onDragOver={onDragOver}
      onDragLeave={onDragLeave}
      onDrop={onDrop}
      onClick={() => fileInputRef.current?.click()}
    >
      {isUploading && (
        <div className={styles.loadingOverlay}>
          <div className={styles.spinner} />
          <p className={styles.loadingText}>Extracting structured profile from your PDF…</p>
        </div>
      )}
      <div className={styles.uploadIconBox}>
        <UploadCloud size={26} strokeWidth={1.75} />
      </div>
      <h3 className={styles.dropzoneText}>Drop your PDF resume here or click to browse</h3>
      <p className={styles.dropzoneSubtext}>
        Supports standard resumes and LinkedIn PDF exports up to 10 MB
      </p>
      <input
        type="file"
        ref={fileInputRef}
        onChange={onFileSelect}
        accept="application/pdf"
        className={styles.fileInput}
      />
      <span className={styles.browseBtn}>Select PDF File</span>
    </div>
  );
}

function CommaSeparatedInput({
  values,
  placeholder,
  ariaLabel,
  onChange,
}: {
  values: string[];
  placeholder: string;
  ariaLabel: string;
  onChange: (next: string[]) => void;
}) {
  const normalizedValues = normalizeTagList(values || []);
  const externalFormatted = normalizedValues.join(", ");
  const [rawText, setRawText] = useState(externalFormatted);
  const [isFocused, setIsFocused] = useState(false);

  // Preserve raw typed commas/spaces while focused; normalize from props otherwise.
  const displayValue = isFocused ? rawText : externalFormatted;

  const commitIfChanged = (candidateRaw: string) => {
    const parsed = parseTagList(candidateRaw);
    if (!tagListsEqual(parsed, normalizedValues)) {
      onChange(parsed);
    }
    return parsed;
  };

  return (
    <input
      type="text"
      className={styles.input}
      placeholder={placeholder}
      aria-label={ariaLabel}
      maxLength={MAX_RAW_COMMA_INPUT_LENGTH}
      value={displayValue}
      onFocus={() => {
        setRawText(externalFormatted);
        setIsFocused(true);
      }}
      onChange={(e) => {
        const sanitizedRaw = stripUnsafeInputChars(e.target.value).slice(
          0,
          MAX_RAW_COMMA_INPUT_LENGTH
        );
        setRawText(sanitizedRaw);
        commitIfChanged(sanitizedRaw);
      }}
      onBlur={() => {
        commitIfChanged(rawText);
        setIsFocused(false);
      }}
    />
  );
}

function SkillTagEditor({
  label,
  tags,
  onChange,
}: {
  label: string;
  tags: string[];
  onChange: (tags: string[]) => void;
}) {
  const [input, setInput] = useState("");

  const addTags = (rawValue: string) => {
    const incoming = parseTagList(rawValue);
    if (incoming.length === 0) return;
    const merged = normalizeTagList([...tags, ...incoming]);
    onChange(merged);
    setInput("");
  };

  return (
    <div className={styles.skillGroup}>
      <span className={styles.fieldLabel}>{label}</span>
      {tags.length > 0 && (
        <div className={styles.tagList}>
          {tags.map((tag, i) => (
            <span key={i} className={styles.tag}>
              <span>{tag}</span>
              <button
                type="button"
                className={styles.tagRemove}
                onClick={() => onChange(tags.filter((_, j) => j !== i))}
                aria-label={`Remove ${tag}`}
              >
                ×
              </button>
            </span>
          ))}
        </div>
      )}
      <div className={styles.tagInput}>
        <input
          className={styles.input}
          value={input}
          maxLength={MAX_RAW_COMMA_INPUT_LENGTH}
          placeholder={`Add ${label.toLowerCase()} skill and press Enter or comma…`}
          onChange={(e) =>
            setInput(stripUnsafeInputChars(e.target.value).slice(0, MAX_RAW_COMMA_INPUT_LENGTH))
          }
          onKeyDown={(e) => {
            if (e.key === "Enter" || (e.key === "," && input.trim())) {
              e.preventDefault();
              addTags(input);
            }
          }}
        />
        <button
          className={styles.tagAddBtn}
          onClick={() => addTags(input)}
          type="button"
          aria-label="Add skill"
        >
          <Plus size={16} strokeWidth={2} />
        </button>
      </div>
    </div>
  );
}

function MonthYearInput({
  label,
  value,
  disabled = false,
  onChange,
}: {
  label: string;
  value: string;
  disabled?: boolean;
  onChange: (value: string) => void;
}) {
  const [draftMonth, setDraftMonth] = useState("");
  const parsed = disabled ? null : parseMonthYearParts(value);
  const selectedYear = parsed?.year || "";
  const selectedMonth = disabled ? "" : selectedYear ? parsed?.month || "" : draftMonth;
  const yearOptions = getYearOptions(selectedYear);

  const emitMonthYear = (nextMonth: string, nextYear: string) => {
    if (disabled) return;
    if (!nextYear) {
      setDraftMonth(nextMonth);
      if (value) onChange("");
      return;
    }
    setDraftMonth("");
    if (nextMonth) {
      const monthName = SHORT_MONTHS[parseInt(nextMonth, 10) - 1];
      onChange(monthName ? `${monthName} ${nextYear}` : `${nextYear}-${nextMonth}`);
    } else {
      onChange(nextYear);
    }
  };

  return (
    <div className={styles.field}>
      <label className={styles.fieldLabel}>{label}</label>
      <div className={styles.monthYearRow}>
        <select
          className={styles.dateSelect}
          aria-label={`${label} month`}
          value={selectedMonth}
          disabled={disabled}
          onChange={(e) => emitMonthYear(e.target.value, selectedYear)}
        >
          <option value="">Month</option>
          {MONTH_OPTIONS.map((m) => (
            <option key={m.value} value={m.value}>
              {m.label}
            </option>
          ))}
        </select>
        <select
          className={styles.dateSelect}
          aria-label={`${label} year`}
          value={selectedYear}
          disabled={disabled}
          onChange={(e) => emitMonthYear(selectedMonth, e.target.value)}
        >
          <option value="">Year</option>
          {yearOptions.map((yr) => (
            <option key={yr} value={yr}>
              {yr}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}

function EndDateField({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
}) {
  const isPresent = /^(present|current|now)$/i.test((value || "").trim());
  return (
    <div className={styles.endDateWrap}>
      <MonthYearInput
        label={label}
        value={value}
        disabled={isPresent}
        onChange={onChange}
      />
      <label className={styles.presentCheckLabel}>
        <input
          type="checkbox"
          className={styles.presentCheckbox}
          checked={isPresent}
          onChange={(e) => onChange(e.target.checked ? "Present" : "")}
        />
        <span>Present</span>
      </label>
    </div>
  );
}

const MONTH_INDEX: Record<string, string> = {
  jan: "01",
  january: "01",
  feb: "02",
  february: "02",
  mar: "03",
  march: "03",
  apr: "04",
  april: "04",
  may: "05",
  jun: "06",
  june: "06",
  jul: "07",
  july: "07",
  aug: "08",
  august: "08",
  sep: "09",
  sept: "09",
  september: "09",
  oct: "10",
  october: "10",
  nov: "11",
  november: "11",
  dec: "12",
  december: "12",
};

const SHORT_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const MONTH_OPTIONS = SHORT_MONTHS.map((label, idx) => ({
  value: String(idx + 1).padStart(2, "0"),
  label,
}));

function getYearOptions(selectedYear: string): string[] {
  const maxYear = new Date().getFullYear() + 6;
  const minYear = 1960;
  const years: string[] = [];
  for (let yr = maxYear; yr >= minYear; yr -= 1) {
    years.push(String(yr));
  }
  if (/^\d{4}$/.test(selectedYear) && !years.includes(selectedYear)) {
    years.push(selectedYear);
    years.sort((a, b) => Number(b) - Number(a));
  }
  return years;
}

function parseMonthYearParts(raw?: string | null): { month: string; year: string } | null {
  const cleaned = (raw || "").trim();
  if (!cleaned || /^(present|current|now)$/i.test(cleaned)) return null;

  const isoMatch = cleaned.match(/^(\d{4})-(\d{2})(?:-\d{2})?$/);
  if (isoMatch) {
    const monthNum = parseInt(isoMatch[2], 10);
    if (monthNum >= 1 && monthNum <= 12) {
      return { month: isoMatch[2], year: isoMatch[1] };
    }
  }

  const slashMatch = cleaned.match(/^(\d{1,2})\/(\d{4})$/);
  if (slashMatch) {
    const monthNum = parseInt(slashMatch[1], 10);
    if (monthNum >= 1 && monthNum <= 12) {
      return { month: slashMatch[1].padStart(2, "0"), year: slashMatch[2] };
    }
  }

  const monthYearMatch = cleaned.match(/^([A-Za-z]+)\.?\s+(\d{4})$/);
  if (monthYearMatch) {
    const mm = MONTH_INDEX[monthYearMatch[1].toLowerCase()];
    if (mm) return { month: mm, year: monthYearMatch[2] };
  }

  const yearMatch = cleaned.match(/^(\d{4})$/);
  if (yearMatch) {
    return { month: "", year: yearMatch[1] };
  }

  return null;
}

function formatDateForSave(raw?: string | null): string {
  const cleaned = (raw || "").trim();
  if (!cleaned) return "";
  if (/^(present|current|now)$/i.test(cleaned)) return "Present";
  const isoMatch = cleaned.match(/^(\d{4})-(\d{2})(?:-\d{2})?$/);
  if (isoMatch) {
    const monthIdx = parseInt(isoMatch[2], 10) - 1;
    const monthName = SHORT_MONTHS[monthIdx];
    if (monthName) return `${monthName} ${isoMatch[1]}`;
  }
  return cleaned;
}

function parseProfileDateScore(raw?: string | null): number {
  const cleaned = (raw || "").trim();
  if (!cleaned) return Number.NEGATIVE_INFINITY;
  if (/^(present|current|now)$/i.test(cleaned)) return Number.POSITIVE_INFINITY;
  const parts = parseMonthYearParts(cleaned);
  if (!parts) return Number.NEGATIVE_INFINITY;
  const monthIdx = parts.month ? parseInt(parts.month, 10) - 1 : 0;
  return Date.UTC(Number(parts.year), monthIdx, 1);
}

function compareScoresDesc(a: number, b: number): number {
  if (a === b) return 0;
  return b > a ? 1 : -1;
}

function sortWorkExperiencesDesc(items: any[]): any[] {
  return [...items].sort((a, b) => {
    const aStart = parseProfileDateScore(a?.start_date);
    const bStart = parseProfileDateScore(b?.start_date);
    const aPrimary = (a?.end_date || "").trim() ? parseProfileDateScore(a?.end_date) : aStart;
    const bPrimary = (b?.end_date || "").trim() ? parseProfileDateScore(b?.end_date) : bStart;
    return compareScoresDesc(aPrimary, bPrimary) || compareScoresDesc(aStart, bStart);
  });
}

function sortCertificationsDesc(items: any[]): any[] {
  return [...items].sort((a, b) =>
    compareScoresDesc(parseProfileDateScore(a?.date), parseProfileDateScore(b?.date))
  );
}

const ORDER_PREF_PREFIX = "cvbuilder_profile_manual_order_";

function readManualOrderPref(userId?: string | null): ManualOrderPrefs {
  if (!userId || typeof window === "undefined") return { ...DEFAULT_MANUAL_ORDER };
  try {
    const raw = window.localStorage.getItem(`${ORDER_PREF_PREFIX}${userId}`);
    if (!raw) return { ...DEFAULT_MANUAL_ORDER };
    const parsed = JSON.parse(raw);
    return {
      work_experiences: Boolean(parsed?.work_experiences),
      certifications: Boolean(parsed?.certifications),
    };
  } catch {
    return { ...DEFAULT_MANUAL_ORDER };
  }
}

function writeManualOrderPref(userId?: string | null, prefs?: ManualOrderPrefs) {
  if (!userId || !prefs || typeof window === "undefined") return;
  try {
    window.localStorage.setItem(
      `${ORDER_PREF_PREFIX}${userId}`,
      JSON.stringify({
        work_experiences: Boolean(prefs.work_experiences),
        certifications: Boolean(prefs.certifications),
      })
    );
  } catch {
    // Ignore storage quota or private-mode restrictions
  }
}

const MAX_RAW_COMMA_INPUT_LENGTH = 500;
const MAX_TAG_ITEMS = 50;
const MAX_TAG_LENGTH = 100;
const UNSAFE_INPUT_CHARS_RE = /[\u0000-\u001F\u007F\u202A-\u202E\u2066-\u2069]/g;

function stripUnsafeInputChars(raw: string): string {
  return raw.replace(/[\r\n\t]/g, " ").replace(UNSAFE_INPUT_CHARS_RE, "");
}

function normalizeTagList(items: string[]): string[] {
  const cleanedItems: string[] = [];
  const seen = new Set<string>();
  for (const rawItem of items) {
    if (typeof rawItem !== "string") continue;
    const cleaned = stripUnsafeInputChars(rawItem)
      .trim()
      .replace(/\s+/g, " ")
      .slice(0, MAX_TAG_LENGTH)
      .trim();
    if (!cleaned) continue;
    const key = cleaned.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    cleanedItems.push(cleaned);
    if (cleanedItems.length >= MAX_TAG_ITEMS) break;
  }
  return cleanedItems;
}

function parseTagList(raw: string): string[] {
  return normalizeTagList(raw.slice(0, MAX_RAW_COMMA_INPUT_LENGTH).split(","));
}

function tagListsEqual(a: string[], b: string[]): boolean {
  return a.length === b.length && a.every((item, idx) => item === b[idx]);
}

function toSafeHref(raw?: string | null): string | null {
  const cleaned = (raw || "").trim();
  if (!cleaned) return null;
  const lower = cleaned.toLowerCase();
  if (
    lower.startsWith("javascript:") ||
    lower.startsWith("data:") ||
    lower.startsWith("vbscript:") ||
    lower.startsWith("file:")
  ) {
    return null;
  }
  if (/^https?:\/\//i.test(cleaned)) return cleaned;
  if (/^[a-z0-9.-]+\.[a-z]{2,}/i.test(cleaned)) return `https://${cleaned}`;
  return null;
}

function deepClone(obj: any) {
  return JSON.parse(JSON.stringify(obj));
}

function formatLabel(key: string): string {
  const explicit: Record<string, string> = {
    linkedin_url: "LinkedIn URL",
    portfolio_url: "Portfolio URL",
    other_url: "Others Link",
  };
  if (explicit[key]) return explicit[key];
  return key
    .replace(/_/g, " ")
    .replace(/url/gi, "URL")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function getPlaceholder(key: string): string {
  const map: Record<string, string> = {
    name: "Alex Rivera",
    email: "alex@example.com",
    phone: "+1 (555) 234-5678",
    location: "San Francisco, CA",
    linkedin_url: "https://linkedin.com/in/...",
    portfolio_url: "https://yoursite.com",
    other_url: "https://github.com/... (GitHub, Kaggle, etc.)",
  };
  return map[key] || "";
}

export default function ProfilePage() {
  return (
    <Suspense
      fallback={
        <div className={styles.loadingState}>
          <div className={styles.spinner} />
          <p>Loading your base profile…</p>
        </div>
      }
    >
      <ProfilePageContent />
    </Suspense>
  );
}
