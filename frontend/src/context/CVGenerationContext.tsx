"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { useSession } from "next-auth/react";
import { apiClient } from "@/lib/api";

interface FormDataState {
  job_title: string;
  company_name: string;
  job_description: string;
}

interface CVGenerationContextType {
  isGenerating: boolean;
  error: string | null;
  formData: FormDataState;
  generatedCv: any;
  setFormData: React.Dispatch<React.SetStateAction<FormDataState>>;
  setError: React.Dispatch<React.SetStateAction<string | null>>;
  clearGeneratedCvIfMatches: (cvId: string) => void;
  startGeneration: () => Promise<void>;
}

const initialFormData: FormDataState = {
  job_title: "",
  company_name: "",
  job_description: "",
};

const CVGenerationContext = createContext<CVGenerationContextType | undefined>(undefined);

export function CVGenerationProvider({ children }: { children: React.ReactNode }) {
  const { data: session } = useSession();
  const userId = session?.user?.id;

  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [formData, setFormData] = useState<FormDataState>(initialFormData);
  const [generatedCv, setGeneratedCv] = useState<any>(null);

  // Clear state if the authenticated user changes or signs out
  useEffect(() => {
    setIsGenerating(false);
    setError(null);
    setFormData(initialFormData);
    setGeneratedCv(null);
  }, [userId]);

  const startGeneration = useCallback(async () => {
    if (isGenerating) return;

    const trimmedJd = formData.job_description.trim();
    if (!trimmedJd || trimmedJd.length < 50) {
      setError("Please provide a more detailed job description (at least 50 characters).");
      return;
    }
    if (trimmedJd.length > 2500) {
      setError("Job description must be 2,500 characters or fewer.");
      return;
    }

    setError(null);
    setIsGenerating(true);

    try {
      const token = (session as any)?.backendAccessToken;
      const response = await apiClient.post("/cv/generate", formData, {
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
        },
      });

      setGeneratedCv(response.data);
    } catch (err: any) {
      console.error("Generation error:", err);
      setError(err.response?.data?.detail || "An error occurred while generating your CV.");
    } finally {
      setIsGenerating(false);
    }
  }, [isGenerating, formData, session]);

  const clearGeneratedCvIfMatches = useCallback((cvId: string) => {
    setGeneratedCv((prev: any) => (prev?.id === cvId ? null : prev));
  }, []);

  return (
    <CVGenerationContext.Provider
      value={{
        isGenerating,
        error,
        formData,
        generatedCv,
        setFormData,
        setError,
        clearGeneratedCvIfMatches,
        startGeneration,
      }}
    >
      {children}
    </CVGenerationContext.Provider>
  );
}

export function useCVGeneration() {
  const context = useContext(CVGenerationContext);
  if (!context) {
    throw new Error("useCVGeneration must be used within a CVGenerationProvider");
  }
  return context;
}

export function useIsInsideDashboard(): boolean {
  const context = useContext(CVGenerationContext);
  return context !== undefined;
}


