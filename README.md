# PaperRadar 🛰️📄

An **MCP server** that pulls the **latest papers in your field** into Claude (or any MCP client).

Ask your assistant:

> *"What's new in cyanobacteria pigment research this week? Summarize the top 5."*

…and it fetches recent papers (journals **and** preprints) from **Europe PMC**, newest first, so the model can summarize / compare them. The reasoning runs on **your** Claude/ChatGPT — PaperRadar just fetches and structures the data. **No API key. No account. Free.**

Built in a weekend (~1.5 days) as a *#weekendbuild*.

## What it gives Claude

One tool:

- **`search_recent_papers(query, days=7, limit=20)`** — latest papers matching `query`, first-published within the last `days`. Returns `title, authors, date, source, doi, url, abstract`.

## Install

```bash
# with uv (recommended)
uv tool install paper-radar        # or: uv run --from . paper-radar
# or with pip
pip install paper-radar
```

Or run from source:

```bash
git clone https://github.com/nagidev-lab/paper-radar && cd paper-radar
uv run paper-radar     # (or: pip install -e . && paper-radar)
```

## Add to Claude

**Claude Desktop** — add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "paper-radar": { "command": "uvx", "args": ["paper-radar"] }
  }
}
```

**Claude Code** — `claude mcp add paper-radar -- uvx paper-radar`

Then just ask: *"what's new in <topic> this week?"*

## How it works

- Data: [Europe PMC](https://europepmc.org/) REST API (covers PubMed + preprints such as bioRxiv). No auth.
- Date filter + newest-first sort done server-side; the model does the summarizing/comparing.
- Titles/abstracts are stripped of HTML entities before returning.

## Roadmap (maybe)

- more sources (arXiv, direct bioRxiv), per-paper detail, saved topics, a hosted version.

---

MIT. A weekend build — feedback welcome.
