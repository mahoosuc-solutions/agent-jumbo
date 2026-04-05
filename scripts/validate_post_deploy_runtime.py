#!/usr/bin/env python3
"""Validate deployed runtime state and key dashboard/browser flows.

Checks:
- HTTP health endpoint responds healthy/degraded
- persisted scheduler file exists in the container and is non-empty
- scheduler API returns tasks
- browser smokes for Work Queue, Workflows, Tasks, Trust & Security, New Chat

Optional:
- restart the container and repeat scheduler persistence checks
"""

from __future__ import annotations

import argparse
import json
import subprocess
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

PLAYWRIGHT_CHECK = r"""
from pathlib import Path
from playwright.sync_api import sync_playwright
import json

BASE_URL = "__BASE_URL__"


def browser_executable():
    candidates = sorted(
        Path("/opt/playwright").glob(
            "chromium_headless_shell-*/chrome-headless-shell-linux64/chrome-headless-shell"
        )
    )
    if not candidates:
        raise RuntimeError("No Playwright browser executable found in /opt/playwright")
    return str(candidates[-1])


def visible_title(page):
    return page.locator(".dashboard-page:visible .dashboard-title").first.inner_text().strip()


def click_sidebar(page, label, title=None):
    selectors = []
    if title:
        selectors.append(page.locator(f"button[title='{title}']"))
    selectors.extend(
        [
            page.get_by_role("button", name=label),
            page.locator(f"button:has-text('{label}')"),
        ]
    )
    for candidate in selectors:
        if candidate.count():
            candidate.first.click()
            page.wait_for_load_state("networkidle")
            return
    raise RuntimeError(f"Could not find dashboard nav for {label}")


def click_trust(page):
    for candidate in [
        page.locator("button[title='Trust & Security']"),
        page.get_by_role("button", name="Trust"),
        page.locator("button:has-text('Trust')"),
    ]:
        if candidate.count():
            candidate.first.click()
            page.wait_for_load_state("networkidle")
            return
    raise RuntimeError("Could not find Trust navigation entry")


def click_new_chat(page):
    for candidate in [
        page.locator("#newChat"),
        page.get_by_role("button", name="New Chat"),
        page.locator("button:has-text('New Chat')"),
    ]:
        if candidate.count():
            candidate.first.click()
            return
    raise RuntimeError("Could not find New Chat button")


result = {}

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, executable_path=browser_executable())

    page = browser.new_page(viewport={"width": 1440, "height": 1400})
    page.goto(BASE_URL, wait_until="networkidle")
    page.evaluate("() => localStorage.setItem('trust_onboarded', '1')")
    page.reload(wait_until="networkidle")

    click_sidebar(page, "Work Queue", "Work Queue")
    result["work_queue"] = {
        "heading": visible_title(page),
        "rows": page.locator(".dashboard-page:visible table tbody tr").count(),
    }

    click_sidebar(page, "Tasks", "Tasks")
    page.wait_for_timeout(1200)
    result["tasks"] = {
        "heading": visible_title(page),
        "cards": page.locator(".dashboard-page:visible .td-card").count(),
        "stats": page.locator(".dashboard-page:visible .stats-cards .stat-value").all_inner_texts(),
        "has_scheduler_task": page.locator(".dashboard-page:visible .td-card-name")
        .get_by_text("platform-health-monitor")
        .count()
        > 0,
    }

    click_trust(page)
    page.wait_for_timeout(800)
    result["trust"] = {
        "heading": visible_title(page),
        "level_cards": page.locator(".dashboard-page:visible .tr-level-card").count(),
        "posture_items": page.locator(".dashboard-page:visible .tr-posture-item").count(),
    }

    before_name = (
        page.locator(".chat-container.chat-selected .chat-name").first.inner_text().strip()
        if page.locator(".chat-container.chat-selected .chat-name").count()
        else ""
    )
    before_id = page.evaluate("() => localStorage.getItem('lastSelectedChat') || ''")
    click_new_chat(page)
    page.wait_for_timeout(1200)
    after_name = (
        page.locator(".chat-container.chat-selected .chat-name").first.inner_text().strip()
        if page.locator(".chat-container.chat-selected .chat-name").count()
        else ""
    )
    after_id = page.evaluate("() => localStorage.getItem('lastSelectedChat') || ''")
    result["new_chat"] = {
        "before": before_name,
        "before_id": before_id,
        "after": after_name,
        "after_id": after_id,
        "active_count": page.locator(".chat-container.chat-selected").count(),
        "changed": bool(after_id and after_id != before_id),
    }
    browser.close()

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, executable_path=browser_executable())
    page = browser.new_page(viewport={"width": 1440, "height": 1400})
    page.goto(BASE_URL + "/workflows", wait_until="networkidle")
    page.evaluate("() => localStorage.setItem('trust_onboarded', '1')")
    page.reload(wait_until="networkidle")
    page.wait_for_timeout(1500)
    result["workflows"] = {
        "titles": page.locator(".dashboard-page:visible .dashboard-title").all_inner_texts(),
        "active_dashboard": page.evaluate("() => Alpine.store('dashboardRouter')?.activeDashboard"),
        "stats": page.locator(".dashboard-page:visible [data-testid$='-value']").all_inner_texts()[:8],
        "recent_execution_rows": page.locator(".dashboard-page:visible .execution-item").count(),
        "workflow_items": page.locator(".dashboard-page:visible .workflow-item").count(),
        "error": page.locator(".dashboard-page:visible [data-testid=workflow-error]").inner_text()
        if page.locator(".dashboard-page:visible [data-testid=workflow-error]").count()
        else "",
    }
    browser.close()

print(json.dumps(result))
"""


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str


def run_command(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, check=check, text=True, capture_output=True)


def fetch_json(url: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def scheduler_file_check(container: str) -> CheckResult:
    cmd = [
        "docker",
        "exec",
        container,
        "sh",
        "-lc",
        "test -s /aj/data/scheduler/tasks.json && wc -c /aj/data/scheduler/tasks.json",
    ]
    proc = run_command(cmd, check=False)
    if proc.returncode != 0:
        return CheckResult(
            "scheduler_file",
            False,
            proc.stderr.strip() or "missing or empty /aj/data/scheduler/tasks.json",
        )
    return CheckResult("scheduler_file", True, proc.stdout.strip())


def scheduler_api_check(base_url: str) -> tuple[CheckResult, dict[str, Any]]:
    try:
        payload = fetch_json(f"{base_url}/scheduler_tasks_list", {})
    except (urllib.error.URLError, ConnectionError, ConnectionResetError) as exc:
        return CheckResult("scheduler_api", False, str(exc)), {}
    tasks = payload.get("tasks", [])
    ok = bool(payload.get("ok")) and len(tasks) > 0
    detail = f"ok={payload.get('ok')} tasks={len(tasks)}"
    return CheckResult("scheduler_api", ok, detail), payload


def health_check(base_url: str) -> CheckResult:
    try:
        payload = fetch_json(f"{base_url}/health")
    except (urllib.error.URLError, ConnectionError, ConnectionResetError) as exc:
        return CheckResult("health", False, str(exc))
    status = payload.get("status", "")
    ok = status in {"healthy", "degraded"}
    return CheckResult("health", ok, f"status={status}")


def workflow_api_check(base_url: str) -> CheckResult:
    try:
        payload = fetch_json(f"{base_url}/workflow_dashboard", {})
    except (urllib.error.URLError, ConnectionError, ConnectionResetError) as exc:
        return CheckResult("workflow_api", False, str(exc))
    stats = payload.get("stats", {})
    ok = bool(payload.get("success")) and all(
        isinstance(stats.get(key), int) and stats.get(key, 0) > 0
        for key in ("total_workflows", "total_executions", "total_skills", "total_learning_paths")
    )
    detail = (
        f"success={payload.get('success')} "
        f"stats={stats.get('total_workflows')}/{stats.get('total_executions')}/"
        f"{stats.get('total_skills')}/{stats.get('total_learning_paths')}"
    )
    return CheckResult("workflow_api", ok, detail)


def browser_smoke(container: str, base_url: str) -> tuple[CheckResult, dict[str, Any]]:
    script = PLAYWRIGHT_CHECK.replace("__BASE_URL__", base_url)
    shell = ". /ins/setup_venv.sh local && python - <<'PY'\n" + script + "\nPY"
    proc = run_command(["docker", "exec", container, "bash", "-lc", shell], check=False)
    if proc.returncode != 0:
        return CheckResult("browser_smoke", False, proc.stderr.strip() or proc.stdout.strip()), {}
    data = json.loads(proc.stdout.strip())
    work_queue_ok = data["work_queue"]["heading"] == "Work Queue" and data["work_queue"]["rows"] > 0
    workflows_ok = (
        data["workflows"]["active_dashboard"] == "workflows"
        and "Workflows & Training" in data["workflows"]["titles"]
        and data["workflows"]["stats"][:4] == ["23", "14", "22", "2"]
        and data["workflows"]["workflow_items"] > 0
        and not data["workflows"]["error"]
    )
    tasks_ok = (
        data["tasks"]["heading"] == "Task Dashboard"
        and data["tasks"]["cards"] > 0
        and data["tasks"]["has_scheduler_task"]
    )
    trust_ok = (
        data["trust"]["heading"] == "Trust & Security"
        and data["trust"]["level_cards"] == 4
        and data["trust"]["posture_items"] >= 6
    )
    new_chat_ok = data["new_chat"]["changed"] and data["new_chat"]["active_count"] == 1
    ok = all((work_queue_ok, workflows_ok, tasks_ok, trust_ok, new_chat_ok))
    detail = (
        f"work_queue={work_queue_ok} workflows={workflows_ok} tasks={tasks_ok} trust={trust_ok} new_chat={new_chat_ok}"
    )
    return CheckResult("browser_smoke", ok, detail), data


def restart_container(container: str) -> CheckResult:
    proc = run_command(["docker", "restart", container], check=False)
    if proc.returncode != 0:
        return CheckResult("restart", False, proc.stderr.strip() or proc.stdout.strip())
    return CheckResult("restart", True, proc.stdout.strip())


def wait_for_http_health(base_url: str, timeout_seconds: int = 120) -> CheckResult:
    deadline = time.time() + timeout_seconds
    last_error = "timed out"
    while time.time() < deadline:
        result = health_check(base_url)
        if result.ok:
            return CheckResult("wait_for_health", True, result.detail)
        last_error = result.detail
        time.sleep(3)
    return CheckResult("wait_for_health", False, last_error)


def print_result(result: CheckResult) -> None:
    status = "PASS" if result.ok else "FAIL"
    print(f"[{status}] {result.name}: {result.detail}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate deployed runtime state and dashboard/browser flows.")
    parser.add_argument("--base-url", default="http://localhost:6274")
    parser.add_argument("--browser-base-url", default="http://127.0.0.1:80")
    parser.add_argument("--container", default="agent-jumbo-production")
    parser.add_argument(
        "--restart-container",
        action="store_true",
        help="Restart the container and repeat scheduler persistence checks.",
    )
    args = parser.parse_args()

    results: list[CheckResult] = []
    artifacts: dict[str, Any] = {}

    results.append(wait_for_http_health(args.base_url))
    results.append(health_check(args.base_url))
    results.append(scheduler_file_check(args.container))
    scheduler_result, scheduler_payload = scheduler_api_check(args.base_url)
    results.append(scheduler_result)
    results.append(workflow_api_check(args.base_url))
    browser_result, browser_payload = browser_smoke(args.container, args.browser_base_url)
    results.append(browser_result)

    artifacts["scheduler_api"] = {
        "task_count": len(scheduler_payload.get("tasks", [])),
    }
    artifacts["browser"] = browser_payload

    if args.restart_container:
        results.append(restart_container(args.container))
        results.append(wait_for_http_health(args.base_url))
        results.append(scheduler_file_check(args.container))
        scheduler_after_restart, scheduler_payload_after_restart = scheduler_api_check(args.base_url)
        results.append(scheduler_after_restart)
        artifacts["scheduler_api_after_restart"] = {
            "task_count": len(scheduler_payload_after_restart.get("tasks", [])),
        }

    for result in results:
        print_result(result)

    print(json.dumps(artifacts, indent=2))

    return 0 if all(result.ok for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
