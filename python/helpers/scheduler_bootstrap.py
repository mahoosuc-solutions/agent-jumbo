from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

DEFAULT_TARGET_PATH = Path("/aj/data/scheduler/tasks.json")
DEFAULT_SEED_CANDIDATES = (Path("/aj/tmp/scheduler/tasks.json"),)


def _task_count(path: Path) -> int:
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return 0
    tasks = payload.get("tasks", [])
    return len(tasks) if isinstance(tasks, list) else 0


def resolve_seed_candidates() -> list[Path]:
    candidates = list(DEFAULT_SEED_CANDIDATES)

    if configured := os.getenv("AGENT_JUMBO_SCHEDULER_SEED_PATH"):
        candidates.append(Path(configured))

    if configured_many := os.getenv("AGENT_JUMBO_SCHEDULER_SEED_PATHS"):
        candidates.extend(Path(p) for p in configured_many.split(":") if p)

    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return unique


def seed_scheduler_file(
    target_path: Path = DEFAULT_TARGET_PATH,
    candidates: list[Path] | None = None,
) -> Path | None:
    if target_path.exists() and target_path.stat().st_size > 0:
        return None

    if candidates is None:
        candidates = resolve_seed_candidates()

    for candidate in candidates:
        if not candidate.exists() or candidate.stat().st_size <= 0:
            continue
        if _task_count(candidate) <= 0:
            continue
        target_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(candidate, target_path)
        return candidate

    return None


def main() -> int:
    source = seed_scheduler_file()
    if source is None:
        print("scheduler bootstrap: no legacy seed copied")
    else:
        print(f"scheduler bootstrap: copied seed from {source}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
