"""Unit tests for app.utils.url."""

from app.utils.url import infer_link_label, sanitize_external_url, strip_url_scheme


def test_sanitize_external_url():
    assert sanitize_external_url(None) is None
    assert sanitize_external_url("   ") is None
    assert sanitize_external_url("javascript:alert(1)") is None
    assert sanitize_external_url("data:text/html,hi") is None
    assert sanitize_external_url("LinkedIn") is None
    assert sanitize_external_url("github.com/alex") == "https://github.com/alex"
    assert sanitize_external_url("http://example.com") == "http://example.com"


def test_strip_url_scheme_and_infer_link_label():
    assert strip_url_scheme("https://www.github.com/alex/") == "github.com/alex"
    assert strip_url_scheme("http://example.com") == "example.com"
    assert infer_link_label("https://github.com/alex") == "GitHub"
    assert infer_link_label("https://unknown.example.com", fallback="Website") == "Website"
