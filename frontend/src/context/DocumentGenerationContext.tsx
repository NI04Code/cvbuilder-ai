"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { useSession } from "next-auth/react";
import { apiClient, DocumentType, getDocumentEndpointConfig } from "@/lib/api";

interface FormDataState {
  job_title: string;
  company_name: string;
  recruiter_name: string;
  job_description: string;
}

interface DocumentGenerationContextType {
  isInsideDashboard: boolean;
  isGeneratingCv: boolean;
  isGeneratingCoverLetter: boolean;
  isGeneratingColdEmail: boolean;
  cvError: string | null;
  coverLetterError: string | null;
  coldEmailError: string | null;
  formData: FormDataState;
  generatedCv: any;
  generatedCoverLetter: any;
  generatedColdEmail: any;
  setFormData: React.Dispatch<React.SetStateAction<FormDataState>>;
  setCvError: React.Dispatch<React.SetStateAction<string | null>>;
  setCoverLetterError: React.Dispatch<React.SetStateAction<string | null>>;
  setColdEmailError: React.Dispatch<React.SetStateAction<string | null>>;
  clearGeneratedDocIfMatches: (docId: string) => void;
  startGeneration: (mode?: DocumentType) => Promise<void>;
}

const initialFormData: FormDataState = {
  job_title: "",
  company_name: "",
  recruiter_name: "",
  job_description: "",
};

const DocumentGenerationContext = createContext<DocumentGenerationContextType | undefined>(
  undefined
);

export function DocumentGenerationProvider({
  children,
  hasSidebar = true,
}: {
  children: React.ReactNode;
  hasSidebar?: boolean;
}) {
  const { data: session } = useSession();
  const userId = session?.user?.id;

  const [isGeneratingCv, setIsGeneratingCv] = useState(false);
  const [isGeneratingCoverLetter, setIsGeneratingCoverLetter] = useState(false);
  const [isGeneratingColdEmail, setIsGeneratingColdEmail] = useState(false);
  const [cvError, setCvError] = useState<string | null>(null);
  const [coverLetterError, setCoverLetterError] = useState<string | null>(null);
  const [coldEmailError, setColdEmailError] = useState<string | null>(null);
  const [formData, setFormData] = useState<FormDataState>(initialFormData);
  const [generatedCv, setGeneratedCv] = useState<any>(null);
  const [generatedCoverLetter, setGeneratedCoverLetter] = useState<any>(null);
  const [generatedColdEmail, setGeneratedColdEmail] = useState<any>(null);

  // Clear state if the authenticated user changes or signs out
  useEffect(() => {
    setIsGeneratingCv(false);
    setIsGeneratingCoverLetter(false);
    setIsGeneratingColdEmail(false);
    setCvError(null);
    setCoverLetterError(null);
    setColdEmailError(null);
    setFormData(initialFormData);
    setGeneratedCv(null);
    setGeneratedCoverLetter(null);
    setGeneratedColdEmail(null);
  }, [userId]);

  const startGeneration = useCallback(
    async (mode: DocumentType = "cv") => {
      const isCoverLetter = mode === "cover_letter";
      const isColdEmail = mode === "cold_email";
      const busy = isColdEmail
        ? isGeneratingColdEmail
        : isCoverLetter
          ? isGeneratingCoverLetter
          : isGeneratingCv;
      const setModeError = isColdEmail
        ? setColdEmailError
        : isCoverLetter
          ? setCoverLetterError
          : setCvError;
      const setModeBusy = isColdEmail
        ? setIsGeneratingColdEmail
        : isCoverLetter
          ? setIsGeneratingCoverLetter
          : setIsGeneratingCv;

      if (busy) return;

      const trimmedJd = formData.job_description.trim();
      if (!trimmedJd || trimmedJd.length < 50) {
        setModeError("Please provide a more detailed job description (at least 50 characters).");
        return;
      }
      if (trimmedJd.length > 2500) {
        setModeError("Job description must be 2,500 characters or fewer.");
        return;
      }

      setModeError(null);
      setModeBusy(true);

      try {
        const token = (session as any)?.backendAccessToken;
        const { apiBase } = getDocumentEndpointConfig(mode);
        const payload = isColdEmail
          ? {
              job_title: formData.job_title,
              company_name: formData.company_name,
              recruiter_name: formData.recruiter_name,
              job_description: formData.job_description,
            }
          : {
              job_title: formData.job_title,
              company_name: formData.company_name,
              job_description: formData.job_description,
            };

        const response = await apiClient.post(`${apiBase}/generate`, payload, {
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
        });

        if (isColdEmail) {
          setGeneratedColdEmail(response.data);
        } else if (isCoverLetter) {
          setGeneratedCoverLetter(response.data);
        } else {
          setGeneratedCv(response.data);
        }
      } catch (err: any) {
        console.error("Generation error:", err);
        const docLabel = isColdEmail
          ? "cold email"
          : isCoverLetter
            ? "cover letter"
            : "CV";
        setModeError(
          err.response?.data?.detail ||
            `An error occurred while generating your ${docLabel}.`
        );
      } finally {
        setModeBusy(false);
      }
    },
    [isGeneratingCv, isGeneratingCoverLetter, isGeneratingColdEmail, formData, session]
  );

  const clearGeneratedDocIfMatches = useCallback((docId: string) => {
    setGeneratedCv((prev: any) => (prev?.id === docId ? null : prev));
    setGeneratedCoverLetter((prev: any) => (prev?.id === docId ? null : prev));
    setGeneratedColdEmail((prev: any) => (prev?.id === docId ? null : prev));
  }, []);

  return (
    <DocumentGenerationContext.Provider
      value={{
        isInsideDashboard: hasSidebar,
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
        setCvError,
        setCoverLetterError,
        setColdEmailError,
        clearGeneratedDocIfMatches,
        startGeneration,
      }}
    >
      {children}
    </DocumentGenerationContext.Provider>
  );
}

export function useDocumentGeneration() {
  const context = useContext(DocumentGenerationContext);
  if (!context) {
    throw new Error("useDocumentGeneration must be used within a DocumentGenerationProvider");
  }
  return context;
}

export function useIsInsideDashboard(): boolean {
  const context = useContext(DocumentGenerationContext);
  return Boolean(context?.isInsideDashboard);
}
