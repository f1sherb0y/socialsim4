"""Web tooling: search and page viewing.

Exports:
- web_search(query: str, max_results: int = 5) -> List[dict]
- view_page(url: str, max_chars: int = 4000) -> dict
"""

from .search import web_search
from .view import view_page

