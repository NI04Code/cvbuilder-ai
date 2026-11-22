"use client";

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSession } from "next-auth/react";
import {
  AlertCircle,
  Briefcase,
  Calendar,
  Columns3,
  ExternalLink,
  List,
  MapPin,
  Pencil,
  Plus,
  Search,
  Trash2,
  User,
  Wallet,
  X,
} from "lucide-react";
import { apiClient } from "@/lib/api";
import styles from "./page.module.css";

type ApplicationStatus =
  | "saved"
  | "applied"
  | "interviewing"
  | "offer"
  | "rejected"
  | "withdrawn";

type WorkMode = "remote" | "hybrid" | "onsite";
type ViewMode = "list" | "board";

interface JobApplicationItem {
  id: string;
  company_name: string;
  role_title: string;
  job_url: string | null;
  status: ApplicationStatus;
  applied_date: string | null;
  work_mode: WorkMode | null;
  location: string | null;
  salary_range: string | null;
  recruiter_name: string | null;
  recruiter_contact: string | null;
  next_follow_up_date: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

interface ApplicationStats {
  total: number;
  saved: number;
  applied: number;
  interviewing: number;
  offer: number;
  rejected: number;
  withdrawn: number;
}

interface ApplicationFormState {
  company_name: string;
  role_title: string;
  job_url: string;
  status: ApplicationStatus;
  applied_date: string;
  work_mode: "" | WorkMode;
  location: string;
  salary_range: string;
  recruiter_name: string;
  recruiter_contact: string;
  next_follow_up_date: string;
  notes: string;
}

const STATUS_OPTIONS: Array<{ value: ApplicationStatus; label: string }> = [
  { value: "saved", label: "Saved" },
  { value: "applied", label: "Applied" },
  { value: "interviewing", label: "Interviewing" },
  { value: "offer", label: "Offer" },
  { value: "rejected", label: "Rejected" },
  { value: "withdrawn", label: "Withdrawn" },
];

const WORK_MODE_LABELS: Record<WorkMode, string> = {
  remote: "Remote",
  hybrid: "Hybrid",
  onsite: "On-site",
};

const EMPTY_STATS: ApplicationStats = {
  total: 0,
  saved: 0,
  applied: 0,
  interviewing: 0,
  offer: 0,
  rejected: 0,
  withdrawn: 0,
};

function todayIsoDate(): string {
  return new Date().toISOString().slice(0, 10);
}

function emptyFormState(): ApplicationFormState {
  return {
    company_name: "",
    role_title: "",
    job_url: "",
    status: "saved",
    applied_date: "",
    work_mode: "",
    location: "",
    salary_range: "",
    recruiter_name: "",
    recruiter_contact: "",
    next_follow_up_date: "",
    notes: "",
  };
}

function toFormState(item: JobApplicationItem): ApplicationFormState {
  return {
    company_name: item.company_name,
    role_title: item.role_title,
    job_url: item.job_url ?? "",
    status: item.status,
    applied_date: item.applied_date ?? "",
    work_mode: item.work_mode ?? "",
    location: item.location ?? "",
    salary_range: item.salary_range ?? "",
    recruiter_name: item.recruiter_name ?? "",
    recruiter_contact: item.recruiter_contact ?? "",
    next_follow_up_date: item.next_follow_up_date ?? "",
    notes: item.notes ?? "",
  };
}

function formatDateLabel(dateStr: string): string {
  const parsed = new Date(`${dateStr}T00:00:00`);
  if (Number.isNaN(parsed.getTime())) return dateStr;
  return parsed.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

function isSafeHttpUrl(url: string | null): url is string {
  return Boolean(url && (url.startsWith("https://") || url.startsWith("http://")));
}

function isFollowUpDue(item: JobApplicationItem): boolean {
  if (!item.next_follow_up_date) return false;
  if (item.status === "rejected" || item.status === "withdrawn" || item.status === "offer") {
    return false;
  }
  return item.next_follow_up_date <= todayIsoDate();
}

export default function TrackerPage() {
  const { data: session, status: sessionStatus } = useSession();
  const [applications, setApplications] = useState<JobApplicationItem[]>([]);
  const [stats, setStats] = useState<ApplicationStats>(EMPTY_STATS);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<"all" | ApplicationStatus>("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [viewMode, setViewMode] = useState<ViewMode>("list");
  const [pageError, setPageError] = useState<string | null>(null);

  const [editingItem, setEditingItem] = useState<JobApplicationItem | null>(null);
  const [form, setForm] = useState<ApplicationFormState>(emptyFormState);
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const [updatingStatusId, setUpdatingStatusId] = useState<string | null>(null);

  const dialogRef = useRef<HTMLDialogElement>(null);
  const token = (session as { backendAccessToken?: string } | null)?.backendAccessToken;

  useEffect(() => {
    if (sessionStatus !== "authenticated" || !token) return;
    let cancelled = false;

    async function loadTrackerData() {
      try {
        const headers = { Authorization: `Bearer ${token}` };
        const [listRes, statsRes] = await Promise.all([
          apiClient.get<JobApplicationItem[]>("/job-applications", {
            params: { limit: 100, offset: 0 },
            headers,
          }),
          apiClient.get<ApplicationStats>("/job-applications/stats", { headers }),
        ]);
        if (cancelled) return;
        setApplications(listRes.data);
        setStats(statsRes.data);
        setPageError(null);
      } catch (err) {
        if (cancelled) return;
        console.error("Failed to load applications", err);
        setPageError("Failed to load your tracked applications. Please refresh and try again.");
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    }

    loadTrackerData();
    return () => {
      cancelled = true;
    };
  }, [sessionStatus, token]);

  const refreshStats = useCallback(async () => {
    if (!token) return;
    try {
      const res = await apiClient.get<ApplicationStats>("/job-applications/stats", {
        headers: { Authorization: `Bearer ${token}` },
      });
      setStats(res.data);
    } catch {
      // Keep existing stats on transient background failure
    }
  }, [token]);

  const openCreateModal = () => {
    setEditingItem(null);
    setForm(emptyFormState());
    setFormError(null);
    dialogRef.current?.showModal();
  };

  const openEditModal = (item: JobApplicationItem) => {
    setEditingItem(item);
    setForm(toFormState(item));
    setFormError(null);
    dialogRef.current?.showModal();
  };

  const closeModal = () => {
    dialogRef.current?.close();
  };

  const handleStatusFieldChange = (nextStatus: ApplicationStatus) => {
    setForm((prev) => ({
      ...prev,
      status: nextStatus,
      applied_date:
        nextStatus === "applied" && !prev.applied_date ? todayIsoDate() : prev.applied_date,
    }));
  };

  const handleSaveApplication = async (e: FormEvent) => {
    e.preventDefault();
    if (!token || submitting) return;

    const trimmedCompany = form.company_name.trim();
    const trimmedRole = form.role_title.trim();
    if (!trimmedCompany || !trimmedRole) {
      setFormError("Company and role are required.");
      return;
    }

    setFormError(null);
    setSubmitting(true);

    const payload = {
      company_name: trimmedCompany,
      role_title: trimmedRole,
      job_url: form.job_url.trim() || null,
      status: form.status,
      applied_date: form.applied_date || null,
      work_mode: form.work_mode || null,
      location: form.location.trim() || null,
      salary_range: form.salary_range.trim() || null,
      recruiter_name: form.recruiter_name.trim() || null,
      recruiter_contact: form.recruiter_contact.trim() || null,
      next_follow_up_date: form.next_follow_up_date || null,
      notes: form.notes.trim() || null,
    };

    try {
      const headers = { Authorization: `Bearer ${token}` };
      if (editingItem) {
        const res = await apiClient.patch<JobApplicationItem>(
          `/job-applications/${editingItem.id}`,
          payload,
          { headers }
        );
        setApplications((prev) =>
          prev.map((item) => (item.id === editingItem.id ? res.data : item))
        );
      } else {
        const res = await apiClient.post<JobApplicationItem>("/job-applications", payload, {
          headers,
        });
        setApplications((prev) => [res.data, ...prev]);
      }
      await refreshStats();
      closeModal();
    } catch (err: unknown) {
      const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data
        ?.detail;
      setFormError(
        typeof detail === "string" ? detail : "Unable to save application. Check your inputs."
      );
    } finally {
      setSubmitting(false);
    }
  };

  const handleInlineStatusChange = async (
    item: JobApplicationItem,
    nextStatus: ApplicationStatus
  ) => {
    if (!token || item.status === nextStatus || updatingStatusId) return;
    setUpdatingStatusId(item.id);
    setPageError(null);

    const patchBody: { status: ApplicationStatus; applied_date?: string } = {
      status: nextStatus,
    };
    if (nextStatus === "applied" && !item.applied_date) {
      patchBody.applied_date = todayIsoDate();
    }

    try {
      const res = await apiClient.patch<JobApplicationItem>(
        `/job-applications/${item.id}`,
        patchBody,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setApplications((prev) => prev.map((row) => (row.id === item.id ? res.data : row)));
      await refreshStats();
    } catch {
      setPageError("Could not update application status. Please try again.");
    } finally {
      setUpdatingStatusId(null);
    }
  };

  const handleDelete = async (id: string) => {
    if (!token || deletingId) return;
    setDeletingId(id);
    setPageError(null);
    try {
      await apiClient.delete(`/job-applications/${id}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      setApplications((prev) => prev.filter((item) => item.id !== id));
      setConfirmDeleteId(null);
      await refreshStats();
    } catch {
      setPageError("Failed to delete application. Please try again.");
    } finally {
      setDeletingId(null);
    }
  };

  const filteredApplications = useMemo(() => {
    const query = searchQuery.trim().toLowerCase();
    return applications.filter((item) => {
      if (statusFilter !== "all" && item.status !== statusFilter) {
        return false;
      }
      if (!query) return true;
      return (
        item.company_name.toLowerCase().includes(query) ||
        item.role_title.toLowerCase().includes(query) ||
        (item.location ?? "").toLowerCase().includes(query) ||
        (item.notes ?? "").toLowerCase().includes(query)
      );
    });
  }, [applications, statusFilter, searchQuery]);

  const boardColumns = useMemo(() => {
    return STATUS_OPTIONS.filter(
      (opt) => opt.value !== "withdrawn" || stats.withdrawn > 0
    ).map((opt) => ({
      ...opt,
      items: filteredApplications.filter((item) => item.status === opt.value),
    }));
  }, [filteredApplications, stats.withdrawn]);

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Application Tracker</h1>
          <p className={styles.subtitle}>
            {loading
              ? "Loading your job application pipeline…"
              : `${stats.total} tracked · ${stats.applied} applied · ${stats.interviewing} interviewing · ${stats.offer} offer${stats.offer === 1 ? "" : "s"}`}
          </p>
        </div>

        <button type="button" onClick={openCreateModal} className={styles.primaryBtn}>
          <Plus size={16} strokeWidth={2} />
          <span>Add Application</span>
        </button>
      </header>

      <div className={styles.toolbar}>
        <div className={styles.filterTabs} role="tablist" aria-label="Filter by application status">
          <button
            type="button"
            role="tab"
            aria-selected={statusFilter === "all"}
            onClick={() => setStatusFilter("all")}
            className={`${styles.filterTab} ${statusFilter === "all" ? styles.filterTabActive : ""}`}
          >
            <span>All</span>
            <span className={styles.filterCount}>{stats.total}</span>
          </button>
          {STATUS_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              type="button"
              role="tab"
              aria-selected={statusFilter === opt.value}
              onClick={() => setStatusFilter(opt.value)}
              className={`${styles.filterTab} ${
                statusFilter === opt.value ? styles.filterTabActive : ""
              }`}
            >
              <span>{opt.label}</span>
              <span className={styles.filterCount}>{stats[opt.value]}</span>
            </button>
          ))}
        </div>

        <div className={styles.controlsRow}>
          <search className={styles.searchForm}>
            <Search size={15} strokeWidth={1.75} className={styles.searchIcon} />
            <input
              type="search"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search company, role, location, or notes…"
              aria-label="Search applications"
              className={styles.searchInput}
            />
          </search>

          <div className={styles.viewSwitch} role="group" aria-label="View mode">
            <button
              type="button"
              onClick={() => setViewMode("list")}
              className={`${styles.viewBtn} ${viewMode === "list" ? styles.viewBtnActive : ""}`}
              aria-pressed={viewMode === "list"}
            >
              <List size={14} strokeWidth={2} />
              <span>List</span>
            </button>
            <button
              type="button"
              onClick={() => setViewMode("board")}
              className={`${styles.viewBtn} ${viewMode === "board" ? styles.viewBtnActive : ""}`}
              aria-pressed={viewMode === "board"}
            >
              <Columns3 size={14} strokeWidth={2} />
              <span>Board</span>
            </button>
          </div>
        </div>
      </div>

      {pageError && (
        <div className={styles.errorBanner} role="alert">
          <AlertCircle size={16} strokeWidth={1.75} />
          <span>{pageError}</span>
        </div>
      )}

      {loading ? (
        <div className={styles.skeletonList} aria-label="Loading applications">
          {[0, 1, 2].map((i) => (
            <div key={i} className={styles.skeletonCard} />
          ))}
        </div>
      ) : filteredApplications.length === 0 ? (
        <div className={styles.emptyState}>
          <div className={styles.emptyIconBox}>
            <Briefcase size={22} strokeWidth={1.75} />
          </div>
          <h2 className={styles.emptyTitle}>
            {applications.length === 0
              ? "No job applications tracked yet"
              : "No matching applications"}
          </h2>
          <p className={styles.emptyDesc}>
            {applications.length === 0
              ? "Log roles you saved or applied to, keep job links handy, and monitor interviews and follow-up dates in one place."
              : "Try clearing your search query or switching the status filter above."}
          </p>
          {applications.length === 0 && (
            <button type="button" onClick={openCreateModal} className={styles.primaryBtn}>
              <Plus size={16} strokeWidth={2} />
              <span>Track First Application</span>
            </button>
          )}
        </div>
      ) : viewMode === "board" ? (
        <div className={styles.boardGrid}>
          {boardColumns.map((col) => (
            <section key={col.value} className={styles.boardColumn} aria-label={col.label}>
              <div className={styles.boardColumnHeader}>
                <h2 className={styles.boardColumnTitle}>{col.label}</h2>
                <span className={styles.boardColumnCount}>{col.items.length}</span>
              </div>
              {col.items.length === 0 ? (
                <p className={styles.boardEmpty}>No items</p>
              ) : (
                <div className={styles.boardCards}>
                  {col.items.map((item) => (
                    <article key={item.id} className={styles.boardCard}>
                      <span className={styles.boardCardRole}>{item.role_title}</span>
                      <span className={styles.boardCardCompany}>{item.company_name}</span>
                      {(item.location || item.salary_range) && (
                        <span className={styles.boardCardMeta}>
                          {[item.location, item.salary_range].filter(Boolean).join(" · ")}
                        </span>
                      )}
                      <div className={styles.boardCardFooter}>
                        <select
                          aria-label={`Status for ${item.company_name} ${item.role_title}`}
                          value={item.status}
                          disabled={updatingStatusId === item.id}
                          onChange={(e) =>
                            handleInlineStatusChange(item, e.target.value as ApplicationStatus)
                          }
                          data-status={item.status}
                          className={styles.statusSelect}
                        >
                          {STATUS_OPTIONS.map((opt) => (
                            <option key={opt.value} value={opt.value}>
                              {opt.label}
                            </option>
                          ))}
                        </select>
                        <button
                          type="button"
                          onClick={() => openEditModal(item)}
                          className={styles.iconBtn}
                          title="Edit application"
                          aria-label={`Edit ${item.company_name} ${item.role_title}`}
                        >
                          <Pencil size={14} strokeWidth={1.75} />
                        </button>
                      </div>
                    </article>
                  ))}
                </div>
              )}
            </section>
          ))}
        </div>
      ) : (
        <div className={styles.appList}>
          {filteredApplications.map((item) => {
            const followUpDue = isFollowUpDue(item);
            return (
              <article key={item.id} className={styles.appCard}>
                <div className={styles.appMain}>
                  <div className={styles.appTitleRow}>
                    <h2 className={styles.appRole}>{item.role_title}</h2>
                    <span className={styles.appCompany}>{item.company_name}</span>
                    {isSafeHttpUrl(item.job_url) && (
                      <a
                        href={item.job_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className={styles.jobUrlLink}
                      >
                        <span>Job Posting</span>
                        <ExternalLink size={12} strokeWidth={1.75} />
                      </a>
                    )}
                  </div>

                  <div className={styles.metaChips}>
                    {item.work_mode && (
                      <span className={styles.metaChip}>{WORK_MODE_LABELS[item.work_mode]}</span>
                    )}
                    {item.location && (
                      <span className={styles.metaChip}>
                        <MapPin size={12} strokeWidth={1.75} />
                        <span>{item.location}</span>
                      </span>
                    )}
                    {item.salary_range && (
                      <span className={styles.metaChip}>
                        <Wallet size={12} strokeWidth={1.75} />
                        <span>{item.salary_range}</span>
                      </span>
                    )}
                    {item.applied_date && (
                      <span className={styles.metaChip}>
                        <Calendar size={12} strokeWidth={1.75} />
                        <span>Applied {formatDateLabel(item.applied_date)}</span>
                      </span>
                    )}
                    {item.next_follow_up_date && (
                      <span
                        className={`${styles.metaChip} ${
                          followUpDue ? styles.followUpChipDue : ""
                        }`}
                      >
                        <Calendar size={12} strokeWidth={1.75} />
                        <span>
                          {followUpDue ? "Follow up due " : "Follow up "}
                          {formatDateLabel(item.next_follow_up_date)}
                        </span>
                      </span>
                    )}
                    {item.recruiter_name && (
                      <span className={styles.metaChip}>
                        <User size={12} strokeWidth={1.75} />
                        <span>
                          {item.recruiter_name}
                          {item.recruiter_contact ? ` (${item.recruiter_contact})` : ""}
                        </span>
                      </span>
                    )}
                  </div>

                  {item.notes && <p className={styles.notesPreview}>{item.notes}</p>}
                </div>

                <div className={styles.appActions}>
                  <select
                    aria-label={`Status for ${item.company_name} ${item.role_title}`}
                    value={item.status}
                    disabled={updatingStatusId === item.id}
                    onChange={(e) =>
                      handleInlineStatusChange(item, e.target.value as ApplicationStatus)
                    }
                    data-status={item.status}
                    className={styles.statusSelect}
                  >
                    {STATUS_OPTIONS.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>

                  <button
                    type="button"
                    onClick={() => openEditModal(item)}
                    className={styles.iconBtn}
                    title="Edit application"
                    aria-label={`Edit ${item.company_name} ${item.role_title}`}
                  >
                    <Pencil size={15} strokeWidth={1.75} />
                  </button>

                  {confirmDeleteId === item.id ? (
                    <div className={styles.confirmGroup}>
                      <button
                        type="button"
                        onClick={() => handleDelete(item.id)}
                        disabled={deletingId === item.id}
                        className={styles.confirmDeleteBtn}
                      >
                        {deletingId === item.id ? "…" : "Delete"}
                      </button>
                      <button
                        type="button"
                        onClick={() => setConfirmDeleteId(null)}
                        disabled={deletingId === item.id}
                        className={styles.cancelDeleteBtn}
                      >
                        Cancel
                      </button>
                    </div>
                  ) : (
                    <button
                      type="button"
                      onClick={() => setConfirmDeleteId(item.id)}
                      className={`${styles.iconBtn} ${styles.deleteBtn}`}
                      disabled={Boolean(deletingId)}
                      title="Delete application"
                      aria-label={`Delete ${item.company_name} ${item.role_title}`}
                    >
                      <Trash2 size={15} strokeWidth={1.75} />
                    </button>
                  )}
                </div>
              </article>
            );
          })}
        </div>
      )}

      <dialog ref={dialogRef} aria-labelledby="app-modal-title" className={styles.dialog}>
        <div className={styles.dialogInner}>
          <div className={styles.dialogHeader}>
            <h2 id="app-modal-title" className={styles.dialogTitle}>
              {editingItem ? "Edit Application" : "Track New Application"}
            </h2>
            <button
              type="button"
              onClick={closeModal}
              className={styles.dialogCloseBtn}
              aria-label="Close modal"
            >
              <X size={16} strokeWidth={1.75} />
            </button>
          </div>

          {formError && (
            <div className={styles.errorBanner} role="alert" aria-live="polite">
              <AlertCircle size={16} strokeWidth={1.75} />
              <span>{formError}</span>
            </div>
          )}

          <form onSubmit={handleSaveApplication} className={styles.form}>
            <div className={styles.formRow}>
              <div className={styles.field}>
                <label htmlFor="company_name" className={styles.label}>
                  Company <span className={styles.requiredMark}>*</span>
                </label>
                <input
                  id="company_name"
                  name="company_name"
                  type="text"
                  required
                  maxLength={255}
                  autoFocus
                  value={form.company_name}
                  onChange={(e) => setForm((p) => ({ ...p, company_name: e.target.value }))}
                  placeholder="e.g., Stripe"
                  className={styles.input}
                />
              </div>

              <div className={styles.field}>
                <label htmlFor="role_title" className={styles.label}>
                  Role <span className={styles.requiredMark}>*</span>
                </label>
                <input
                  id="role_title"
                  name="role_title"
                  type="text"
                  required
                  maxLength={255}
                  value={form.role_title}
                  onChange={(e) => setForm((p) => ({ ...p, role_title: e.target.value }))}
                  placeholder="e.g., Senior Backend Engineer"
                  className={styles.input}
                />
              </div>
            </div>

            <div className={styles.formRow}>
              <div className={styles.field}>
                <label htmlFor="job_url" className={styles.label}>
                  Job URL
                </label>
                <input
                  id="job_url"
                  name="job_url"
                  type="url"
                  maxLength={2048}
                  autoCorrect="off"
                  autoCapitalize="none"
                  spellCheck={false}
                  value={form.job_url}
                  onChange={(e) => setForm((p) => ({ ...p, job_url: e.target.value }))}
                  placeholder="https://company.com/careers/123"
                  className={styles.input}
                />
              </div>

              <div className={styles.field}>
                <label htmlFor="status" className={styles.label}>
                  Status <span className={styles.requiredMark}>*</span>
                </label>
                <select
                  id="status"
                  name="status"
                  required
                  value={form.status}
                  onChange={(e) =>
                    handleStatusFieldChange(e.target.value as ApplicationStatus)
                  }
                  className={styles.select}
                >
                  {STATUS_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>
                      {opt.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>

            <div className={styles.formRow}>
              <div className={styles.field}>
                <label htmlFor="applied_date" className={styles.label}>
                  Applied Date
                </label>
                <input
                  id="applied_date"
                  name="applied_date"
                  type="date"
                  value={form.applied_date}
                  onChange={(e) => setForm((p) => ({ ...p, applied_date: e.target.value }))}
                  className={styles.input}
                />
              </div>

              <div className={styles.field}>
                <label htmlFor="next_follow_up_date" className={styles.label}>
                  Next Follow-up / Interview Date
                </label>
                <input
                  id="next_follow_up_date"
                  name="next_follow_up_date"
                  type="date"
                  value={form.next_follow_up_date}
                  onChange={(e) =>
                    setForm((p) => ({ ...p, next_follow_up_date: e.target.value }))
                  }
                  className={styles.input}
                />
              </div>
            </div>

            <div className={styles.formRow}>
              <div className={styles.field}>
                <label htmlFor="work_mode" className={styles.label}>
                  Work Mode
                </label>
                <select
                  id="work_mode"
                  name="work_mode"
                  value={form.work_mode}
                  onChange={(e) =>
                    setForm((p) => ({ ...p, work_mode: e.target.value as "" | WorkMode }))
                  }
                  className={styles.select}
                >
                  <option value="">Not specified</option>
                  <option value="remote">Remote</option>
                  <option value="hybrid">Hybrid</option>
                  <option value="onsite">On-site</option>
                </select>
              </div>

              <div className={styles.field}>
                <label htmlFor="location" className={styles.label}>
                  Location
                </label>
                <input
                  id="location"
                  name="location"
                  type="text"
                  maxLength={255}
                  value={form.location}
                  onChange={(e) => setForm((p) => ({ ...p, location: e.target.value }))}
                  placeholder="e.g., Singapore / Remote"
                  className={styles.input}
                />
              </div>
            </div>

            <div className={styles.formRow}>
              <div className={styles.field}>
                <label htmlFor="salary_range" className={styles.label}>
                  Salary / Compensation
                </label>
                <input
                  id="salary_range"
                  name="salary_range"
                  type="text"
                  maxLength={120}
                  value={form.salary_range}
                  onChange={(e) => setForm((p) => ({ ...p, salary_range: e.target.value }))}
                  placeholder="e.g., $140k - $170k"
                  className={styles.input}
                />
              </div>

              <div className={styles.field}>
                <label htmlFor="recruiter_name" className={styles.label}>
                  Recruiter / Contact Name
                </label>
                <input
                  id="recruiter_name"
                  name="recruiter_name"
                  type="text"
                  maxLength={255}
                  value={form.recruiter_name}
                  onChange={(e) => setForm((p) => ({ ...p, recruiter_name: e.target.value }))}
                  placeholder="e.g., Sarah Jenkins"
                  className={styles.input}
                />
              </div>
            </div>

            <div className={styles.field}>
              <label htmlFor="recruiter_contact" className={styles.label}>
                Recruiter Email / LinkedIn
              </label>
              <input
                id="recruiter_contact"
                name="recruiter_contact"
                type="text"
                maxLength={320}
                value={form.recruiter_contact}
                onChange={(e) => setForm((p) => ({ ...p, recruiter_contact: e.target.value }))}
                placeholder="e.g., sarah@company.com or linkedin.com/in/..."
                className={styles.input}
              />
            </div>

            <div className={styles.field}>
              <label htmlFor="notes" className={styles.label}>
                Notes (Interview Prep, Referral, Feedback)
              </label>
              <textarea
                id="notes"
                name="notes"
                maxLength={4000}
                value={form.notes}
                onChange={(e) => setForm((p) => ({ ...p, notes: e.target.value }))}
                placeholder="Referral contact, tailored CV angle, interview stages…"
                className={styles.textarea}
              />
            </div>

            <div className={styles.dialogFooter}>
              <button type="button" onClick={closeModal} className={styles.cancelBtn}>
                Cancel
              </button>
              <button type="submit" disabled={submitting} className={styles.primaryBtn}>
                <span>
                  {submitting
                    ? "Saving…"
                    : editingItem
                      ? "Save Changes"
                      : "Save Application"}
                </span>
              </button>
            </div>
          </form>
        </div>
      </dialog>
    </div>
  );
}
