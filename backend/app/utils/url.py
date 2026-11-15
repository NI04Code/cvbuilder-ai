"""URL sanitization and display formatting helpers for profile links and PDF templates."""

from urllib.parse import urlsplit

_KNOWN_HOST_LABELS: tuple[tuple[str, str], ...] = (
    ("linkedin.com", "LinkedIn"),
    ("github.com", "GitHub"),
    ("gitlab.com", "GitLab"),
    ("kaggle.com", "Kaggle"),
    ("huggingface.co", "Hugging Face"),
    ("scholar.google.", "Google Scholar"),
    ("behance.net", "Behance"),
    ("dribbble.com", "Dribbble"),
    ("medium.com", "Medium"),
    ("substack.com", "Substack"),
)


def sanitize_external_url(raw: str | None) -> str | None:
    """Validate and normalize an external URL to a safe http(s) href, or return None.

    Returns plain label placeholders (e.g., 'LinkedIn') as None for href rendering while
    auto-prefixing bare domains (e.g., 'linkedin.com/in/user' -> 'https://linkedin.com/in/user').
    """
    if raw is None:
        return None
    cleaned = raw.strip()
    if not cleaned:
        return None

    lower = cleaned.lower()
    if any(lower.startswith(bad) for bad in ("javascript:", "data:", "vbscript:", "file:")):
        return None

    if "://" not in cleaned:
        if "." not in cleaned.split("/", 1)[0]:
            return None
        cleaned = f"https://{cleaned}"

    parsed = urlsplit(cleaned)
    if parsed.scheme.lower() not in ("http", "https") or not parsed.netloc:
        return None

    return cleaned


def strip_url_scheme(url: str) -> str:
    """Return URL without leading scheme or trailing slash for compact display."""
    stripped = url.strip()
    for prefix in ("https://www.", "http://www.", "https://", "http://"):
        if stripped.lower().startswith(prefix):
            stripped = stripped[len(prefix):]
            break
    return stripped.rstrip("/")


def infer_link_label(url: str, fallback: str = "Other Link") -> str:
    """Infer a concise human-readable label (e.g., 'GitHub') from an external URL."""
    host = urlsplit(url).netloc.lower()
    for domain_fragment, label in _KNOWN_HOST_LABELS:
        if domain_fragment in host:
            return label
    return fallback

