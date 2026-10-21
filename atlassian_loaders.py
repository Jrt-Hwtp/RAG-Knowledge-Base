import requests
from bs4 import BeautifulSoup
from langchain_core.document_loaders import BaseLoader
from langchain_core.documents import Document


class ConfluenceLoader(BaseLoader):
    """Loader สำหรับดึงหน้า Confluence ผ่าน REST API"""

    def __init__(self, url: str, username: str, api_key: str, space_key: str | None = None, limit: int = 50):
        self.url = url.rstrip("/")
        self.username = username
        self.api_key = api_key
        self.space_key = space_key
        self.limit = limit

    def load(self) -> list[Document]:
        docs, start = [], 0
        endpoint = f"{self.url}/wiki/rest/api/content"
        while True:
            params = {"type": "page", "expand": "body.storage", "limit": self.limit, "start": start}
            if self.space_key:
                params["spaceKey"] = self.space_key
            try:
                r = requests.get(endpoint, auth=(self.username, self.api_key), params=params, timeout=30)
                r.raise_for_status()
                data = r.json()
            except Exception as e:
                print(f"[warn] Confluence load warning: {e}")
                break

            results = data.get("results", [])
            for p in results:
                html = p.get("body", {}).get("storage", {}).get("value", "")
                text = BeautifulSoup(html, "html.parser").get_text("\n", strip=True)
                title = p.get("title", "")
                webui = p.get("_links", {}).get("webui", "")
                docs.append(
                    Document(
                        page_content=f"{title}\n{text}".strip(),
                        metadata={"source": f"{self.url}/wiki{webui}", "type": "confluence", "title": title},
                    )
                )

            if "next" not in data.get("_links", {}) or len(results) == 0:
                break
            start += self.limit
        return docs


class JiraLoader(BaseLoader):
    """Loader สำหรับดึง Jira Issues ผ่าน REST API (JQL)"""

    def __init__(self, url: str, username: str, api_key: str, jql: str = "", limit: int = 50):
        self.url = url.rstrip("/")
        self.username = username
        self.api_key = api_key
        self.jql = jql
        self.limit = limit

    @staticmethod
    def _adf_to_text(node) -> str:
        if not node:
            return ""
        if isinstance(node, dict):
            if node.get("type") == "text":
                return node.get("text", "")
            return " ".join(JiraLoader._adf_to_text(c) for c in node.get("content", []))
        return " ".join(JiraLoader._adf_to_text(c) for c in node)

    def load(self) -> list[Document]:
        params = {"fields": "summary,description,status", "maxResults": self.limit}
        if self.jql:
            params["jql"] = self.jql
        try:
            r = requests.get(
                f"{self.url}/rest/api/3/search/jql",
                auth=(self.username, self.api_key),
                params=params,
                timeout=30,
            )
            r.raise_for_status()
            issues = r.json().get("issues", [])
        except Exception as e:
            print(f"[warn] Jira load warning: {e}")
            return []

        docs = []
        for i in issues:
            f = i.get("fields", {})
            key = i.get("key", i.get("id", ""))
            desc = self._adf_to_text(f.get("description"))
            status = (f.get("status") or {}).get("name", "")
            text = f"Jira Issue {key}: {f.get('summary', '')}\nStatus: {status}\n{desc}".strip()
            docs.append(
                Document(
                    page_content=text,
                    metadata={"source": f"{self.url}/browse/{key}", "type": "jira", "key": key, "status": status},
                )
            )
        return docs
