"use client";

import { useState, useEffect } from "react";
import { FileSignature, Sparkles, Download, Eye, AlertCircle } from "lucide-react";
import { motion } from "framer-motion";
import { useSession } from "next-auth/react";
import { apiClient } from "@/lib/api";
import { useCVGeneration } from "@/context/CVGenerationContext";
import styles from "./page.module.css";
import Link from "next/link";

export default function GeneratePage() {
  const { data: session, status, update } = useSession();
  const { isGenerating, error, formData, generatedCv, setFormData, startGeneration } = useCVGeneration();
  const [hasProfile, setHasProfile] = useState<boolean | null>(null);

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

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    await startGeneration();
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    setFormData((prev) => ({
      ...prev,
      [e.target.name]: e.target.value,
    }));
  };

  if (hasProfile === false) {
    return (
      <div className={styles.emptyPreview} style={{ height: '80vh' }}>
        <AlertCircle size={48} className="mb-4 opacity-50" />
        <h2 className="text-xl font-bold mb-2">Profile Required</h2>
        <p className="mb-4">You need to upload and parse a resume before you can generate tailored CVs.</p>
        <Link href="/profile" className={styles.actionBtn}>
          Go to Upload
        </Link>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      {/* Left Panel: Input Form */}
      <div className={styles.leftPanel}>
        <header className={styles.header}>
          <h1 className={styles.title}>Tailor Your CV</h1>
          <p className={styles.subtitle}>
            Paste the job details and let our AI optimize your profile for ATS.
          </p>
        </header>

        {error && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className={styles.errorMsg}>
            <AlertCircle size={20} />
            {error}
          </motion.div>
        )}

        <form onSubmit={handleGenerate} className="flex flex-col gap-6">
          <div className="flex gap-4">
            <div className={styles.formGroup} style={{ flex: 1 }}>
              <label htmlFor="job_title" className={styles.label}>Job Title (Optional)</label>
              <input
                type="text"
                id="job_title"
                name="job_title"
                value={formData.job_title}
                onChange={handleChange}
                placeholder="e.g. Senior Software Engineer"
                className={styles.input}
              />
            </div>
            <div className={styles.formGroup} style={{ flex: 1 }}>
              <label htmlFor="company_name" className={styles.label}>Company (Optional)</label>
              <input
                type="text"
                id="company_name"
                name="company_name"
                value={formData.company_name}
                onChange={handleChange}
                placeholder="e.g. Google"
                className={styles.input}
              />
            </div>
          </div>

          <div className={styles.formGroup}>
            <label htmlFor="job_description" className={styles.label}>Job Description *</label>
            <textarea
              id="job_description"
              name="job_description"
              value={formData.job_description}
              onChange={handleChange}
              placeholder="Paste the full job description here..."
              className={styles.textarea}
              required
            />
          </div>

          <button 
            type="submit" 
            className={styles.generateBtn}
            disabled={isGenerating || formData.job_description.length < 10}
          >
            {isGenerating ? (
              <>
                <span className={styles.spinner} style={{ width: '20px', height: '20px', borderWidth: '2px' }} />
                Generating ATS-Optimized CV...
              </>
            ) : (
              <>
                <Sparkles size={20} />
                Generate Tailored CV
              </>
            )}
          </button>
        </form>
      </div>

      {/* Right Panel: Preview */}
      <div className={styles.rightPanel}>
        <div className={styles.previewHeader}>
          <div className={styles.previewTitle}>
            <Eye size={20} />
            CV Preview
          </div>
          {generatedCv && (
            <div className={styles.actions}>
              {generatedCv.ats_score && (
                <div className={styles.atsScore} title="Estimated ATS Match Score">
                  ATS: {generatedCv.ats_score}%
                </div>
              )}
              <button className={styles.actionBtn} onClick={async () => {
                const token = (session as any)?.backendAccessToken;
                const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/cv/${generatedCv.id}/download`, {
                  headers: { Authorization: `Bearer ${token}` }
                });
                if (res.ok) {
                  const blob = await res.blob();
                  const url = window.URL.createObjectURL(blob);
                  const a = document.createElement('a');
                  a.href = url;
                  a.download = `CV_${formData.company_name || 'Tailored'}.pdf`;
                  a.click();
                }
              }}>
                <Download size={16} />
                Download PDF
              </button>
            </div>
          )}
        </div>
        
        <div className={styles.previewContent}>
          {isGenerating ? (
            <div className={styles.loadingState}>
              <div className={styles.spinner} />
              <p>Analyzing job requirements and tailoring content...</p>
            </div>
          ) : generatedCv ? (
            <div className={styles.emptyPreview}>
              <FileSignature size={64} className="mb-4 text-green-500 opacity-80" />
              <h3 className="text-lg font-medium text-gray-800">CV Generated Successfully!</h3>
              <p className="text-sm mt-2 text-gray-500">
                Your tailored CV for {generatedCv.job_title || 'the role'} at {generatedCv.company_name || 'the company'} is ready.
              </p>
              <p className="text-sm mt-1 text-gray-500">
                Click "Download PDF" to view and save it.
              </p>
            </div>
          ) : (
            <div className={styles.emptyPreview}>
              <FileSignature size={48} className="mb-4 opacity-50" />
              <p>Fill out the job details and generate to see your tailored CV here.</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
