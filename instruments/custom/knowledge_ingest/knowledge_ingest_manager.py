"""Manager for ingesting and storing knowledge sources."""

import hashlib
import json
import os
import re
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any

from bs4 import BeautifulSoup

from python.helpers import files
from python.helpers.datetime_utils import isoformat_z, utc_now

from .knowledge_ingest_db import KnowledgeIngestDatabase


class KnowledgeIngestManager:
    """Orchestrates ingestion of RSS, web pages, and direct text."""

    def __init__(self, db_path: str):
        self.db = KnowledgeIngestDatabase(db_path)

    def register_source(
        self,
        name: str,
        source_type: str,
        uri: str,
        tags: list[str] | None = None,
        cadence: str | None = None,
        config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if not name or not source_type or not uri:
            return {"error": "name, source_type, and uri are required"}

        existing = self.db.find_source(name, uri)
        if existing:
            return {"status": "exists", "source_id": existing}

        source_id = self.db.add_source(
            name,
            source_type,
            uri,
            tags=tags,
            cadence=cadence,
            config=config,
        )
        return {"status": "registered", "source_id": source_id}

    def list_sources(self) -> dict[str, Any]:
        return {"sources": self.db.list_sources()}

    def ingest_source(self, source_id: int, max_items: int = 10) -> dict[str, Any]:
        source = self.db.get_source(source_id)
        if not source:
            return {"error": f"source_id {source_id} not found"}

        try:
            if source["type"] == "rss":
                items = self._fetch_rss(source["uri"], max_items)
            elif source["type"] == "url":
                items = [self._fetch_web_page(source["uri"], source["name"])]
            elif source["type"] == "mcp":
                return {"error": "mcp sources require tool-driven ingestion"}
            else:
                return {"error": f"unsupported source type: {source['type']}"}

            added = self._store_items(source, items)
            self.db.record_ingestion(source_id, "ok", added)
            return {"status": "ok", "source_id": source_id, "items_added": added}
        except Exception as exc:
            self.db.record_ingestion(source_id, "error", 0, error=str(exc))
            return {"error": str(exc)}

    def ingest_all(self, max_items_per_source: int = 10) -> dict[str, Any]:
        results = []
        for source in self.db.list_sources():
            result = self.ingest_source(source["id"], max_items=max_items_per_source)
            results.append(result)
        return {"status": "ok", "results": results}

    def store_external_items(self, source: dict[str, Any], items: list[dict[str, Any]]) -> dict[str, Any]:
        added = self._store_items(source, items)
        self.db.record_ingestion(source["id"], "ok", added)
        return {"status": "ok", "source_id": source["id"], "items_added": added}

    def store_mcp_payload(self, source: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
        items = self._items_from_mcp_payload(payload, source)
        if not items:
            return {"error": "no items extracted from mcp payload"}
        return self.store_external_items(source, items)

    def ingest_text(
        self,
        title: str,
        content: str,
        tags: list[str] | None = None,
        confidence: float = 0.7,
    ) -> dict[str, Any]:
        if not title or not content:
            return {"error": "title and content are required"}

        source = {
            "id": 0,
            "name": "manual",
            "type": "text",
            "uri": "manual",
            "tags": tags or [],
        }
        item = {
            "title": title,
            "url": None,
            "published_at": isoformat_z(utc_now()),
            "content": content,
            "tags": tags or [],
            "confidence": confidence,
        }
        added = self._store_items(source, [item])
        return {"status": "ok", "items_added": added}

    def _fetch_rss(self, uri: str, max_items: int) -> list[dict[str, Any]]:
        xml = self._fetch_url(uri)
        root = ET.fromstring(xml)  # nosec B314 - parsing controlled XML input
        channel = root.find("channel") or root
        items = []
        for item in channel.findall("item")[:max_items]:
            title = self._get_xml_text(item, "title")
            link = self._get_xml_text(item, "link")
            pub_date = self._get_xml_text(item, "pubDate")
            description = self._get_xml_text(item, "description")
            if not title:
                continue
            items.append(
                {
                    "title": title,
                    "url": link,
                    "published_at": pub_date,
                    "content": self._normalize_text(description),
                    "tags": [],
                    "confidence": 0.6,
                }
            )
        return items

    def _fetch_web_page(self, uri: str, title_hint: str) -> dict[str, Any]:
        html = self._fetch_url(uri)
        soup = BeautifulSoup(html, "html.parser")
        title = soup.title.string.strip() if soup.title and soup.title.string else title_hint
        text = " ".join(p.get_text(" ", strip=True) for p in soup.find_all("p"))
        return {
            "title": title,
            "url": uri,
            "published_at": None,
            "content": self._normalize_text(text),
            "tags": [],
            "confidence": 0.5,
        }

    def _fetch_url(self, uri: str) -> str:
        request = urllib.request.Request(uri, headers={"User-Agent": "AgentZero/1.0"})
        with urllib.request.urlopen(request, timeout=20) as response:  # nosec B310 - URL from controlled config
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="ignore")

    def _items_from_mcp_payload(self, payload: dict[str, Any], source: dict[str, Any]) -> list[dict[str, Any]]:
        structured = payload.get("structuredContent") or {}
        items = []
        candidates = structured.get("results") or structured.get("items") or structured.get("data") or []
        for entry in candidates:
            title = entry.get("title") or entry.get("name") or source.get("name")
            url = entry.get("url") or entry.get("link")
            content = entry.get("description") or entry.get("summary") or json.dumps(entry)
            items.append(
                {
                    "title": title,
                    "url": url,
                    "published_at": None,
                    "content": self._normalize_text(content),
                    "tags": source.get("tags", []),
                    "confidence": 0.5,
                }
            )

        if items:
            return items

        content_blocks = payload.get("content") or []
        text_parts = []
        for block in content_blocks:
            if isinstance(block, dict) and block.get("type") == "text":
                text_parts.append(block.get("text", ""))
        if text_parts:
            return [
                {
                    "title": source.get("name", "MCP Result"),
                    "url": source.get("uri"),
                    "published_at": None,
                    "content": self._normalize_text("\n".join(text_parts)),
                    "tags": source.get("tags", []),
                    "confidence": 0.4,
                }
            ]

        return []

    def _store_items(self, source: dict[str, Any], items: list[dict[str, Any]]) -> int:
        added = 0
        for item in items:
            content = item.get("content") or ""
            content_hash = self._hash_text(item.get("title", "") + content)
            tags = self._merge_tags(source.get("tags", []), item.get("tags", []))
            stored = self.db.add_item(
                source_id=source["id"],
                title=item.get("title", "untitled"),
                url=item.get("url"),
                published_at=item.get("published_at"),
                content=content,
                content_hash=content_hash,
                tags=tags,
                confidence=float(item.get("confidence", 0.5)),
            )
            if stored:
                self._write_knowledge_item(source, item, content_hash, tags)
                added += 1
        return added

    def _write_knowledge_item(
        self,
        source: dict[str, Any],
        item: dict[str, Any],
        content_hash: str,
        tags: list[str],
    ) -> None:
        subdir = os.getenv("AGENT_KNOWLEDGE_SUBDIR", "custom")
        try:
            from python.helpers import settings as settings_module

            subdir = settings_module.get_settings().get("agent_knowledge_subdir", subdir)
        except Exception:
            pass
        date_stamp = utc_now().strftime("%Y%m%d")
        safe_name = self._slugify(source["name"])
        rel_path = f"knowledge/{subdir}/ingest/{safe_name}/{date_stamp}-{content_hash}.md"
        payload = [
            f"# {item.get('title', 'Untitled')}",
            f"source: {source.get('uri')}",
            f"tags: {', '.join(tags)}",
            f"confidence: {item.get('confidence', 0.5)}",
            "",
            item.get("content", ""),
        ]
        files.write_file(rel_path, "\n".join(payload))

    def _get_xml_text(self, parent: ET.Element, tag: str) -> str:
        element = parent.find(tag)
        if element is None or element.text is None:
            return ""
        return element.text.strip()

    def _hash_text(self, text: str) -> str:
        return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()[:16]

    def _merge_tags(self, source_tags: list[str], item_tags: list[str]) -> list[str]:
        merged = {tag.strip() for tag in source_tags + item_tags if tag and tag.strip()}
        return sorted(merged)

    def _normalize_text(self, text: str) -> str:
        text = re.sub(r"\s+", " ", text or "").strip()
        return text

    def _slugify(self, value: str) -> str:
        value = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip()).strip("-")
        return value.lower() or "source"
