# RAG-Knowledge-Base

A simple command-line RAG (retrieval) tool that searches team knowledge across Confluence, Jira, and local Markdown files. It does not call an LLM: it loads documents, splits them into chunks, and returns the chunks most similar to your query.

## How it works

1. **Load** documents from:
   - Confluence pages (HTML converted to text with BeautifulSoup)
   - Jira issues (Atlassian Document Format converted to text)
   - Local `.md` files (recursive, `.git` skipped)
2. **Chunk** each document by paragraph/heading, around 800 characters per chunk.
3. **Retrieve** with TF-IDF over character n-grams (2-4) and cosine similarity. Character n-grams work for languages without spaces between words, such as Thai.
4. **Print** the top-k chunks with their score and source (URL or file path).

Matching is lexical, not semantic, so it works best when the query shares keywords with the documents.

## Setup

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

Create a `.env` file (already git-ignored) for Atlassian access:

```env
ATLASSIAN_URL=https://your-domain.atlassian.net
ATLASSIAN_USERNAME=you@example.com
ATLASSIAN_API_TOKEN=your-api-token
```

## Usage

```bash
# Markdown files only (no Atlassian credentials needed)
uv run python rag_loader.py "what does the login system use?" --no-atlassian

# All sources
uv run python rag_loader.py "what does the login system use?"

# Custom Confluence space, JQL, Markdown folder, and number of results
uv run python rag_loader.py "query" --confluence-space DEV --jira-jql "project = DEV" --md-dir . -k 5
```

| Option | Default | Description |
| --- | --- | --- |
| `query` | required | Search text |
| `--md-dir` | `.` | Folder scanned for `.md` files |
| `--confluence-space` | all spaces | Confluence space key |
| `--jira-jql` | `order by created DESC` | JQL used to select issues |
| `--no-atlassian` | off | Skip Confluence and Jira |
| `-k` | `3` | Number of results |

## Reading the output

```
Loaded 12 documents

--- 0.482 | https://your-domain.atlassian.net/wiki/spaces/DEV/pages/123
<first 500 characters of the matching chunk>
```

Each result shows `--- <score> | <source>` followed by the chunk text. The score is cosine similarity: the closer to 1, the better the match. If Atlassian cannot be reached, a `[warn]` line is printed and the search continues with Markdown files.

## Project layout

| File | Purpose |
| --- | --- |
| `rag_loader.py` | Loaders, chunking, retriever, and CLI |
| `architecture.md` | Sample system architecture document used as search content |
| `pyproject.toml`, `uv.lock` | Dependencies managed by uv |