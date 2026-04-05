import os

from instruments.custom.digest_builder.digest_builder_manager import DigestBuilderManager
from instruments.custom.knowledge_ingest.knowledge_ingest_db import KnowledgeIngestDatabase


def _seed_items(db: KnowledgeIngestDatabase, source_id: int, items: list[dict]) -> None:
    """Helper to insert multiple items."""
    for i, item in enumerate(items):
        db.add_item(
            source_id=source_id,
            title=item.get("title", f"Item {i}"),
            url=item.get("url", f"https://example.com/{i}"),
            published_at=item.get("published_at", "2024-01-01"),
            content=item.get("content", ""),
            content_hash=f"hash_{i}",
            tags=item.get("tags", ["tech"]),
            confidence=item.get("confidence", 0.9),
        )


def test_digest_builder_creates_summary(tmp_path):
    db_path = os.path.join(tmp_path, "knowledge_ingest.db")
    db = KnowledgeIngestDatabase(db_path)
    source_id = db.add_source(
        name="Test Source",
        source_type="rss",
        uri="https://example.com/rss",
        tags=["tech"],
        cadence="daily",
    )

    db.add_item(
        source_id=source_id,
        title="AI platform update",
        url="https://example.com/ai",
        published_at="2024-01-01",
        content="New AI infrastructure release",
        content_hash="hash1",
        tags=["tech"],
        confidence=0.9,
    )

    manager = DigestBuilderManager(db_path)
    result = manager.build_digest(window_hours=24)

    assert result["status"] == "ok"
    assert "Digest" in result["summary"]
    digests = manager.list_digests(limit=1)
    assert len(digests["digests"]) == 1


def test_digest_empty_window(tmp_path):
    """Digest with no items should still produce a valid summary."""
    db_path = os.path.join(tmp_path, "knowledge_ingest.db")
    KnowledgeIngestDatabase(db_path)  # init schema

    manager = DigestBuilderManager(db_path)
    result = manager.build_digest(window_hours=24)

    assert result["status"] == "ok"
    assert result["digest_id"] is not None
    assert "No notable items" in result["summary"]


def test_digest_respects_max_items_per_section(tmp_path):
    """Each section should be capped at max_items_per_section."""
    db_path = os.path.join(tmp_path, "knowledge_ingest.db")
    db = KnowledgeIngestDatabase(db_path)
    source_id = db.add_source(
        name="Tech Feed",
        source_type="rss",
        uri="https://example.com/rss",
        tags=["tech"],
        cadence="daily",
    )

    _seed_items(
        db, source_id, [{"title": f"AI Article {i}", "tags": ["tech"], "content": "tech ai ml"} for i in range(10)]
    )

    manager = DigestBuilderManager(db_path)
    result = manager.build_digest(window_hours=24, max_items_per_section=2)

    assert result["status"] == "ok"
    # Count "AI Article" occurrences in summary — should be <= 2
    count = result["summary"].count("AI Article")
    assert count <= 2


def test_digest_categorizes_by_tags(tmp_path):
    """Items with architecture/business/tech tags go to correct sections."""
    db_path = os.path.join(tmp_path, "knowledge_ingest.db")
    db = KnowledgeIngestDatabase(db_path)
    source_id = db.add_source(
        name="Mixed Feed",
        source_type="rss",
        uri="https://example.com/rss",
        tags=[],
        cadence="daily",
    )

    _seed_items(
        db,
        source_id,
        [
            {"title": "Cloud Migration", "tags": ["architecture", "cloud"], "content": "infrastructure"},
            {"title": "Sales Growth", "tags": ["business", "sales"], "content": "market strategy"},
            {"title": "ML Pipeline", "tags": ["tech", "ml"], "content": "data processing"},
        ],
    )

    manager = DigestBuilderManager(db_path)
    result = manager.build_digest(window_hours=24)

    summary = result["summary"]
    assert "Architecture Signals" in summary
    assert "Business Signals" in summary
    assert "Tech Signals" in summary
    assert "Cloud Migration" in summary
    assert "Sales Growth" in summary
    assert "ML Pipeline" in summary


def test_digest_categorizes_by_content_fallback(tmp_path):
    """Items without matching tags fall back to content-based categorization."""
    db_path = os.path.join(tmp_path, "knowledge_ingest.db")
    db = KnowledgeIngestDatabase(db_path)
    source_id = db.add_source(
        name="Feed",
        source_type="rss",
        uri="https://example.com/rss",
        tags=[],
        cadence="daily",
    )

    _seed_items(
        db,
        source_id,
        [
            {"title": "Platform Scaling", "tags": [], "content": "cloud infrastructure scalability"},
        ],
    )

    manager = DigestBuilderManager(db_path)
    result = manager.build_digest(window_hours=24)

    assert "Platform Scaling" in result["summary"]


def test_list_digests_returns_multiple(tmp_path):
    """list_digests should return multiple digests in order."""
    db_path = os.path.join(tmp_path, "knowledge_ingest.db")
    KnowledgeIngestDatabase(db_path)

    manager = DigestBuilderManager(db_path)
    manager.build_digest(window_hours=24)
    manager.build_digest(window_hours=48)

    digests = manager.list_digests(limit=10)
    assert len(digests["digests"]) == 2


def test_list_digests_respects_limit(tmp_path):
    """list_digests limit parameter should cap results."""
    db_path = os.path.join(tmp_path, "knowledge_ingest.db")
    KnowledgeIngestDatabase(db_path)

    manager = DigestBuilderManager(db_path)
    for _ in range(5):
        manager.build_digest(window_hours=24)

    digests = manager.list_digests(limit=2)
    assert len(digests["digests"]) == 2


def test_build_architecture_review_basic(tmp_path):
    """Architecture review should produce structured ADR content."""
    db_path = os.path.join(tmp_path, "knowledge_ingest.db")
    manager = DigestBuilderManager(db_path)

    result = manager.build_architecture_review(
        context="Choosing a message queue for async processing",
        options=[
            {"title": "Redis Streams", "tradeoffs": ["Simple", "Limited durability"]},
            {"title": "RabbitMQ", "tradeoffs": ["Mature", "More ops overhead"]},
        ],
        decision="Redis Streams for MVP",
        follow_ups=["Set up dead letter queue", "Add monitoring"],
        open_questions=["What about backpressure handling?"],
    )

    assert result["status"] == "ok"
    adr = result["adr"]
    assert "Architecture Decision Record" in adr
    assert "Redis Streams" in adr
    assert "RabbitMQ" in adr
    assert "Redis Streams for MVP" in adr
    assert "dead letter queue" in adr
    assert "backpressure" in adr


def test_build_architecture_review_empty_options(tmp_path):
    """Architecture review with no options should not crash."""
    db_path = os.path.join(tmp_path, "knowledge_ingest.db")
    manager = DigestBuilderManager(db_path)

    result = manager.build_architecture_review(
        context="",
        options=[],
        decision="",
        follow_ups=[],
        open_questions=[],
    )

    assert result["status"] == "ok"
    assert "N/A" in result["adr"]
    assert "TBD" in result["adr"]


def test_digest_includes_action_prompts(tmp_path):
    """Every digest should end with action prompts."""
    db_path = os.path.join(tmp_path, "knowledge_ingest.db")
    KnowledgeIngestDatabase(db_path)

    manager = DigestBuilderManager(db_path)
    result = manager.build_digest(window_hours=24)

    assert "Action prompts" in result["summary"]
    assert "follow-up research" in result["summary"]


def test_digest_summary_includes_date(tmp_path):
    """Digest summary header should include the date."""
    db_path = os.path.join(tmp_path, "knowledge_ingest.db")
    KnowledgeIngestDatabase(db_path)

    manager = DigestBuilderManager(db_path)
    result = manager.build_digest(window_hours=24)

    # Should contain a date pattern like 2026-04-05
    import re

    assert re.search(r"\d{4}-\d{2}-\d{2}", result["summary"])
