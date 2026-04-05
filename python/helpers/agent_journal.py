"""
Agent Work Journal — persistent record of what the agent worked on.

Stored in data/agent_journal.db on the named Docker volume.
Tables: work_sessions, work_journal, operator_goals, chat_messages
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Reuse the canonical DatabaseManager pattern
from python.helpers.db_manager import DatabaseManager
from python.helpers.db_paths import db_path


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _get_db() -> DatabaseManager:
    """Return the shared DatabaseManager instance for agent_journal.db."""
    db_file_path = db_path("agent_journal.db")
    data_dir = str(Path(db_file_path).parent)
    return DatabaseManager("agent_journal.db", data_dir)


_SCHEMA = """
CREATE TABLE IF NOT EXISTS work_sessions (
    id           TEXT PRIMARY KEY,
    project_name TEXT,
    context_id   TEXT NOT NULL,
    started_at   TEXT NOT NULL,
    ended_at     TEXT,
    status       TEXT NOT NULL DEFAULT 'active',
    summary      TEXT,
    input_intent TEXT
);
CREATE INDEX IF NOT EXISTS idx_ws_project ON work_sessions(project_name, started_at);
CREATE INDEX IF NOT EXISTS idx_ws_status  ON work_sessions(status, started_at);

CREATE TABLE IF NOT EXISTS work_journal (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id   TEXT NOT NULL REFERENCES work_sessions(id),
    project_name TEXT,
    context_id   TEXT NOT NULL,
    logged_at    TEXT NOT NULL,
    entry_type   TEXT NOT NULL,
    tool_name    TEXT,
    description  TEXT NOT NULL,
    outcome      TEXT,
    metadata     TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_wj_session ON work_journal(session_id, logged_at);
CREATE INDEX IF NOT EXISTS idx_wj_project ON work_journal(project_name, logged_at);
CREATE INDEX IF NOT EXISTS idx_wj_type    ON work_journal(entry_type, logged_at);

CREATE TABLE IF NOT EXISTS operator_goals (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    project_name TEXT,
    created_at   TEXT NOT NULL,
    updated_at   TEXT NOT NULL,
    status       TEXT NOT NULL DEFAULT 'active',
    title        TEXT NOT NULL,
    description  TEXT NOT NULL,
    priority     INTEGER NOT NULL DEFAULT 5,
    due_date     TEXT,
    metadata     TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS idx_og_project ON operator_goals(project_name, status, priority);

CREATE TABLE IF NOT EXISTS chat_messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id  TEXT NOT NULL REFERENCES work_sessions(id),
    context_id  TEXT NOT NULL,
    message_no  INTEGER NOT NULL,
    role        TEXT NOT NULL,
    content     TEXT NOT NULL,
    tool_name   TEXT,
    posted_at   TEXT NOT NULL,
    tokens      INTEGER
);
CREATE INDEX IF NOT EXISTS idx_cm_session ON chat_messages(session_id, message_no);
CREATE INDEX IF NOT EXISTS idx_cm_context ON chat_messages(context_id, posted_at);
"""


def _ensure_schema(db: DatabaseManager) -> None:
    with db.cursor() as cur:
        cur.executescript(_SCHEMA)


# ── Public API ──────────────────────────────────────────────────────────────


def start_session(context_id: str, project_name: str | None, input_intent: str | None = None) -> str:
    """Open a new work session. Returns the session_id."""
    db = _get_db()
    _ensure_schema(db)
    session_id = str(uuid.uuid4())
    with db.cursor() as cur:
        cur.execute(
            "INSERT OR IGNORE INTO work_sessions (id, project_name, context_id, started_at, input_intent) VALUES (?,?,?,?,?)",
            (session_id, project_name, context_id, _now(), input_intent),
        )
    return session_id


def get_or_create_session(context_id: str, project_name: str | None) -> str:
    """Return existing active session for context_id or create a new one."""
    db = _get_db()
    _ensure_schema(db)
    with db.cursor() as cur:
        cur.execute(
            "SELECT id FROM work_sessions WHERE context_id=? AND status='active' ORDER BY started_at DESC LIMIT 1",
            (context_id,),
        )
        row = cur.fetchone()
        if row:
            return row[0]
    return start_session(context_id, project_name)


def end_session(session_id: str, summary: str | None = None, status: str = "completed") -> None:
    db = _get_db()
    _ensure_schema(db)
    with db.cursor() as cur:
        cur.execute(
            "UPDATE work_sessions SET ended_at=?, status=?, summary=? WHERE id=?",
            (_now(), status, summary, session_id),
        )


def mark_interrupted_sessions(context_id: str) -> int:
    """Mark any still-active sessions for this context as interrupted. Returns count."""
    db = _get_db()
    _ensure_schema(db)
    with db.cursor() as cur:
        cur.execute(
            "UPDATE work_sessions SET status='interrupted', ended_at=? WHERE context_id=? AND status='active'",
            (_now(), context_id),
        )
        return cur.rowcount


def log_entry(
    session_id: str,
    entry_type: str,
    description: str,
    context_id: str = "",
    project_name: str | None = None,
    tool_name: str | None = None,
    outcome: str | None = None,
    metadata: dict | None = None,
) -> None:
    db = _get_db()
    _ensure_schema(db)
    with db.cursor() as cur:
        cur.execute(
            "INSERT INTO work_journal (session_id, project_name, context_id, logged_at, entry_type, tool_name, description, outcome, metadata) VALUES (?,?,?,?,?,?,?,?,?)",
            (
                session_id,
                project_name,
                context_id,
                _now(),
                entry_type,
                tool_name,
                description,
                outcome,
                json.dumps(metadata or {}),
            ),
        )


def log_tool_use(
    session_id: str,
    tool_name: str,
    description: str,
    outcome: str | None = None,
    context_id: str = "",
    project_name: str | None = None,
    metadata: dict | None = None,
) -> None:
    log_entry(
        session_id,
        "tool_use",
        description,
        context_id=context_id,
        project_name=project_name,
        tool_name=tool_name,
        outcome=outcome,
        metadata=metadata,
    )


def log_artifact(
    session_id: str,
    description: str,
    path: str,
    context_id: str = "",
    project_name: str | None = None,
    metadata: dict | None = None,
) -> None:
    log_entry(
        session_id,
        "artifact",
        description,
        context_id=context_id,
        project_name=project_name,
        outcome=path,
        metadata=metadata,
    )


def log_decision(
    session_id: str,
    description: str,
    context_id: str = "",
    project_name: str | None = None,
    metadata: dict | None = None,
) -> None:
    log_entry(session_id, "decision", description, context_id=context_id, project_name=project_name, metadata=metadata)


def get_recent_sessions(project_name: str | None = None, limit: int = 10) -> list[dict]:
    db = _get_db()
    _ensure_schema(db)
    if project_name:
        rows = db.fetch_all(
            "SELECT * FROM work_sessions WHERE project_name=? ORDER BY started_at DESC LIMIT ?",
            (project_name, limit),
        )
    else:
        rows = db.fetch_all(
            "SELECT * FROM work_sessions ORDER BY started_at DESC LIMIT ?",
            (limit,),
        )
    return rows


def get_active_goals(project_name: str | None = None) -> list[dict]:
    db = _get_db()
    _ensure_schema(db)
    if project_name:
        rows = db.fetch_all(
            "SELECT * FROM operator_goals WHERE (project_name=? OR project_name IS NULL) AND status='active' ORDER BY priority ASC",
            (project_name,),
        )
    else:
        rows = db.fetch_all(
            "SELECT * FROM operator_goals WHERE status='active' ORDER BY priority ASC",
        )
    return rows


def upsert_goal(
    title: str, description: str, project_name: str | None = None, priority: int = 5, due_date: str | None = None
) -> int:
    db = _get_db()
    _ensure_schema(db)
    now = _now()
    with db.cursor() as cur:
        cur.execute(
            "INSERT INTO operator_goals (project_name, created_at, updated_at, title, description, priority, due_date) VALUES (?,?,?,?,?,?,?)",
            (project_name, now, now, title, description, priority, due_date),
        )
        return cur.lastrowid


def build_startup_context(project_name: str | None = None) -> str:
    """Build a markdown summary block for agent system prompt injection."""
    lines = ["## Work Context\n"]

    goals = get_active_goals(project_name)
    if goals:
        lines.append("### Active Goals")
        for g in goals[:5]:
            due = f" (due {g['due_date']})" if g.get("due_date") else ""
            lines.append(f"- [{g['priority']}] {g['title']}{due}: {g['description']}")
        lines.append("")

    sessions = get_recent_sessions(project_name, limit=5)
    if sessions:
        lines.append("### Recent Work Sessions")
        for s in sessions:
            status_tag = f"[{s['status']}]"
            summary = s.get("summary") or s.get("input_intent") or "(no summary)"
            lines.append(f"- {status_tag} {s['started_at'][:10]} — {summary}")
        lines.append("")

    interrupted = [s for s in sessions if s["status"] == "interrupted"]
    if interrupted:
        lines.append("### ⚠ Interrupted Tasks (may need follow-up)")
        for s in interrupted:
            lines.append(
                f"- {s['started_at'][:10]} project={s.get('project_name', '?')}: {s.get('input_intent', '(unknown)')}"
            )
        lines.append("")

    return "\n".join(lines)
