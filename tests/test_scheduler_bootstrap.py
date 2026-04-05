import json
from pathlib import Path

from python.helpers.scheduler_bootstrap import seed_scheduler_file


def write_tasks(path: Path, count: int) -> None:
    tasks = [{"uuid": str(i), "name": f"task-{i}"} for i in range(count)]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"tasks": tasks}))


def test_seed_scheduler_file_copies_first_non_empty_candidate(tmp_path):
    target = tmp_path / "data" / "scheduler" / "tasks.json"
    empty_seed = tmp_path / "tmp" / "scheduler" / "tasks.json"
    full_seed = tmp_path / "host" / "scheduler" / "tasks.json"

    write_tasks(empty_seed, 0)
    write_tasks(full_seed, 2)

    copied = seed_scheduler_file(target, [empty_seed, full_seed])

    assert copied == full_seed
    assert target.read_text() == full_seed.read_text()


def test_seed_scheduler_file_does_not_override_existing_target(tmp_path):
    target = tmp_path / "data" / "scheduler" / "tasks.json"
    seed = tmp_path / "host" / "scheduler" / "tasks.json"

    write_tasks(target, 1)
    write_tasks(seed, 3)

    copied = seed_scheduler_file(target, [seed])

    assert copied is None
    assert '"name": "task-0"' in target.read_text()


def test_seed_scheduler_file_returns_none_when_no_valid_candidates(tmp_path):
    target = tmp_path / "data" / "scheduler" / "tasks.json"
    missing = tmp_path / "missing.json"
    invalid = tmp_path / "invalid.json"
    invalid.write_text("not-json")

    copied = seed_scheduler_file(target, [missing, invalid])

    assert copied is None
    assert not target.exists()
