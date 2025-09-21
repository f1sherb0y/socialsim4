import html
import re
import httpx
from urllib.parse import urlparse


def http_get(url: str, headers=None, timeout=10):
    """GET a URL and return (text, content_type) using httpx.

    Raises RuntimeError on HTTP/network errors.
    """
    try:
        with httpx.Client(follow_redirects=True, timeout=timeout, headers=headers or {}) as client:
            resp = client.get(url)
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "")
            text = resp.text
            return text, content_type
    except httpx.HTTPError as e:
        raise RuntimeError(f"HTTP error: {e}")


def strip_html_text(html_content: str) -> str:
    # Remove script/style
    html_content = re.sub(
        r"<script[\s\S]*?</script>", " ", html_content, flags=re.IGNORECASE
    )
    html_content = re.sub(
        r"<style[\s\S]*?</style>", " ", html_content, flags=re.IGNORECASE
    )
    # Replace common block elements with newlines for readability
    html_content = re.sub(
        r"<(br|p|div|li|h[1-6]|section|article|header|footer)[^>]*>",
        "\n",
        html_content,
        flags=re.IGNORECASE,
    )
    # Strip remaining tags
    text = re.sub(r"<[^>]+>", " ", html_content)
    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def safe_http_https_only(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https")
    except Exception:
        return False
