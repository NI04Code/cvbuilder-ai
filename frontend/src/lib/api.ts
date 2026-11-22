import axios, { AxiosError, InternalAxiosRequestConfig } from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

export const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

let inFlightRefresh: Promise<string | null> | null = null;

/**
 * Triggers a NextAuth session check on the client so expired or near-expiry
 * backendAccessTokens are refreshed via /api/auth/session without stamping concurrent requests.
 */
async function getRefreshedAccessToken(): Promise<string | null> {
  if (typeof window === "undefined") {
    return null;
  }
  if (!inFlightRefresh) {
    inFlightRefresh = (async () => {
      try {
        const { getSession } = await import("next-auth/react");
        const session = await getSession();
        return ((session as any)?.backendAccessToken as string | undefined) ?? null;
      } catch {
        return null;
      } finally {
        inFlightRefresh = null;
      }
    })();
  }
  return inFlightRefresh;
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as
      | (InternalAxiosRequestConfig & { _retry?: boolean })
      | undefined;

    if (
      typeof window === "undefined" ||
      error.response?.status !== 401 ||
      !originalRequest ||
      originalRequest._retry ||
      originalRequest.url?.includes("/auth/")
    ) {
      return Promise.reject(error);
    }

    originalRequest._retry = true;
    const freshToken = await getRefreshedAccessToken();
    if (!freshToken) {
      return Promise.reject(error);
    }

    originalRequest.headers.set("Authorization", `Bearer ${freshToken}`);
    return apiClient(originalRequest);
  }
);

export type DocumentType = "cv" | "cover_letter" | "cold_email";

const DOCUMENT_ENDPOINT_MAP: Record<DocumentType, { apiBase: string; filenamePrefix: string }> = {
  cv: { apiBase: "/cv", filenamePrefix: "cv" },
  cover_letter: { apiBase: "/cover-letters", filenamePrefix: "cover-letter" },
  cold_email: { apiBase: "/cold-emails", filenamePrefix: "cold-email" },
};

export function getDocumentEndpointConfig(documentType: DocumentType = "cv") {
  return DOCUMENT_ENDPOINT_MAP[documentType] || DOCUMENT_ENDPOINT_MAP.cv;
}

function sanitizeFilenameSegment(value?: string | null, fallback = "Tailored"): string {
  const cleaned = (value || "").trim().replace(/[^a-zA-Z0-9]+/g, "-").replace(/^-+|-+$/g, "");
  return cleaned || fallback;
}

/**
 * Extracts the downloaded PDF filename from Content-Disposition if exposed by the API,
 * otherwise builds `<prefix>-<company>-<user-name>.pdf` without any unique code.
 */
export function extractDownloadFilename(
  contentDisposition: string | null,
  fallbackCompany?: string | null,
  fallbackUserName?: string | null,
  documentType: DocumentType = "cv"
): string {
  if (contentDisposition) {
    const utf8Match = contentDisposition.match(/filename\*\s*=\s*UTF-8''([^;]+)/i);
    if (utf8Match?.[1]) {
      return decodeURIComponent(utf8Match[1].trim().replace(/^["']|["']$/g, ""));
    }
    const plainMatch = contentDisposition.match(/filename\s*=\s*("?)([^";\n]+)\1/i);
    if (plainMatch?.[2]) {
      return plainMatch[2].trim();
    }
  }

  const { filenamePrefix } = getDocumentEndpointConfig(documentType);
  const companyPart = sanitizeFilenameSegment(fallbackCompany, "Tailored");
  const namePart = sanitizeFilenameSegment(fallbackUserName, "Candidate");
  return `${filenamePrefix}-${companyPart}-${namePart}.pdf`;
}

/**
 * Shared authenticated PDF download helper for any generated document type.
 */
export async function downloadDocumentPdf(options: {
  docId: string;
  documentType: DocumentType;
  token?: string;
  fallbackCompany?: string | null;
  fallbackUserName?: string | null;
}): Promise<boolean> {
  const { docId, documentType, token, fallbackCompany, fallbackUserName } = options;
  const { apiBase } = getDocumentEndpointConfig(documentType);
  const downloadUrl = `${API_URL}${apiBase}/${docId}/download`;

  let res = await fetch(downloadUrl, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (res.status === 401) {
    const freshToken = await getRefreshedAccessToken();
    if (freshToken) {
      res = await fetch(downloadUrl, {
        headers: { Authorization: `Bearer ${freshToken}` },
      });
    }
  }
  if (!res.ok) {
    return false;
  }

  const blob = await res.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = extractDownloadFilename(
    res.headers.get("content-disposition"),
    fallbackCompany,
    fallbackUserName,
    documentType
  );
  a.click();
  window.URL.revokeObjectURL(url);
  return true;
}
