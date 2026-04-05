"""
Memory Stats API — returns memory statistics and supports consolidation operations.
"""

from __future__ import annotations

from python.helpers.api import ApiHandler


class MemoryStats(ApiHandler):
    """API endpoint for memory statistics and consolidation."""

    async def process(self, input: dict, request) -> dict:
        try:
            from python.helpers.memory import Memory, get_existing_memory_subdirs

            action = input.get("action", "stats")

            if action == "list_subdirs":
                subdirs = get_existing_memory_subdirs()
                return {"success": True, "subdirs": subdirs}

            if action == "stats":
                subdir = input.get("memory_subdir", "default")
                db = Memory.index.get(subdir)
                if not db:
                    return {
                        "success": True,
                        "stats": {
                            "total_documents": 0,
                            "by_area": {},
                            "memory_subdir": subdir,
                            "loaded": False,
                        },
                    }
                mem = Memory(db=db, memory_subdir=subdir)
                stats = mem.get_stats()
                stats["loaded"] = True
                return {"success": True, "stats": stats}

            if action == "consolidate":
                subdir = input.get("memory_subdir", "default")
                area = input.get("area")
                threshold = float(input.get("similarity_threshold", 0.95))
                dry_run = bool(input.get("dry_run", True))

                db = Memory.index.get(subdir)
                if not db:
                    return {"success": False, "error": f"Memory subdir '{subdir}' not loaded"}

                mem = Memory(db=db, memory_subdir=subdir)
                result = await mem.consolidate(
                    area=area,
                    similarity_threshold=threshold,
                    dry_run=dry_run,
                )
                return {"success": True, **result}

            if action == "retention":
                subdir = input.get("memory_subdir", "default")
                area = input.get("area", "executive")
                max_age_days = int(input.get("max_age_days", 90))
                dry_run = bool(input.get("dry_run", True))

                db = Memory.index.get(subdir)
                if not db:
                    return {"success": False, "error": f"Memory subdir '{subdir}' not loaded"}

                mem = Memory(db=db, memory_subdir=subdir)
                result = await mem.apply_retention(
                    area=area,
                    max_age_days=max_age_days,
                    dry_run=dry_run,
                )
                return {"success": True, **result}

            return {"success": False, "error": f"Unknown action: {action}"}

        except Exception as e:
            import traceback

            traceback.print_exc()
            return {"success": False, "error": str(e)}
