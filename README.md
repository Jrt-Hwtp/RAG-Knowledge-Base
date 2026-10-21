# RAG-Knowledge-Base

A knowledge retrieval and RAG system that searches team knowledge across Confluence, Jira, and local Markdown files.

The project provides two implementations:
1. **`rag_loader.py`**: Fast, lightweight command-line retrieval tool using TF-IDF and character n-grams without requiring an LLM or GPU.
2. **`enterprise_rag.py`**: Full RAG pipeline powered by LangChain, local Ollama embeddings (`nomic-embed-text`), Chroma vector store, and a local LLM (`gemma4:12b`).

---

## 1. Lightweight Search (`rag_loader.py`)

Searches documents and returns the most relevant chunks using lexical similarity (TF-IDF + cosine similarity).

### How it works
1. **Load**:
   - Confluence pages (HTML converted to text with BeautifulSoup)
   - Jira issues (Atlassian Document Format converted to text)
   - Local `.md` files
2. **Chunk**: Paragraph/heading based chunks (~800 chars).
3. **Retrieve**: TF-IDF over character n-grams (2-4), which works well for non-space-delimited languages such as Thai.
4. **Print**: Top-k matching chunks with similarity score and source URL/filepath.

### Usage

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

---

## 2. Enterprise RAG Pipeline (`enterprise_rag.py`)

A generative Q&A pipeline that indexes documents into a vector database and uses an LLM to formulate grounded answers.

### How it works
1. **Load**: Uses the custom `ConfluenceLoader` and `JiraLoader` from `atlassian_loaders.py`, plus LangChain's `TextLoader` for Markdown. Jira issues are filtered by project and status (`JiraProject` / `JiraStatus` enums).
2. **Chunk**: Splits documents with `RecursiveCharacterTextSplitter` (chunk size: 1000, overlap: 100).
3. **Embed & Index**: Uses `OllamaEmbeddings` (`nomic-embed-text`) stored in a local `Chroma` vector store.
4. **Generate**: Queries a local Ollama LLM (`gemma4:12b`) through an LCEL RAG chain to produce answers in Thai/English grounded in the context.

### Prerequisites for Enterprise RAG
Make sure [Ollama](https://ollama.ai/) is installed and running, then pull the required models:

```bash
ollama pull nomic-embed-text
ollama pull gemma4:12b
```

> **Note:** Embeddings require a dedicated embedding model such as `nomic-embed-text`. Chat models like `gemma4:12b` do not support embeddings (the server returns HTTP 501).

### Usage

```bash
uv run python enterprise_rag.py
```

---

## Setup & Configuration

Requires [uv](https://docs.astral.sh/uv/).

```bash
uv sync
```

Create a `.env` file in the project root with your Atlassian credentials:

```env
ATLASSIAN_URL=https://your-domain.atlassian.net
ATLASSIAN_USERNAME=your-email@example.com
ATLASSIAN_API_TOKEN=your-atlassian-api-token
```

> **Note:** For `enterprise_rag.py`, make sure to adjust `space_key`, `JiraProject`, and `JiraStatus` in the script to match your Confluence space and Jira project keys if needed.

---

## Project Layout

| File | Purpose |
| --- | --- |
| `enterprise_rag.py` | Full LangChain RAG pipeline with Chroma vector database and Ollama (`gemma4:12b` + `nomic-embed-text`) |
| `atlassian_loaders.py` | Confluence and Jira document loaders |
| `rag_loader.py` | Lightweight TF-IDF document loader, chunker, and CLI search tool |
| `architecture.md` | Sample system architecture document used as local Markdown context |
| `.env` | Environment configuration for Atlassian API credentials (git-ignored) |
| `pyproject.toml`, `uv.lock` | Dependencies managed by uv |