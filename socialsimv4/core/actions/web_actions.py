import re

from socialsimv4.core.action import Action
from socialsimv4.core.tools.web import view_page as tool_view_page
from socialsimv4.core.tools.web import web_search as tool_web_search


class WebSearchAction(Action):
    NAME = "web_search"
    DESC = "Search the web and return top results (title, URL, snippet)."
    INSTRUCTION = """- To search the web for information:
<Action name=\"web_search\"><query>[keywords or question]</query><max_results>5</max_results></Action>
"""

    def handle(self, action_data, agent, simulator, scene):
        query = (action_data or {}).get("query")
        if not query:
            agent.append_env_message("web_search: missing <query>.")
            return False
        try:
            max_results = int((action_data or {}).get("max_results", 5))
        except Exception:
            max_results = 5
        max_results = max(1, min(10, max_results))

        try:
            results = tool_web_search(query, max_results)
        except Exception as e:
            agent.append_env_message(f"web_search failed: {e}")
            return False

        if not results:
            agent.append_env_message("web_search: no results or network unavailable.")
            return False

        # Format and deliver results to the agent only (not broadcast)
        lines = [f"Web search results for '{query}':"]
        for i, r in enumerate(results, 1):
            title = r.get("title", "").strip()
            url = r.get("url", "").strip()
            snippet = r.get("snippet", "").strip()
            if snippet:
                snippet = re.sub(r"\s+", " ", snippet)
            lines.append(f"{i}. {title} - {url}")
            if snippet:
                lines.append(f"   {snippet}")
        agent.append_env_message("\n".join(lines))
        simulator.log_event(
            "web_search",
            {"agent": agent.name, "query": query, "count": len(results)},
        )
        return True


class ViewPageAction(Action):
    NAME = "view_page"
    DESC = "Fetch and preview the text content of a web page."
    INSTRUCTION = """- To view a web page's text content:
<Action name=\"view_page\"><url>https://example.com/article</url><max_chars>4000</max_chars></Action>
"""

    def handle(self, action_data, agent, simulator, scene):
        url = (action_data or {}).get("url", "").strip()
        if not url:
            agent.append_env_message("view_page: missing <url>.")
            return False

        try:
            max_chars = int((action_data or {}).get("max_chars", 4000))
        except Exception:
            max_chars = 4000
        max_chars = max(500, min(20000, max_chars))

        try:
            data = tool_view_page(url, max_chars)
        except Exception as e:
            agent.append_env_message(f"view_page failed: {e}")
            return False

        title = data.get("title")
        text = data.get("text", "")
        header = f"Page content preview: {title}" if title else "Page content preview:"
        agent.append_env_message(f"{header}\nURL: {url}\n\n{text}")
        simulator.log_event(
            "view_page",
            {
                "agent": agent.name,
                "url": url,
                "length": len(text),
                "truncated": bool(data.get("truncated")),
            },
        )
        return True
