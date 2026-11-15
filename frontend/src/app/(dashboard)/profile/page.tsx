"use client";

import { useEffect, useState, useRef, DragEvent, ChangeEvent, useCallback } from "react";
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
  AlertCircle,
  CheckCircle,
  Award,
  FolderOpen,
  ExternalLink,
  Users,
} from "lucide-react";
import { useSession } from "next-auth/react";
import { apiClient } from "@/lib/api";
import styles from "./page.module.css";

type TabId = "profile" | "import";

export default function ProfilePage() {
  const { data: session, status, update } = useSession();
  const [profile, setProfile] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<TabId>("profile");
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [formData, setFormData] = useState<any>(null);
  const [message, setMessage] = useState<{ type: "success" | "error"; text: string } | null>(null);

  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const token = (session as any)?.backendAccessToken;

  const fetchProfile = useCallback(async () => {
    if (status !== "authenticated") return;
    try {
      const response = await apiClient.get("/profile/", {
        headers: { Authorization: `Bearer ${token}` },
      });
      setProfile(response.data);
      setFormData(deepClone(response.data));
    } catch (err: any) {
      if (err.response?.status === 404) {
        setProfile(null);
      }
    } finally {
      setLoading(false);
    }
  }, [status, token]);

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
      await apiClient.post("/resume/upload", fd, {
        headers: { "Content-Type": "multipart/form-data", Authorization: `Bearer ${token}` },
      });
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
        payload.work_experiences = formData.work_experiences.map((exp: any) => ({
          ...exp,
          start_date: formatDateForSave(exp.start_date),
          end_date: formatDateForSave(exp.end_date),
        }));
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
        payload.certifications = formData.certifications.map((cert: any) => ({
          ...cert,
          date: formatDateForSave(cert.date),
        }));
      }
      if (formData.projects) payload.projects = formData.projects;

      const response = await apiClient.put("/profile/", payload, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setProfile(response.data);
      setFormData(deepClone(response.data));
      setEditing(false);
      setMessage({ type: "success", text: "Profile changes saved." });
      await update({ hasProfile: true });
    } catch (err: any) {
      setMessage({ type: "error", text: err.response?.data?.detail || "Failed to save profile." });
    } finally {
      setSaving(false);
    }
  };

  const startEditing = () => {
    if (!formData) {
      setFormData({
        personal_info: {
          name: "",
          email: "",
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
            <h1 className={styles.title}>Base Career Profile</h1>
            <p className={styles.subtitle}>
              Import an existing PDF resume or enter your work history manually.
            </p>
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
              <button className={styles.editBtn} onClick={startEditing}>
                <Pencil size={15} strokeWidth={1.75} />
                <span>Edit Profile</span>
              </button>
            ) : (
              <>
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
            </div>
            {editing ? (
              <div className={styles.itemsStack}>
                {(formData?.work_experiences || []).map((exp: any, idx: number) => (
                  <div key={idx} className={styles.listItemEdit}>
                    <div className={styles.listItemEditHeader}>
                      <span className={styles.listItemEditTitle}>
                        {exp.title || exp.company
                          ? `${exp.title || "Role"}${exp.company ? ` · ${exp.company}` : ""}`
                          : "Position Details"}
                      </span>
                      <button
                        type="button"
                        className={styles.removeBtn}
                        onClick={() => removeListItem("work_experiences", idx)}
                        title="Remove position"
                      >
                        <Trash2 size={15} strokeWidth={1.75} />
                      </button>
                    </div>
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
                      <CalendarDateInput
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
                      placeholder="Key achievements and impact (one bullet per line)"
                      value={(exp.bullets || []).join("\n")}
                      onChange={(e) =>
                        updateListItem("work_experiences", idx, "bullets", e.target.value.split("\n"))
                      }
                    />
                  </div>
                ))}
                <button
                  type="button"
                  className={styles.addBtn}
                  onClick={() =>
                    addListItem("work_experiences", {
                      title: "",
                      company: "",
                      start_date: "",
                      end_date: "",
                      location: "",
                      bullets: [],
                    })
                  }
                >
                  <Plus size={16} strokeWidth={2} />
                  <span>Add Work Experience</span>
                </button>
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
                      <CalendarDateInput
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
                    <input
                      className={styles.input}
                      placeholder="Relevant coursework (comma-separated)"
                      value={(edu.relevant_coursework || []).join(", ")}
                      onChange={(e) =>
                        updateListItem(
                          "education",
                          idx,
                          "relevant_coursework",
                          e.target.value
                            .split(",")
                            .map((c: string) => c.trim())
                            .filter(Boolean)
                        )
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
                      <CalendarDateInput
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
                      placeholder="Key contributions and impact (one bullet per line)"
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
            </div>
            {editing ? (
              <div className={styles.itemsStack}>
                {(formData?.certifications || []).map((cert: any, idx: number) => (
                  <div key={idx} className={styles.listItemEdit}>
                    <div className={styles.listItemEditHeader}>
                      <span className={styles.listItemEditTitle}>
                        {cert.name || "Certification"}
                      </span>
                      <button
                        type="button"
                        className={styles.removeBtn}
                        onClick={() => removeListItem("certifications", idx)}
                      >
                        <Trash2 size={15} strokeWidth={1.75} />
                      </button>
                    </div>
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
                      <CalendarDateInput
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
                  </div>
                ))}
                <button
                  type="button"
                  className={styles.addBtn}
                  onClick={() =>
                    addListItem("certifications", {
                      name: "",
                      issuer: "",
                      date: "",
                      credential_id: "",
                      url: "",
                    })
                  }
                >
                  <Plus size={16} strokeWidth={2} />
                  <span>Add Certification</span>
                </button>
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
                {(formData?.projects || []).map((proj: any, idx: number) => (
                  <div key={idx} className={styles.listItemEdit}>
                    <div className={styles.listItemEditHeader}>
                      <span className={styles.listItemEditTitle}>
                        {proj.name || "Project"}
                      </span>
                      <button
                        type="button"
                        className={styles.removeBtn}
                        onClick={() => removeListItem("projects", idx)}
                      >
                        <Trash2 size={15} strokeWidth={1.75} />
                      </button>
                    </div>
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
                    <input
                      className={styles.input}
                      placeholder="Technologies (comma-separated)"
                      value={(proj.technologies || []).join(", ")}
                      onChange={(e) =>
                        updateListItem(
                          "projects",
                          idx,
                          "technologies",
                          e.target.value
                            .split(",")
                            .map((t: string) => t.trim())
                            .filter(Boolean)
                        )
                      }
                    />
                    <input
                      className={styles.input}
                      placeholder="Project URL (optional)"
                      value={proj.url || ""}
                      onChange={(e) => updateListItem("projects", idx, "url", e.target.value)}
                    />
                  </div>
                ))}
                <button
                  type="button"
                  className={styles.addBtn}
                  onClick={() =>
                    addListItem("projects", {
                      name: "",
                      description: "",
                      technologies: [],
                      url: "",
                    })
                  }
                >
                  <Plus size={16} strokeWidth={2} />
                  <span>Add Project</span>
                </button>
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

  function addListItem(section: string, template: any) {
    setFormData({
      ...formData,
      [section]: [...(formData?.[section] || []), template],
    });
  }

  function removeListItem(section: string, idx: number) {
    const items = [...(formData?.[section] || [])];
    items.splice(idx, 1);
    setFormData({ ...formData, [section]: items });
  }
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

  const addTag = () => {
    const trimmed = input.trim();
    if (trimmed && !tags.includes(trimmed)) {
      onChange([...tags, trimmed]);
      setInput("");
    }
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
          placeholder={`Add ${label.toLowerCase()} skill and press Enter…`}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              addTag();
            }
          }}
        />
        <button className={styles.tagAddBtn} onClick={addTag} type="button" aria-label="Add skill">
          <Plus size={16} strokeWidth={2} />
        </button>
      </div>
    </div>
  );
}

function CalendarDateInput({
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
  const inputValue = disabled ? "" : toDateInputValue(value);
  return (
    <div className={styles.field}>
      <label className={styles.fieldLabel}>{label}</label>
      <input
        type="date"
        className={styles.dateInput}
        value={inputValue}
        disabled={disabled}
        onClick={(e) => {
          if (disabled) return;
          try {
            e.currentTarget.showPicker?.();
          } catch {
            // Fallback gracefully on browsers that block programmatic picker opening
          }
        }}
        onKeyDown={(e) => {
          if (e.key === "Tab" || e.key === "Shift" || e.key === "Escape") return;
          if (e.key === "Backspace" || e.key === "Delete") {
            onChange("");
          }
          e.preventDefault();
        }}
        onChange={(e) => onChange(e.target.value)}
      />
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
      <CalendarDateInput
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

function toDateInputValue(raw?: string | null): string {
  const cleaned = (raw || "").trim();
  if (!cleaned || /^(present|current|now)$/i.test(cleaned)) return "";
  if (/^\d{4}-\d{2}-\d{2}$/.test(cleaned)) return cleaned;
  if (/^\d{4}-\d{2}$/.test(cleaned)) return `${cleaned}-01`;

  const slashMatch = cleaned.match(/^(\d{1,2})\/(\d{4})$/);
  if (slashMatch) {
    return `${slashMatch[2]}-${slashMatch[1].padStart(2, "0")}-01`;
  }

  const monthYearMatch = cleaned.match(/^([A-Za-z]+)\.?\s+(\d{4})$/);
  if (monthYearMatch) {
    const mm = MONTH_INDEX[monthYearMatch[1].toLowerCase()];
    if (mm) return `${monthYearMatch[2]}-${mm}-01`;
  }

  const yearMatch = cleaned.match(/^(\d{4})$/);
  if (yearMatch) return `${yearMatch[1]}-01-01`;

  return "";
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
