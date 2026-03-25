from __future__ import annotations

import json
from typing import Any

from python.helpers.db_connection import DatabaseConnection

from .territory_seed import SEED_TERRITORIES


class OpportunitiesDatabase:
    def __init__(self, db_path: str = "data/opportunities.db"):
        self.db = DatabaseConnection(db_path)
        self.init_database()
        self.seed_territories()

    def init_database(self) -> None:
        conn = self.db.conn
        conn.execute("""
            CREATE TABLE IF NOT EXISTS territories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                state TEXT NOT NULL,
                metro_name TEXT NOT NULL,
                cluster_name TEXT NOT NULL,
                priority_tier INTEGER NOT NULL DEFAULT 3,
                status TEXT NOT NULL DEFAULT 'planned',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS territory_zips (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                territory_id INTEGER NOT NULL,
                zip_code TEXT NOT NULL,
                city TEXT NOT NULL DEFAULT '',
                state TEXT NOT NULL DEFAULT '',
                UNIQUE(territory_id, zip_code),
                FOREIGN KEY (territory_id) REFERENCES territories(id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS opportunities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                territory_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                buyer_name TEXT NOT NULL DEFAULT '',
                source_type TEXT NOT NULL DEFAULT 'manual',
                source_url TEXT,
                external_id TEXT,
                zip_code TEXT NOT NULL DEFAULT '',
                city TEXT NOT NULL DEFAULT '',
                state TEXT NOT NULL DEFAULT '',
                stage TEXT NOT NULL DEFAULT 'discovered',
                lane TEXT NOT NULL DEFAULT 'discovery',
                recommendation TEXT NOT NULL DEFAULT 'watch',
                approval_status TEXT NOT NULL DEFAULT 'pending',
                raw_requirements TEXT NOT NULL DEFAULT '',
                normalized_summary TEXT NOT NULL DEFAULT '',
                must_have_requirements TEXT NOT NULL DEFAULT '[]',
                due_date TEXT,
                strategic_fit_score REAL NOT NULL DEFAULT 0,
                delivery_risk_score REAL NOT NULL DEFAULT 0,
                estimated_contract_value REAL NOT NULL DEFAULT 0,
                confidence_score REAL NOT NULL DEFAULT 0,
                linked_idea_id INTEGER,
                linked_project_name TEXT,
                linked_workflow_name TEXT,
                linked_proposal_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(source_type, external_id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS opportunity_estimates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                opportunity_id INTEGER NOT NULL UNIQUE,
                total_hours REAL NOT NULL DEFAULT 0,
                timeline_weeks INTEGER NOT NULL DEFAULT 0,
                estimated_cost REAL NOT NULL DEFAULT 0,
                roles_json TEXT NOT NULL DEFAULT '[]',
                milestones_json TEXT NOT NULL DEFAULT '[]',
                assumptions_json TEXT NOT NULL DEFAULT '[]',
                risks_json TEXT NOT NULL DEFAULT '[]',
                pricing_notes TEXT NOT NULL DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (opportunity_id) REFERENCES opportunities(id)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_territories_status ON territories(status)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_opportunities_territory ON opportunities(territory_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_opportunities_stage ON opportunities(stage)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_opportunities_lane ON opportunities(lane)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_opportunities_due_date ON opportunities(due_date)")
        conn.commit()

    def seed_territories(self) -> None:
        existing = self.db.query_one("SELECT id FROM territories LIMIT 1")
        if existing:
            return
        for territory in SEED_TERRITORIES:
            created = self.create_territory(territory)
            for zip_row in territory["zips"]:
                self.add_zip(created["id"], zip_row)

    def create_territory(self, territory: dict[str, Any]) -> dict[str, Any]:
        with self.db.transaction() as conn:
            cursor = conn.execute(
                """
                INSERT INTO territories (state, metro_name, cluster_name, priority_tier, status)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    territory["state"],
                    territory["metro_name"],
                    territory["cluster_name"],
                    territory.get("priority_tier", 3),
                    territory.get("status", "planned"),
                ),
            )
            territory_id = int(cursor.lastrowid)
        created = self.get_territory(territory_id)
        if not created:
            raise RuntimeError(f"failed to create territory {territory_id}")
        return created

    def add_zip(self, territory_id: int, zip_row: dict[str, Any]) -> None:
        with self.db.transaction() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO territory_zips (territory_id, zip_code, city, state)
                VALUES (?, ?, ?, ?)
                """,
                (
                    territory_id,
                    zip_row["zip_code"],
                    zip_row.get("city", ""),
                    zip_row.get("state", ""),
                ),
            )

    def list_territories(self, status: str | None = None) -> list[dict[str, Any]]:
        where = []
        params: list[Any] = []
        if status:
            where.append("status = ?")
            params.append(status)
        sql = """
            SELECT *
            FROM territories
        """
        if where:
            sql += f" WHERE {' AND '.join(where)}"
        sql += " ORDER BY priority_tier ASC, metro_name ASC, cluster_name ASC"
        territories = self.db.query_rows(sql, params)
        for territory in territories:
            territory["zips"] = self.db.query_rows(
                "SELECT zip_code, city, state FROM territory_zips WHERE territory_id = ? ORDER BY zip_code",
                (territory["id"],),
            )
        return territories

    def get_territory(self, territory_id: int) -> dict[str, Any] | None:
        territory = self.db.query_one("SELECT * FROM territories WHERE id = ?", (territory_id,))
        if territory:
            territory["zips"] = self.db.query_rows(
                "SELECT zip_code, city, state FROM territory_zips WHERE territory_id = ? ORDER BY zip_code",
                (territory_id,),
            )
        return territory

    def update_territory_status(self, territory_id: int, status: str) -> bool:
        with self.db.transaction() as conn:
            cursor = conn.execute(
                """
                UPDATE territories SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?
                """,
                (status, territory_id),
            )
            return cursor.rowcount > 0

    def create_opportunity(self, payload: dict[str, Any]) -> dict[str, Any]:
        must_haves = json.dumps(payload.get("must_have_requirements", []))
        with self.db.transaction() as conn:
            cursor = conn.execute(
                """
                INSERT INTO opportunities (
                    territory_id, title, buyer_name, source_type, source_url, external_id,
                    zip_code, city, state, stage, lane, recommendation, approval_status,
                    raw_requirements, normalized_summary, must_have_requirements, due_date,
                    strategic_fit_score, delivery_risk_score, estimated_contract_value, confidence_score
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["territory_id"],
                    payload["title"],
                    payload.get("buyer_name", ""),
                    payload.get("source_type", "manual"),
                    payload.get("source_url"),
                    payload.get("external_id"),
                    payload.get("zip_code", ""),
                    payload.get("city", ""),
                    payload.get("state", ""),
                    payload.get("stage", "discovered"),
                    payload.get("lane", "discovery"),
                    payload.get("recommendation", "watch"),
                    payload.get("approval_status", "pending"),
                    payload.get("raw_requirements", ""),
                    payload.get("normalized_summary", ""),
                    must_haves,
                    payload.get("due_date"),
                    payload.get("strategic_fit_score", 0),
                    payload.get("delivery_risk_score", 0),
                    payload.get("estimated_contract_value", 0),
                    payload.get("confidence_score", 0),
                ),
            )
            opportunity_id = int(cursor.lastrowid)
        created = self.get_opportunity(opportunity_id)
        if not created:
            raise RuntimeError(f"failed to load opportunity {opportunity_id}")
        return created

    def find_existing_opportunity(
        self,
        *,
        territory_id: int,
        source_type: str,
        external_id: str | None = None,
        source_url: str | None = None,
        title: str,
        buyer_name: str,
        due_date: str | None = None,
    ) -> dict[str, Any] | None:
        if external_id:
            return self.db.query_one(
                """
                SELECT *
                FROM opportunities
                WHERE territory_id = ? AND source_type = ? AND external_id = ?
                """,
                (territory_id, source_type, external_id),
            )
        if source_url:
            return self.db.query_one(
                """
                SELECT *
                FROM opportunities
                WHERE territory_id = ? AND source_type = ? AND source_url = ?
                """,
                (territory_id, source_type, source_url),
            )
        return self.db.query_one(
            """
            SELECT *
            FROM opportunities
            WHERE territory_id = ?
              AND lower(title) = lower(?)
              AND lower(buyer_name) = lower(?)
              AND coalesce(due_date, '') = coalesce(?, '')
            """,
            (territory_id, title, buyer_name, due_date),
        )

    def create_or_update_opportunity(self, payload: dict[str, Any]) -> tuple[dict[str, Any], bool]:
        existing = self.find_existing_opportunity(
            territory_id=payload["territory_id"],
            source_type=payload.get("source_type", "manual"),
            external_id=payload.get("external_id"),
            source_url=payload.get("source_url"),
            title=payload["title"],
            buyer_name=payload.get("buyer_name", ""),
            due_date=payload.get("due_date"),
        )
        if not existing:
            return self.create_opportunity(payload), True

        updates = {
            "source_url": payload.get("source_url"),
            "external_id": payload.get("external_id"),
            "zip_code": payload.get("zip_code", ""),
            "city": payload.get("city", ""),
            "state": payload.get("state", ""),
            "raw_requirements": payload.get("raw_requirements", ""),
            "normalized_summary": payload.get("normalized_summary", ""),
            "must_have_requirements": payload.get("must_have_requirements", []),
            "due_date": payload.get("due_date"),
            "strategic_fit_score": payload.get("strategic_fit_score", existing.get("strategic_fit_score", 0)),
            "delivery_risk_score": payload.get("delivery_risk_score", existing.get("delivery_risk_score", 0)),
            "estimated_contract_value": payload.get(
                "estimated_contract_value",
                existing.get("estimated_contract_value", 0),
            ),
            "confidence_score": payload.get("confidence_score", existing.get("confidence_score", 0)),
        }
        self.update_opportunity(existing["id"], updates)
        reloaded = self.get_opportunity(existing["id"])
        if not reloaded:
            raise RuntimeError(f"failed to reload opportunity {existing['id']}")
        return reloaded, False

    def update_opportunity(self, opportunity_id: int, updates: dict[str, Any]) -> bool:
        allowed = {
            "title",
            "buyer_name",
            "source_type",
            "source_url",
            "external_id",
            "zip_code",
            "city",
            "state",
            "stage",
            "lane",
            "recommendation",
            "approval_status",
            "raw_requirements",
            "normalized_summary",
            "must_have_requirements",
            "due_date",
            "strategic_fit_score",
            "delivery_risk_score",
            "estimated_contract_value",
            "confidence_score",
            "linked_idea_id",
            "linked_project_name",
            "linked_workflow_name",
            "linked_proposal_id",
        }
        sets: list[str] = []
        params: list[Any] = []
        for key, value in updates.items():
            if key not in allowed:
                continue
            if key == "must_have_requirements":
                value = json.dumps(value or [])
            sets.append(f"{key} = ?")
            params.append(value)
        if not sets:
            return False
        sets.append("updated_at = CURRENT_TIMESTAMP")
        params.append(opportunity_id)
        with self.db.transaction() as conn:
            cursor = conn.execute(
                f"UPDATE opportunities SET {', '.join(sets)} WHERE id = ?",
                params,
            )
            return cursor.rowcount > 0

    def list_opportunities(
        self,
        territory_id: int | None = None,
        stage: str | None = None,
        lane: str | None = None,
        search: str | None = None,
    ) -> list[dict[str, Any]]:
        where = ["1=1"]
        params: list[Any] = []
        if territory_id:
            where.append("territory_id = ?")
            params.append(territory_id)
        if stage:
            where.append("stage = ?")
            params.append(stage)
        if lane:
            where.append("lane = ?")
            params.append(lane)
        if search:
            like = f"%{search}%"
            where.append("(title LIKE ? OR buyer_name LIKE ? OR normalized_summary LIKE ?)")
            params.extend([like, like, like])
        rows = self.db.query_rows(
            f"""
            SELECT opportunities.*, territories.cluster_name, territories.metro_name
            FROM opportunities
            JOIN territories ON territories.id = opportunities.territory_id
            WHERE {" AND ".join(where)}
            ORDER BY
              CASE stage
                WHEN 'discovered' THEN 1
                WHEN 'normalized' THEN 2
                WHEN 'qualified' THEN 3
                WHEN 'estimated' THEN 4
                WHEN 'approved_for_solutioning' THEN 5
                WHEN 'solutioning' THEN 6
                WHEN 'proposal_ready' THEN 7
                ELSE 8
              END,
              COALESCE(due_date, '9999-12-31') ASC,
              updated_at DESC
            """,
            params,
        )
        for row in rows:
            row["must_have_requirements"] = json.loads(row.get("must_have_requirements") or "[]")
            row["estimate"] = self.get_estimate(row["id"])
        return rows

    def get_opportunity(self, opportunity_id: int) -> dict[str, Any] | None:
        row = self.db.query_one(
            """
            SELECT opportunities.*, territories.cluster_name, territories.metro_name
            FROM opportunities
            JOIN territories ON territories.id = opportunities.territory_id
            WHERE opportunities.id = ?
            """,
            (opportunity_id,),
        )
        if row:
            row["must_have_requirements"] = json.loads(row.get("must_have_requirements") or "[]")
            row["estimate"] = self.get_estimate(opportunity_id)
        return row

    def upsert_estimate(self, opportunity_id: int, payload: dict[str, Any]) -> dict[str, Any]:
        encoded = {
            "roles_json": json.dumps(payload.get("roles", [])),
            "milestones_json": json.dumps(payload.get("milestones", [])),
            "assumptions_json": json.dumps(payload.get("assumptions", [])),
            "risks_json": json.dumps(payload.get("risks", [])),
        }
        with self.db.transaction() as conn:
            existing = conn.execute(
                "SELECT id FROM opportunity_estimates WHERE opportunity_id = ?",
                (opportunity_id,),
            ).fetchone()
            if existing:
                conn.execute(
                    """
                    UPDATE opportunity_estimates
                    SET total_hours = ?, timeline_weeks = ?, estimated_cost = ?,
                        roles_json = ?, milestones_json = ?, assumptions_json = ?, risks_json = ?,
                        pricing_notes = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE opportunity_id = ?
                    """,
                    (
                        payload["total_hours"],
                        payload["timeline_weeks"],
                        payload["estimated_cost"],
                        encoded["roles_json"],
                        encoded["milestones_json"],
                        encoded["assumptions_json"],
                        encoded["risks_json"],
                        payload.get("pricing_notes", ""),
                        opportunity_id,
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO opportunity_estimates (
                        opportunity_id, total_hours, timeline_weeks, estimated_cost,
                        roles_json, milestones_json, assumptions_json, risks_json, pricing_notes
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        opportunity_id,
                        payload["total_hours"],
                        payload["timeline_weeks"],
                        payload["estimated_cost"],
                        encoded["roles_json"],
                        encoded["milestones_json"],
                        encoded["assumptions_json"],
                        encoded["risks_json"],
                        payload.get("pricing_notes", ""),
                    ),
                )
        estimate = self.get_estimate(opportunity_id)
        if not estimate:
            raise RuntimeError(f"failed to save estimate for opportunity {opportunity_id}")
        return estimate

    def get_estimate(self, opportunity_id: int) -> dict[str, Any] | None:
        row = self.db.query_one("SELECT * FROM opportunity_estimates WHERE opportunity_id = ?", (opportunity_id,))
        if not row:
            return None
        row["roles"] = json.loads(row.pop("roles_json") or "[]")
        row["milestones"] = json.loads(row.pop("milestones_json") or "[]")
        row["assumptions"] = json.loads(row.pop("assumptions_json") or "[]")
        row["risks"] = json.loads(row.pop("risks_json") or "[]")
        return row

    def territory_dashboard(self) -> dict[str, Any]:
        territories = self.list_territories()
        result = {
            "territories": [],
            "stats": {
                "total_territories": len(territories),
                "active_territories": 0,
                "covered_territories": 0,
                "total_opportunities": 0,
                "approved_opportunities": 0,
            },
        }
        for territory in territories:
            counts = self.db.query_rows(
                """
                SELECT stage, COUNT(*) as count
                FROM opportunities
                WHERE territory_id = ?
                GROUP BY stage
                """,
                (territory["id"],),
            )
            count_map = {row["stage"]: row["count"] for row in counts}
            total = sum(count_map.values())
            coverage_ready = total > 0 and count_map.get("discovered", 0) == 0 and count_map.get("normalized", 0) == 0
            enriched = {
                **territory,
                "opportunity_total": total,
                "by_stage": count_map,
                "coverage_complete": coverage_ready,
            }
            result["territories"].append(enriched)
            result["stats"]["total_opportunities"] += total
            result["stats"]["approved_opportunities"] += (
                count_map.get("approved_for_solutioning", 0)
                + count_map.get("solutioning", 0)
                + count_map.get("proposal_ready", 0)
            )
            if territory["status"] == "active":
                result["stats"]["active_territories"] += 1
            if territory["status"] == "covered":
                result["stats"]["covered_territories"] += 1
        return result
