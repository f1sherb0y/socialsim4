from duckduckgo_search import DDGS


def web_search(query: str, max_results: int = 5):
    """Search the web via DuckDuckGo (DDGS) and return structured results.

    Returns: List[dict] with keys: title, url, snippet
    """
    max_results = max(1, min(10, int(max_results)))
    out = []
    with DDGS() as ddgs:
        for item in ddgs.text(query, max_results=max_results):
            out.append(
                {
                    "title": item.get("title", ""),
                    "url": item.get("href", ""),
                    "snippet": item.get("body", ""),
                }
            )
    return out
