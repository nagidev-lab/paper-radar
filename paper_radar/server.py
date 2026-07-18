"""PaperRadar — an MCP server that fetches the latest papers in your field.

Ask Claude "what's new in <topic> this week?" and it pulls recent papers
(journals + preprints) from Europe PMC, newest first. Inference runs on your
own Claude/ChatGPT; PaperRadar just fetches and structures the data.
"""
from __future__ import annotations

import html
import re
from datetime import date, timedelta

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("PaperRadar")

EUROPE_PMC = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
UA = "PaperRadar/0.1 (MCP; https://github.com/nagidev-lab/paper-radar)"


def _clean(s: str | None) -> str:
    """Strip HTML tags/entities that Europe PMC returns in titles/abstracts."""
    if not s:
        return ""
    s = html.unescape(s)          # &lt;sub&gt; -> <sub>  (unescape first)
    s = re.sub(r"<[^>]+>", "", s)  # then strip tags
    return s.strip()


def fetch_recent_papers(query: str, days: int = 7, limit: int = 20) -> list[dict]:
    """Core fetch logic (kept separate from the MCP tool so it's easy to test)."""
    days = max(1, int(days))
    limit = min(max(1, int(limit)), 100)
    since = (date.today() - timedelta(days=days)).isoformat()
    today = date.today().isoformat()
    q = f"({query}) AND (FIRST_PDATE:[{since} TO {today}])"
    params = {
        "query": q,
        "format": "json",
        "pageSize": limit,
        "sort": "P_PDATE_D desc",  # publication date, newest first
        "resultType": "core",      # includes abstractText
    }
    r = httpx.get(EUROPE_PMC, params=params, timeout=30, headers={"User-Agent": UA})
    r.raise_for_status()
    results = r.json().get("resultList", {}).get("result", [])
    out: list[dict] = []
    for it in results[:limit]:
        doi = it.get("doi")
        url = (
            f"https://doi.org/{doi}"
            if doi
            else f"https://europepmc.org/article/{it.get('source', 'MED')}/{it.get('id', '')}"
        )
        out.append(
            {
                "title": _clean(it.get("title")),
                "authors": _clean(it.get("authorString")),
                "date": it.get("firstPublicationDate") or str(it.get("pubYear", "")),
                "source": it.get("source", ""),
                "doi": doi,
                "url": url,
                "abstract": _clean(it.get("abstractText")),
            }
        )
    return out


@mcp.tool()
def search_recent_papers(query: str, days: int = 7, limit: int = 20) -> list[dict]:
    """Search the latest scientific papers (journals + preprints), newest first.

    Args:
        query: search terms, e.g. "cyanobacteria pigment" or "CRISPR base editing".
        days: only include papers first-published within the last N days (default 7).
        limit: max number of papers to return (default 20, max 100).

    Returns:
        A list of papers, each with: title, authors, date, source, doi, url, abstract.
        Data source: Europe PMC (covers PubMed + preprints like bioRxiv). No API key needed.
    """
    return fetch_recent_papers(query, days, limit)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
