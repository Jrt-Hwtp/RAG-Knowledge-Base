"""Load documents from Atlassian (Confluence + Jira) and .md files, then run simple RAG retrieval.

Install:  uv add requests python-dotenv beautifulsoup4 scikit-learn
Usage:
    python rag_loader.py "what does the login system use?"
    python rag_loader.py "query" --md-dir . --confluence-space DEV --jira-jql "project = DEV"
"""
import argparse
import os
import re
from dataclasses import dataclass, field
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


@dataclass
class Document:
    text: str
    source: str
    metadata: dict = field(default_factory=dict)


# ---------- Atlassian ----------
class AtlassianClient:
    def __init__(self):
        load_dotenv()
        self.base = os.environ["ATLASSIAN_URL"].strip().rstrip("/")
        self.session = requests.Session()
        self.session.auth = (
            os.environ["ATLASSIAN_USERNAME"].strip(),
            os.environ["ATLASSIAN_API_TOKEN"].strip(),
        )
        self.session.headers["Accept"] = "application/json"

    @staticmethod
    def _html_to_text(html: str) -> str:
        return BeautifulSoup(html or "", "html.parser").get_text("\n", strip=True)

    def load_confluence(self, space_key: str | None = None, limit: int = 50) -> list[Document]:
        docs, start = [], 0
        url = f"{self.base}/wiki/rest/api/content"
        while True:
            params = {"type": "page", "expand": "body.storage", "limit": limit, "start": start}
            if space_key:
                params["spaceKey"] = space_key
            r = self.session.get(url, params=params, timeout=30)
            r.raise_for_status()
            data = r.json()
            for p in data.get("results", []):
                text = self._html_to_text(p["body"]["storage"]["value"])
                if text:
                    docs.append(Document(
                        text=f"{p['title']}\n{text}",
                        source=f"{self.base}/wiki{p['_links']['webui']}",
                        metadata={"type": "confluence", "title": p["title"]},
                    ))
            if "next" not in data.get("_links", {}):
                break
            start += limit
        return docs

    def load_jira(self, jql: str = "order by created DESC", max_results: int = 100) -> list[Document]:
        r = self.session.get(
            f"{self.base}/rest/api/3/search/jql",
            params={"jql": jql, "maxResults": max_results, "fields": "summary,description,status"},
            timeout=30,
        )
        r.raise_for_status()
        docs = []
        for i in r.json().get("issues", []):
            f = i["fields"]
            desc = self._adf_to_text(f.get("description"))
            docs.append(Document(
                text=f"{i['key']}: {f['summary']}\n{desc}",
                source=f"{self.base}/browse/{i['key']}",
                metadata={"type": "jira", "key": i["key"], "status": (f.get("status") or {}).get("name")},
            ))
        return docs

    def _adf_to_text(self, node) -> str:
        """Convert Atlassian Document Format to plain text"""
        if not node:
            return ""
        if isinstance(node, dict):
            if node.get("type") == "text":
                return node.get("text", "")
            return " ".join(self._adf_to_text(c) for c in node.get("content", []))
        return " ".join(self._adf_to_text(c) for c in node)


# ---------- Markdown ----------
def load_markdown(directory: str) -> list[Document]:
    docs = []
    for path in Path(directory).rglob("*.md"):
        if ".git" in path.parts or ".venv" in path.parts:
            continue
        if path.name.lower() == "readme.md":
            continue
        text = path.read_text(encoding="utf-8", errors="ignore").strip()
        if text:
            docs.append(Document(text=text, source=str(path), metadata={"type": "markdown"}))
    return docs


# ---------- Chunk + Retrieve ----------
def chunk(docs: list[Document], size: int = 800) -> list[Document]:
    chunks = []
    for d in docs:
        paragraphs = re.split(r"\n\s*\n|\n(?=#)", d.text)
        buf = ""
        for p in paragraphs:
            if buf and len(buf) + len(p) > size:
                chunks.append(Document(buf.strip(), d.source, d.metadata))
                buf = ""
            buf += p + "\n\n"
        if buf.strip():
            chunks.append(Document(buf.strip(), d.source, d.metadata))
    return chunks


class Retriever:
    def __init__(self, chunks: list[Document]):
        self.chunks = chunks
        # char n-grams work for languages like Thai that have no spaces between words
        self.vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4))
        self.matrix = self.vec.fit_transform([c.text for c in chunks])

    def search(self, query: str, k: int = 3):
        scores = cosine_similarity(self.vec.transform([query]), self.matrix)[0]
        top = scores.argsort()[::-1][:k]
        return [(self.chunks[i], float(scores[i])) for i in top]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("query")
    ap.add_argument("--md-dir", default=".")
    ap.add_argument("--confluence-space")
    ap.add_argument("--jira-jql", default="order by created DESC")
    ap.add_argument("--no-atlassian", action="store_true")
    ap.add_argument("-k", type=int, default=3)
    a = ap.parse_args()

    docs = load_markdown(a.md_dir)
    if not a.no_atlassian:
        try:
            client = AtlassianClient()
            docs += client.load_confluence(a.confluence_space)
            docs += client.load_jira(a.jira_jql)
        except Exception as e:  # still allow .md files if Atlassian is unreachable
            print(f"[warn] Failed to load Atlassian: {e}")

    print(f"Loaded {len(docs)} documents")
    retriever = Retriever(chunk(docs))
    for c, score in retriever.search(a.query, a.k):
        print(f"\n--- {score:.3f} | {c.source}\n{c.text[:500]}")


if __name__ == "__main__":
    main()
