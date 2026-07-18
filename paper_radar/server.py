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


def _url_for(it: dict) -> str:
    doi = it.get("doi")
    if doi:
        return f"https://doi.org/{doi}"
    src, pid = it.get("source"), it.get("id")
    if src and pid:
        return f"https://europepmc.org/article/{src}/{pid}"
    return ""


def fetch_recent_papers(query: str, days: int = 7, limit: int = 20) -> dict:
    """Core fetch logic (kept separate from the MCP tool so it's easy to test).

    Returns a dict: {query, date_range, count, papers, [error]} so the caller can
    tell "zero hits" from "bad query / fetch failed".
    """
    query = (query or "").strip()
    if not query:
        return {"error": "Empty query. Provide search terms, e.g. 'CRISPR base editing'.",
                "query": "", "count": 0, "papers": []}
    try:
        days = max(1, int(days))
        limit = min(max(1, int(limit)), 100)
    except (TypeError, ValueError):
        return {"error": "days and limit must be integers.",
                "query": query, "count": 0, "papers": []}

    since = (date.today() - timedelta(days=days - 1)).isoformat()
    today = date.today().isoformat()
    epmc_q = f"({query}) AND (FIRST_PDATE:[{since} TO {today}])"
    meta = {"query": epmc_q, "date_range": [since, today]}
    params = {
        "query": epmc_q, "format": "json", "pageSize": limit,
        "sort": "P_PDATE_D desc",  # publication date, newest first
        "resultType": "core",      # includes abstractText
    }
    try:
        r = httpx.get(EUROPE_PMC, params=params, timeout=30, headers={"User-Agent": UA})
        r.raise_for_status()
        data = r.json()
    except httpx.HTTPStatusError as e:
        return {**meta, "error": f"Europe PMC returned HTTP {e.response.status_code}. Try simpler keywords.",
                "count": 0, "papers": []}
    except httpx.RequestError as e:
        return {**meta, "error": f"Could not reach Europe PMC ({e.__class__.__name__}).",
                "count": 0, "papers": []}
    except ValueError:
        return {**meta, "error": "Europe PMC returned an unexpected (non-JSON) response.",
                "count": 0, "papers": []}

    papers = []
    for it in data.get("resultList", {}).get("result", [])[:limit]:
        papers.append({
            "title": _clean(it.get("title")),
            "authors": _clean(it.get("authorString")),
            "date": it.get("firstPublicationDate") or str(it.get("pubYear", "")),
            "source": it.get("source", ""),
            "doi": it.get("doi"),
            "url": _url_for(it),
            "abstract": _clean(it.get("abstractText")),
        })
    return {**meta, "count": len(papers), "papers": papers}


@mcp.tool()
def search_recent_papers(query: str, days: int = 7, limit: int = 20) -> dict:
    """Search the latest scientific papers (journals + preprints), newest first.

    Args:
        query: search terms, e.g. "cyanobacteria pigment" or "CRISPR base editing".
        days: only include papers first-published within the last N days (default 7).
        limit: max number of papers to return (default 20, max 100).

    Returns:
        A dict: {query, date_range, count, papers, [error]}. Each paper has
        title, authors, date, source, doi, url, abstract.
        Data source: Europe PMC (PubMed + preprints like bioRxiv). No API key needed.
        If `error` is present, no papers were fetched (bad query or fetch failure).
    """
    return fetch_recent_papers(query, days, limit)


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
