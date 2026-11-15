import axios from "axios";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api";

export const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

function sanitizeFilenameSegment(value?: string | null, fallback = "Tailored"): string {
  const cleaned = (value || "").trim().replace(/[^a-zA-Z0-9]+/g, "-").replace(/^-+|-+$/g, "");
  return cleaned || fallback;
}

/**
 * Extracts the downloaded PDF filename from Content-Disposition if exposed by the API,
 * otherwise builds `cv-<company>-<user-name>.pdf` without any unique code.
 */
export function extractDownloadFilename(
  contentDisposition: string | null,
  fallbackCompany?: string | null,
  fallbackUserName?: string | null
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

  const companyPart = sanitizeFilenameSegment(fallbackCompany, "Tailored");
  const namePart = sanitizeFilenameSegment(fallbackUserName, "Candidate");
  return `cv-${companyPart}-${namePart}.pdf`;
}
