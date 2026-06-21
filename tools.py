"""
The two tools the research agent can call.

`web_search`  -> resolve a company name to its real site / find news pages.
`fetch_url`   -> download a page and return clean readable text.

Resolving the URL via search (instead of guessing example.com) is itself an
anti-hallucination measure: we never invent the company's web address.
"""

from __future__ import annotations
import os
import httpx

SEARCH_KEY = os.environ.get("TAVILY_API_KEY")


def web_search(query: str, max_results: int = 5) -> list[dict]:
    """Returns [{title, url, snippet}]. Uses Tavily; swap for Brave/Serper freely."""
    if not SEARCH_KEY:
        return [{"title": "SEARCH DISABLED",
                 "url": "",
                 "snippet": "No TAVILY_API_KEY set. Pass a homepage URL directly."}]
    r = httpx.post(
        "https://api.tavily.com/search",
        json={"api_key": SEARCH_KEY, "query": query,
              "max_results": max_results, "include_answer": False},
        timeout=20,
    )
    r.raise_for_status()
    return [{"title": x.get("title", ""), "url": x.get("url", ""),
             "snippet": x.get("content", "")} for x in r.json().get("results", [])]


def fetch_url(url: str, max_chars: int = 6000) -> str:
    """Download a page and return clean main-content text (truncated)."""
    try:
        import trafilatura
        downloaded = trafilatura.fetch_url(url)
        if downloaded:
            text = trafilatura.extract(downloaded, include_comments=False,
                                       include_tables=False)
            if text:
                return text[:max_chars]
    except Exception:
        pass
    # Fallback: raw text via httpx if trafilatura found nothing (e.g. odd pages)
    try:
        resp = httpx.get(url, timeout=20, follow_redirects=True,
                         headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        import re
        stripped = re.sub(r"<[^>]+>", " ", resp.text)
        return re.sub(r"\s+", " ", stripped)[:max_chars]
    except Exception as e:
        return f"FETCH_ERROR for {url}: {e}"
