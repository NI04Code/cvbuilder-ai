"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { useSession } from "next-auth/react";
import { apiClient, DocumentType, getDocumentEndpointConfig } from "@/lib/api";

interface FormDataState {
  job_title: string;
  company_name: string;
  job_description: string;
}

interface DocumentGenerationContextType {
  isGeneratingCv: boolean;
  isGeneratingCoverLetter: boolean;
  cvError: string | null;
  coverLetterError: string | null;
  formData: FormDataState;
  generatedCv: any;
  generatedCoverLetter: any;
  setFormData: React.Dispatch<React.SetStateAction<FormDataState>>;
  setCvError: React.Dispatch<React.SetStateAction<string | null>>;
  setCoverLetterError: React.Dispatch<React.SetStateAction<string | null>>;
  clearGeneratedDocIfMatches: (docId: string) => void;
  startGeneration: (mode?: DocumentType) => Promise<void>;
}

const initialFormData: FormDataState = {
  job_title: "",
  company_name: "",
  job_description: "",
};

const DocumentGenerationContext = createContext<DocumentGenerationContextType | undefined>(
  undefined
);

export function DocumentGenerationProvider({ children }: { children: React.ReactNode }) {
  const { data: session } = useSession();
  const userId = session?.user?.id;

  const [isGeneratingCv, setIsGeneratingCv] = useState(false);
  const [isGeneratingCoverLetter, setIsGeneratingCoverLetter] = useState(false);
  const [cvError, setCvError] = useState<string | null>(null);
  const [coverLetterError, setCoverLetterError] = useState<string | null>(null);
  const [formData, setFormData] = useState<FormDataState>(initialFormData);
  const [generatedCv, setGeneratedCv] = useState<any>(null);
  const [generatedCoverLetter, setGeneratedCoverLetter] = useState<any>(null);

  // Clear state if the authenticated user changes or signs out
  useEffect(() => {
    setIsGeneratingCv(false);
    setIsGeneratingCoverLetter(false);
    setCvError(null);
    setCoverLetterError(null);
    setFormData(initialFormData);
    setGeneratedCv(null);
    setGeneratedCoverLetter(null);
  }, [userId]);

  const startGeneration = useCallback(
    async (mode: DocumentType = "cv") => {
      const isCoverLetter = mode === "cover_letter";
      const busy = isCoverLetter ? isGeneratingCoverLetter : isGeneratingCv;
      const setModeError = isCoverLetter ? setCoverLetterError : setCvError;
      const setModeBusy = isCoverLetter ? setIsGeneratingCoverLetter : setIsGeneratingCv;

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
        const response = await apiClient.post(`${apiBase}/generate`, formData, {
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
        });

        if (isCoverLetter) {
          setGeneratedCoverLetter(response.data);
        } else {
          setGeneratedCv(response.data);
        }
      } catch (err: any) {
        console.error("Generation error:", err);
        setModeError(
          err.response?.data?.detail ||
            `An error occurred while generating your ${isCoverLetter ? "cover letter" : "CV"}.`
        );
      } finally {
        setModeBusy(false);
      }
    },
    [isGeneratingCv, isGeneratingCoverLetter, formData, session]
  );

  const clearGeneratedDocIfMatches = useCallback((docId: string) => {
    setGeneratedCv((prev: any) => (prev?.id === docId ? null : prev));
    setGeneratedCoverLetter((prev: any) => (prev?.id === docId ? null : prev));
  }, []);

  return (
    <DocumentGenerationContext.Provider
      value={{
        isGeneratingCv,
        isGeneratingCoverLetter,
        cvError,
        coverLetterError,
        formData,
        generatedCv,
        generatedCoverLetter,
        setFormData,
        setCvError,
        setCoverLetterError,
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
  return context !== undefined;
}

