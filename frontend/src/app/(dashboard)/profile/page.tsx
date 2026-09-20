"use client";

import { useEffect, useState, useRef, DragEvent, ChangeEvent, useCallback } from "react";
import {
  UserCircle, Briefcase, GraduationCap, Settings, FileText,
  UploadCloud, Pencil, Save, X, Plus, Trash2, AlertCircle, CheckCircle,
  Award, FolderOpen, ExternalLink,
} from "lucide-react";
import { useSession } from "next-auth/react";
import { apiClient } from "@/lib/api";
import styles from "./page.module.css";
import { motion, AnimatePresence } from "framer-motion";

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

  // Upload state
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

  // ── Upload handlers ──────────────────────────────────────────
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
      setMessage({ type: "error", text: "File size exceeds the 10MB limit." });
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
      setMessage({ type: "success", text: "Resume parsed successfully! Switch to the Profile tab to review." });
      setActiveTab("profile");
    } catch (err: any) {
      setMessage({ type: "error", text: err.response?.data?.detail || "Failed to parse resume." });
    } finally {
      setIsUploading(false);
    }
  };

  // ── Manual save handler ──────────────────────────────────────
  const handleSave = async () => {
    setSaving(true);
    setMessage(null);
    try {
      const payload: any = {};
      if (formData.personal_info) payload.personal_info = formData.personal_info;
      if (formData.summary !== undefined) payload.summary = formData.summary;
      if (formData.work_experiences) payload.work_experiences = formData.work_experiences;
      if (formData.education) payload.education = formData.education;
      if (formData.skills) payload.skills = formData.skills;
      if (formData.certifications) payload.certifications = formData.certifications;
      if (formData.projects) payload.projects = formData.projects;

      const response = await apiClient.put("/profile/", payload, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setProfile(response.data);
      setFormData(deepClone(response.data));
      setEditing(false);
      setMessage({ type: "success", text: "Profile saved successfully!" });
      await update({ hasProfile: true });
    } catch (err: any) {
      setMessage({ type: "error", text: err.response?.data?.detail || "Failed to save profile." });
    } finally {
      setSaving(false);
    }
  };

  const startEditing = () => {
    if (!formData) {
      // Starting from scratch
      setFormData({
        personal_info: { name: "", email: "", phone: "", location: "", linkedin_url: "", portfolio_url: "" },
        summary: "",
        work_experiences: [],
        education: [],
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

  // ── Loading state ────────────────────────────────────────────
  if (loading || status === "loading") {
    return (
      <div className={styles.loadingState}>
        <div className={styles.spinner} />
        <p>Loading your profile...</p>
      </div>
    );
  }

  // ── Empty state (no profile yet) ─────────────────────────────
  if (!profile && !editing) {
    return (
      <div className={styles.container}>
        <header className={styles.header}>
          <div className={styles.headerLeft}>
            <h1 className={styles.title}>My Profile</h1>
            <p className={styles.subtitle}>Get started by importing your resume or filling in your details manually.</p>
          </div>
        </header>

        <div className={styles.emptyState}>
          <FileText size={64} style={{ opacity: 0.4 }} />
          <h2 style={{ fontSize: "1.5rem", fontWeight: 700, color: "#f8fafc" }}>No Profile Yet</h2>
          <p style={{ maxWidth: 500 }}>Choose how you'd like to set up your professional profile:</p>

          <div className={styles.emptyCards}>
            <motion.div
              className={styles.emptyCard}
              onClick={() => setActiveTab("import")}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              <div className={styles.emptyCardIcon}><UploadCloud size={32} /></div>
              <span className={styles.emptyCardTitle}>Import from PDF</span>
              <span className={styles.emptyCardDesc}>Upload your resume or LinkedIn export and let AI extract your data automatically.</span>
            </motion.div>

            <motion.div
              className={styles.emptyCard}
              onClick={startEditing}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
            >
              <div className={styles.emptyCardIcon}><Pencil size={32} /></div>
              <span className={styles.emptyCardTitle}>Fill Manually</span>
              <span className={styles.emptyCardDesc}>Enter your work experience, education, and skills by filling out a form.</span>
            </motion.div>
          </div>
        </div>

        {/* Show import dropzone if user clicked "Import from PDF" */}
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

  // ── Main profile view ────────────────────────────────────────
  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div className={styles.headerLeft}>
          <h1 className={styles.title}>My Profile</h1>
          <p className={styles.subtitle}>
            {editing ? "Edit your profile information below." : "This data powers your tailored CV generation."}
          </p>
        </div>
      </header>

      {/* Tab Bar */}
      <div className={styles.tabs}>
        <button
          className={`${styles.tab} ${activeTab === "profile" ? styles.tabActive : ""}`}
          onClick={() => setActiveTab("profile")}
        >
          <UserCircle size={16} /> Profile
        </button>
        <button
          className={`${styles.tab} ${activeTab === "import" ? styles.tabActive : ""}`}
          onClick={() => setActiveTab("import")}
        >
          <UploadCloud size={16} /> Import from PDF
        </button>
      </div>

      {/* Messages */}
      <AnimatePresence>
        {message && (
          <motion.div
            className={message.type === "success" ? styles.successMsg : styles.errorMsg}
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
          >
            {message.type === "success" ? <CheckCircle size={18} /> : <AlertCircle size={18} />}
            {message.text}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Profile Tab */}
      {activeTab === "profile" && (
        <>
          {/* Action buttons */}
          {!editing ? (
            <div className={styles.saveBar}>
              <button className={styles.editBtn} onClick={startEditing}>
                <Pencil size={14} /> Edit Profile
              </button>
            </div>
          ) : (
            <div className={styles.saveBar}>
              <button className={styles.cancelBtn} onClick={cancelEditing}>Cancel</button>
              <button className={styles.saveBtn} onClick={handleSave} disabled={saving}>
                <Save size={16} /> {saving ? "Saving..." : "Save Changes"}
              </button>
            </div>
          )}

          {/* Personal Info */}
          <motion.section className={styles.section} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
            <div className={styles.sectionHeader}>
              <h2 className={styles.sectionTitle}><UserCircle size={22} /> Personal Information</h2>
            </div>
            {editing ? (
              <div className={styles.grid}>
                {["name", "email", "phone", "location", "linkedin_url", "portfolio_url"].map((key) => (
                  <div key={key} className={styles.field}>
                    <label className={styles.fieldLabel}>{formatLabel(key)}</label>
                    <input
                      className={styles.input}
                      value={formData?.personal_info?.[key] || ""}
                      placeholder={getPlaceholder(key)}
                      onChange={(e) => updateField("personal_info", key, e.target.value)}
                    />
                  </div>
                ))}
              </div>
            ) : (
              <div className={styles.grid}>
                {["name", "email", "phone", "location", "linkedin_url", "portfolio_url"].map((key) => (
                  <div key={key} className={styles.field}>
                    <span className={styles.fieldLabel}>{formatLabel(key)}</span>
                    <div className={styles.fieldValue}>
                      {key.includes("url") && profile?.personal_info?.[key] ? (
                        <a href={profile.personal_info[key]} target="_blank" rel="noreferrer" style={{ color: "#818cf8" }}>
                          {profile.personal_info[key]}
                        </a>
                      ) : (
                        profile?.personal_info?.[key] || "N/A"
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </motion.section>

          {/* Summary */}
          <motion.section className={styles.section} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}>
            <div className={styles.sectionHeader}>
              <h2 className={styles.sectionTitle}><FileText size={22} /> Professional Summary</h2>
            </div>
            {editing ? (
              <textarea
                className={styles.textarea}
                value={formData?.summary || ""}
                placeholder="Write a compelling professional summary..."
                onChange={(e) => setFormData({ ...formData, summary: e.target.value })}
              />
            ) : (
              <div className={styles.fieldValue} style={{ lineHeight: 1.6 }}>
                {profile?.summary || "No summary provided."}
              </div>
            )}
          </motion.section>

          {/* Work Experience */}
          <motion.section className={styles.section} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
            <div className={styles.sectionHeader}>
              <h2 className={styles.sectionTitle}><Briefcase size={22} /> Work Experience</h2>
            </div>
            {editing ? (
              <>
                {(formData?.work_experiences || []).map((exp: any, idx: number) => (
                  <div key={idx} className={styles.listItemEdit}>
                    <div className={styles.listItemEditHeader}>
                      <span className={styles.listItemEditTitle}>Experience #{idx + 1}</span>
                      <button className={styles.removeBtn} onClick={() => removeListItem("work_experiences", idx)}>
                        <Trash2 size={14} />
                      </button>
                    </div>
                    <div className={styles.inlineRow}>
                      <input className={styles.input} placeholder="Job Title" value={exp.title || ""} onChange={(e) => updateListItem("work_experiences", idx, "title", e.target.value)} />
                      <input className={styles.input} placeholder="Company" value={exp.company || ""} onChange={(e) => updateListItem("work_experiences", idx, "company", e.target.value)} />
                    </div>
                    <div className={styles.inlineRow}>
                      <input className={styles.input} placeholder="Start Date (e.g. Jan 2022)" value={exp.start_date || ""} onChange={(e) => updateListItem("work_experiences", idx, "start_date", e.target.value)} />
                      <input className={styles.input} placeholder="End Date or Present" value={exp.end_date || ""} onChange={(e) => updateListItem("work_experiences", idx, "end_date", e.target.value)} />
                    </div>
                    <textarea
                      className={styles.textarea}
                      placeholder="Key achievements (one per line)"
                      value={(exp.bullets || []).join("\n")}
                      onChange={(e) => updateListItem("work_experiences", idx, "bullets", e.target.value.split("\n"))}
                    />
                  </div>
                ))}
                <button className={styles.addBtn} onClick={() => addListItem("work_experiences", { title: "", company: "", start_date: "", end_date: "", location: "", bullets: [] })}>
                  <Plus size={16} /> Add Experience
                </button>
              </>
            ) : (
              <>
                {(profile?.work_experiences || []).length > 0 ? (
                  profile.work_experiences.map((exp: any, idx: number) => (
                    <div key={idx} className={styles.listItem}>
                      <div className={styles.listItemHeader}>
                        <div>
                          <div className={styles.itemTitle}>{exp.title}</div>
                          <div className={styles.itemSubtitle}>{exp.company}</div>
                        </div>
                        <div className={styles.itemDate}>{exp.start_date || ""} - {exp.end_date || "Present"}</div>
                      </div>
                      {exp.bullets?.length > 0 && (
                        <ul className={styles.bulletList}>
                          {exp.bullets.map((b: string, bIdx: number) => <li key={bIdx}>{b}</li>)}
                        </ul>
                      )}
                    </div>
                  ))
                ) : (
                  <p style={{ color: "#94a3b8" }}>No work experience added yet.</p>
                )}
              </>
            )}
          </motion.section>

          {/* Education */}
          <motion.section className={styles.section} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
            <div className={styles.sectionHeader}>
              <h2 className={styles.sectionTitle}><GraduationCap size={22} /> Education</h2>
            </div>
            {editing ? (
              <>
                {(formData?.education || []).map((edu: any, idx: number) => (
                  <div key={idx} className={styles.listItemEdit}>
                    <div className={styles.listItemEditHeader}>
                      <span className={styles.listItemEditTitle}>Education #{idx + 1}</span>
                      <button className={styles.removeBtn} onClick={() => removeListItem("education", idx)}>
                        <Trash2 size={14} />
                      </button>
                    </div>
                    <input className={styles.input} placeholder="Institution" value={edu.institution || ""} onChange={(e) => updateListItem("education", idx, "institution", e.target.value)} />
                    <div className={styles.inlineRow}>
                      <input className={styles.input} placeholder="Degree (e.g. Bachelor of Science)" value={edu.degree || ""} onChange={(e) => updateListItem("education", idx, "degree", e.target.value)} />
                      <input className={styles.input} placeholder="Field of Study" value={edu.field || ""} onChange={(e) => updateListItem("education", idx, "field", e.target.value)} />
                    </div>
                    <div className={styles.inlineRow}>
                      <input className={styles.input} placeholder="Start Date" value={edu.start_date || ""} onChange={(e) => updateListItem("education", idx, "start_date", e.target.value)} />
                      <input className={styles.input} placeholder="End Date" value={edu.end_date || ""} onChange={(e) => updateListItem("education", idx, "end_date", e.target.value)} />
                    </div>
                    <input className={styles.input} placeholder="GPA (e.g. 3.8/4.0)" value={edu.gpa || ""} onChange={(e) => updateListItem("education", idx, "gpa", e.target.value)} />
                    <input className={styles.input} placeholder="Relevant coursework (comma-separated)" value={(edu.relevant_coursework || []).join(", ")} onChange={(e) => updateListItem("education", idx, "relevant_coursework", e.target.value.split(",").map((c: string) => c.trim()).filter(Boolean))} />
                  </div>
                ))}
                <button className={styles.addBtn} onClick={() => addListItem("education", { institution: "", degree: "", field: "", start_date: "", end_date: "", gpa: "", relevant_coursework: [] })}>
                  <Plus size={16} /> Add Education
                </button>
              </>
            ) : (
              <>
                {(profile?.education || []).length > 0 ? (
                  profile.education.map((edu: any, idx: number) => (
                    <div key={idx} className={styles.listItem}>
                      <div className={styles.listItemHeader}>
                        <div>
                          <div className={styles.itemTitle}>{edu.institution}</div>
                          <div className={styles.itemSubtitle}>{edu.degree} {edu.field ? `in ${edu.field}` : ""}</div>
                        </div>
                        <div className={styles.itemDate}>{edu.start_date ? `${edu.start_date} - ` : ""}{edu.end_date || ""}</div>
                      </div>
                      {edu.gpa && <div style={{ color: "#94a3b8", fontSize: "0.875rem", marginTop: "0.25rem" }}>GPA: {edu.gpa}</div>}
                      {edu.relevant_coursework?.length > 0 && (
                        <div style={{ marginTop: "0.5rem" }}>
                          <span className={styles.fieldLabel} style={{ marginBottom: "0.25rem" }}>Relevant Coursework</span>
                          <div className={styles.tagList}>
                            {edu.relevant_coursework.map((c: string, cIdx: number) => (
                              <span key={cIdx} className={styles.tag}>{c}</span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  ))
                ) : (
                  <p style={{ color: "#94a3b8" }}>No education added yet.</p>
                )}
              </>
            )}
          </motion.section>

          {/* Skills */}
          <motion.section className={styles.section} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
            <div className={styles.sectionHeader}>
              <h2 className={styles.sectionTitle}><Settings size={22} /> Skills</h2>
            </div>
            {editing ? (
              <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
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
              <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
                {["technical", "soft", "tools", "languages"].map((category) => {
                  const items = profile?.skills?.[category] || [];
                  if (items.length === 0) return null;
                  return (
                    <div key={category}>
                      <span className={styles.fieldLabel}>{formatLabel(category)}</span>
                      <div className={styles.tagList}>
                        {items.map((s: string, i: number) => (
                          <span key={i} className={styles.tag}>{s}</span>
                        ))}
                      </div>
                    </div>
                  );
                })}
                {!profile?.skills && <p style={{ color: "#94a3b8" }}>No skills added yet.</p>}
              </div>
            )}
          </motion.section>

          {/* Certifications */}
          <motion.section className={styles.section} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }}>
            <div className={styles.sectionHeader}>
              <h2 className={styles.sectionTitle}><Award size={22} /> Certifications</h2>
            </div>
            {editing ? (
              <>
                {(formData?.certifications || []).map((cert: any, idx: number) => (
                  <div key={idx} className={styles.listItemEdit}>
                    <div className={styles.listItemEditHeader}>
                      <span className={styles.listItemEditTitle}>Certification #{idx + 1}</span>
                      <button className={styles.removeBtn} onClick={() => removeListItem("certifications", idx)}>
                        <Trash2 size={14} />
                      </button>
                    </div>
                    <input className={styles.input} placeholder="Certification Name" value={cert.name || ""} onChange={(e) => updateListItem("certifications", idx, "name", e.target.value)} />
                    <div className={styles.inlineRow}>
                      <input className={styles.input} placeholder="Issuing Organization" value={cert.issuer || ""} onChange={(e) => updateListItem("certifications", idx, "issuer", e.target.value)} />
                      <input className={styles.input} placeholder="Date Obtained" value={cert.date || ""} onChange={(e) => updateListItem("certifications", idx, "date", e.target.value)} />
                    </div>
                    <input className={styles.input} placeholder="Credential ID (optional)" value={cert.credential_id || ""} onChange={(e) => updateListItem("certifications", idx, "credential_id", e.target.value)} />
                  </div>
                ))}
                <button className={styles.addBtn} onClick={() => addListItem("certifications", { name: "", issuer: "", date: "", credential_id: "" })}>
                  <Plus size={16} /> Add Certification
                </button>
              </>
            ) : (
              <>
                {(profile?.certifications || []).length > 0 ? (
                  profile.certifications.map((cert: any, idx: number) => (
                    <div key={idx} className={styles.listItem}>
                      <div className={styles.listItemHeader}>
                        <div>
                          <div className={styles.itemTitle}>{cert.name}</div>
                          <div className={styles.itemSubtitle}>{cert.issuer || ""}</div>
                        </div>
                        <div className={styles.itemDate}>{cert.date || ""}</div>
                      </div>
                      {cert.credential_id && <div style={{ color: "#64748b", fontSize: "0.8rem", marginTop: "0.25rem" }}>ID: {cert.credential_id}</div>}
                    </div>
                  ))
                ) : (
                  <p style={{ color: "#94a3b8" }}>No certifications added yet.</p>
                )}
              </>
            )}
          </motion.section>

          {/* Projects */}
          <motion.section className={styles.section} initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
            <div className={styles.sectionHeader}>
              <h2 className={styles.sectionTitle}><FolderOpen size={22} /> Projects</h2>
            </div>
            {editing ? (
              <>
                {(formData?.projects || []).map((proj: any, idx: number) => (
                  <div key={idx} className={styles.listItemEdit}>
                    <div className={styles.listItemEditHeader}>
                      <span className={styles.listItemEditTitle}>Project #{idx + 1}</span>
                      <button className={styles.removeBtn} onClick={() => removeListItem("projects", idx)}>
                        <Trash2 size={14} />
                      </button>
                    </div>
                    <input className={styles.input} placeholder="Project Name" value={proj.name || ""} onChange={(e) => updateListItem("projects", idx, "name", e.target.value)} />
                    <textarea
                      className={styles.textarea}
                      placeholder="Brief description of the project..."
                      style={{ minHeight: "70px" }}
                      value={proj.description || ""}
                      onChange={(e) => updateListItem("projects", idx, "description", e.target.value)}
                    />
                    <input className={styles.input} placeholder="Technologies (comma-separated)" value={(proj.technologies || []).join(", ")} onChange={(e) => updateListItem("projects", idx, "technologies", e.target.value.split(",").map((t: string) => t.trim()).filter(Boolean))} />
                    <input className={styles.input} placeholder="Project URL (optional)" value={proj.url || ""} onChange={(e) => updateListItem("projects", idx, "url", e.target.value)} />
                  </div>
                ))}
                <button className={styles.addBtn} onClick={() => addListItem("projects", { name: "", description: "", technologies: [], url: "" })}>
                  <Plus size={16} /> Add Project
                </button>
              </>
            ) : (
              <>
                {(profile?.projects || []).length > 0 ? (
                  profile.projects.map((proj: any, idx: number) => (
                    <div key={idx} className={styles.listItem}>
                      <div className={styles.listItemHeader}>
                        <div>
                          <div className={styles.itemTitle}>{proj.name}</div>
                          {proj.url && (
                            <a href={proj.url} target="_blank" rel="noreferrer" style={{ color: "#818cf8", fontSize: "0.85rem", display: "flex", alignItems: "center", gap: "0.25rem" }}>
                              <ExternalLink size={12} /> {proj.url}
                            </a>
                          )}
                        </div>
                      </div>
                      {proj.description && <p style={{ color: "#cbd5e1", fontSize: "0.95rem", marginTop: "0.5rem", lineHeight: 1.5 }}>{proj.description}</p>}
                      {proj.technologies?.length > 0 && (
                        <div className={styles.tagList} style={{ marginTop: "0.5rem" }}>
                          {proj.technologies.map((t: string, tIdx: number) => (
                            <span key={tIdx} className={styles.tag}>{t}</span>
                          ))}
                        </div>
                      )}
                    </div>
                  ))
                ) : (
                  <p style={{ color: "#94a3b8" }}>No projects added yet.</p>
                )}
              </>
            )}
          </motion.section>

          {/* Bottom save bar (when editing) */}
          {editing && (
            <div className={styles.saveBar}>
              <button className={styles.cancelBtn} onClick={cancelEditing}>Cancel</button>
              <button className={styles.saveBtn} onClick={handleSave} disabled={saving}>
                <Save size={16} /> {saving ? "Saving..." : "Save Changes"}
              </button>
            </div>
          )}
        </>
      )}

      {/* Import Tab */}
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

  // ── Helper functions ─────────────────────────────────────────
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

// ── Sub-components ───────────────────────────────────────────────

function ImportTab({
  isDragging, isUploading, fileInputRef, message,
  onDragOver, onDragLeave, onDrop, onFileSelect,
}: any) {
  return (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
      <div
        className={`${styles.dropzone} ${isDragging ? styles.dropzoneActive : ""}`}
        onDragOver={onDragOver}
        onDragLeave={onDragLeave}
        onDrop={onDrop}
        onClick={() => fileInputRef.current?.click()}
      >
        <AnimatePresence>
          {isUploading && (
            <motion.div className={styles.loadingOverlay} initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
              <div className={styles.loadingSpinner} />
              <p className={styles.loadingText}>Extracting and parsing your profile with AI...</p>
            </motion.div>
          )}
        </AnimatePresence>
        <UploadCloud size={64} className={styles.uploadIcon} />
        <h3 className={styles.dropzoneText}>Drag & drop your PDF here</h3>
        <p className={styles.dropzoneSubtext}>Upload your resume or LinkedIn PDF export • Maximum 10MB</p>
        <input type="file" ref={fileInputRef} onChange={onFileSelect} accept="application/pdf" className={styles.fileInput} />
        <button className={styles.browseBtn} type="button">Browse Files</button>
      </div>

      {message && (
        <motion.div className={message.type === "success" ? styles.successMsg : styles.errorMsg} initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} style={{ marginTop: "1rem" }}>
          {message.type === "success" ? <CheckCircle size={18} /> : <AlertCircle size={18} />}
          {message.text}
        </motion.div>
      )}
    </motion.div>
  );
}

function SkillTagEditor({ label, tags, onChange }: { label: string; tags: string[]; onChange: (tags: string[]) => void }) {
  const [input, setInput] = useState("");

  const addTag = () => {
    const trimmed = input.trim();
    if (trimmed && !tags.includes(trimmed)) {
      onChange([...tags, trimmed]);
      setInput("");
    }
  };

  return (
    <div>
      <span className={styles.fieldLabel}>{label}</span>
      <div className={styles.tagList} style={{ marginBottom: "0.5rem" }}>
        {tags.map((tag, i) => (
          <span key={i} className={styles.tag}>
            {tag}
            <button className={styles.tagRemove} onClick={() => onChange(tags.filter((_, j) => j !== i))}>×</button>
          </span>
        ))}
      </div>
      <div className={styles.tagInput}>
        <input
          className={styles.input}
          value={input}
          placeholder={`Add a ${label.toLowerCase()} skill...`}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addTag(); } }}
        />
        <button className={styles.tagAddBtn} onClick={addTag} type="button"><Plus size={18} /></button>
      </div>
    </div>
  );
}

// ── Utilities ────────────────────────────────────────────────────

function deepClone(obj: any) {
  return JSON.parse(JSON.stringify(obj));
}

function formatLabel(key: string): string {
  return key.replace(/_/g, " ").replace(/url/gi, "URL").replace(/\b\w/g, (c) => c.toUpperCase());
}

function getPlaceholder(key: string): string {
  const map: Record<string, string> = {
    name: "John Doe",
    email: "john@example.com",
    phone: "+1 234 567 890",
    location: "San Francisco, CA",
    linkedin_url: "https://linkedin.com/in/...",
    portfolio_url: "https://yoursite.com",
  };
  return map[key] || "";
}
