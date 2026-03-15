"""Digest builder manager."""

from datetime import datetime, timedelta
from typing import Any

from instruments.custom.knowledge_ingest.knowledge_ingest_db import KnowledgeIngestDatabase
from python.helpers.datetime_utils import utc_now

SECTION_KEYWORDS = {
    "architecture": ["architecture", "infra", "platform", "cloud", "scalability", "system"],
    "tech": ["tech", "ai", "ml", "data", "devops", "security", "api"],
    "business": ["business", "strategy", "market", "finance", "sales", "customer"],
}


class DigestBuilderManager:
    """Creates concise digests from stored items."""

    def __init__(self, db_path: str):
        self.db = KnowledgeIngestDatabase(db_path)

    def build_digest(
        self,
        window_hours: int = 24,
        max_items_per_section: int = 3,
        channel: str = "telegram",
    ) -> dict[str, Any]:
        window_end = utc_now()
        window_start = window_end - timedelta(hours=window_hours)

        items = self.db.list_items(since_hours=window_hours)
        sections = {"architecture": [], "tech": [], "business": []}

        for item in items:
            section = self._categorize(item)
            if len(sections[section]) < max_items_per_section:
                sections[section].append(item)

        summary = self._format_digest(window_start, window_end, sections)
        digest_id = self.db.add_digest(
            window_start=window_start.isoformat(),
            window_end=window_end.isoformat(),
            summary=summary,
            channels=[channel],
        )

        return {
            "status": "ok",
            "digest_id": digest_id,
            "window_start": window_start.isoformat(),
            "window_end": window_end.isoformat(),
            "summary": summary,
        }

    def list_digests(self, limit: int = 10) -> dict[str, Any]:
        return {"digests": self.db.list_digests(limit=limit)}

    def build_architecture_review(
        self,
        context: str,
        options: list[dict[str, Any]],
        decision: str,
        follow_ups: list[str],
        open_questions: list[str],
    ) -> dict[str, Any]:
        lines = ["Architecture Decision Record", "", "Context", context or "N/A", "", "Options"]
        if not options:
            lines.append("- N/A")
        for option in options:
            title = option.get("title") or "Option"
            tradeoffs = option.get("tradeoffs") or []
            lines.append(f"- {title}")
            for tradeoff in tradeoffs:
                lines.append(f"  - {tradeoff}")
        lines.extend(["", "Decision", decision or "TBD", "", "Follow-up Actions"])
        if follow_ups:
            for action in follow_ups:
                lines.append(f"- {action}")
        else:
            lines.append("- TBD")
        lines.extend(["", "Open Questions"])
        if open_questions:
            for question in open_questions:
                lines.append(f"- {question}")
        else:
            lines.append("- None")
        return {"status": "ok", "adr": "\n".join(lines)}

    def _categorize(self, item: dict[str, Any]) -> str:
        tags = {tag.lower() for tag in item.get("tags", [])}
        if tags:
            for section, keywords in SECTION_KEYWORDS.items():
                if tags.intersection(keywords):
                    return section
        content = f"{item.get('title', '')} {item.get('content', '')}".lower()
        for section, keywords in SECTION_KEYWORDS.items():
            if any(keyword in content for keyword in keywords):
                return section
        return "tech"

    def _format_digest(
        self,
        window_start: datetime,
        window_end: datetime,
        sections: dict[str, list[dict[str, Any]]],
    ) -> str:
        header = f"Daily Architecture + Tech + Business Digest ({window_start.strftime('%Y-%m-%d')})"
        lines = [header, ""]
        for section in ["architecture", "tech", "business"]:
            items = sections.get(section, [])
            title = f"{section.title()} Signals"
            lines.append(title)
            if not items:
                lines.append("- No notable items in this window")
            for item in items:
                link = f" ({item['url']})" if item.get("url") else ""
                tags = ", ".join(item.get("tags") or [])
                tag_suffix = f" [{tags}]" if tags else ""
                lines.append(f"- {item.get('title', 'Untitled')}{link}{tag_suffix}")
            lines.append("")
        lines.append("Action prompts")
        lines.append("- Review the top items and decide on follow-up research")
        lines.append("- Capture any decisions into memory")
        return "\n".join(lines).strip()
