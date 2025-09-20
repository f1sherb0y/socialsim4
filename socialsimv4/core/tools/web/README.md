Web tools (search and view)

Overview
- web_search(query, max_results=5) -> List[dict]
  - Returns: [{"title": str, "url": str, "snippet": str}]
- view_page(url, max_chars=4000) -> dict
  - Returns: {"title": Optional[str], "text": str, "truncated": bool, "content_type": Optional[str]}

Backends (prototype)
- Search: duckduckgo_search (DDGS) library.
- Page text extraction: trafilatura.

Dependencies
- duckduckgo_search (search)
- trafilatura (content extraction)
- httpx (networking)

Future expansion
- The code is structured to add providers (e.g., SerpAPI, Bing) later without changing the tool interfaces.
- Consider a headless browser (Playwright) if dynamic rendering is required.

Notes
- Keep this simple for now; add providers later without changing interfaces.
