"""
Codebase Scanner — stateless discovery of work items from source code.

Takes a project path, returns findings as dicts ready for upsert.
"""

import hashlib
import json
import os
import re
import subprocess
from pathlib import Path
from typing import Any

# Directories to always skip
IGNORE_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    ".next",
    ".turbo",
    "dist",
    "build",
    ".cache",
    ".mypy_cache",
    ".pytest_cache",
    ".tox",
    "coverage",
    ".nyc_output",
    "vendor",
    ".egg-info",
    "eggs",
    ".eggs",
}

# File extensions to scan for TODOs
CODE_EXTENSIONS = {
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".go",
    ".rs",
    ".rb",
    ".java",
    ".kt",
    ".swift",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
    ".cs",
    ".php",
    ".sh",
    ".bash",
    ".zsh",
    ".yaml",
    ".yml",
    ".toml",
    ".cfg",
    ".ini",
    ".sql",
    ".html",
    ".css",
    ".scss",
}

TODO_PATTERN = re.compile(
    r"#\s*(TODO|FIXME|HACK|XXX|BUG|OPTIMIZE|REVIEW)\b[:\s]*(.*)",
    re.IGNORECASE,
)

SKIP_PATTERN_PY = re.compile(
    r"@pytest\.mark\.skip|pytest\.skip\(|@unittest\.skip|\.skipTest\(",
)

SKIP_PATTERN_JS = re.compile(
    r"\bit\.skip\b|\bxit\b|\bdescribe\.skip\b|\btest\.skip\b|\bxdescribe\b|\bxtest\b",
)


def _make_id(file_path: str, line_number: int, source_type: str, snippet: str) -> str:
    """Deterministic external_id for dedup across scans."""
    raw = f"{file_path}:{line_number}:{source_type}:{snippet[:80]}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _should_skip_dir(name: str) -> bool:
    return name in IGNORE_DIRS or name.startswith(".")


def _walk_files(project_path: str, extensions: set[str] | None = None):
    """Yield (full_path, relative_path) for scannable files."""
    root = Path(project_path)
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if not _should_skip_dir(d)]
        for fname in filenames:
            if extensions and Path(fname).suffix not in extensions:
                continue
            full = os.path.join(dirpath, fname)
            rel = os.path.relpath(full, root)
            yield full, rel


def scan_todos(project_path: str) -> list[dict[str, Any]]:
    """Find TODO/FIXME/HACK/XXX comments in source code."""
    findings: list[dict[str, Any]] = []

    for full_path, rel_path in _walk_files(project_path, CODE_EXTENSIONS):
        try:
            with open(full_path, encoding="utf-8", errors="ignore") as f:
                for line_no, line in enumerate(f, 1):
                    m = TODO_PATTERN.search(line)
                    if m:
                        tag = m.group(1).upper()
                        comment = m.group(2).strip()
                        title = f"{tag}: {comment[:120]}" if comment else f"{tag} in {rel_path}"

                        source_type = "fixme" if tag in ("FIXME", "BUG") else "todo"
                        findings.append(
                            {
                                "source": "scanner",
                                "source_type": source_type,
                                "title": title,
                                "description": f"{tag} comment at {rel_path}:{line_no}\n\n```\n{line.strip()}\n```",
                                "file_path": rel_path,
                                "line_number": line_no,
                                "external_id": _make_id(rel_path, line_no, source_type, line.strip()),
                            }
                        )
        except (OSError, UnicodeDecodeError):
            continue

    return findings


def scan_skipped_tests(project_path: str) -> list[dict[str, Any]]:
    """Find skipped/disabled tests in Python and JS/TS files."""
    findings: list[dict[str, Any]] = []
    test_extensions = {".py", ".js", ".ts", ".tsx", ".jsx"}

    for full_path, rel_path in _walk_files(project_path, test_extensions):
        # Only scan files that look like tests
        fname = Path(rel_path).name
        if not (
            fname.startswith("test_")
            or fname.endswith(("_test.py", ".test.ts", ".test.js", ".test.tsx", ".test.jsx", ".spec.ts", ".spec.js"))
        ):
            continue

        try:
            with open(full_path, encoding="utf-8", errors="ignore") as f:
                for line_no, line in enumerate(f, 1):
                    pattern = SKIP_PATTERN_PY if rel_path.endswith(".py") else SKIP_PATTERN_JS
                    if pattern.search(line):
                        snippet = line.strip()
                        findings.append(
                            {
                                "source": "scanner",
                                "source_type": "skipped_test",
                                "title": f"Skipped test in {fname}:{line_no}",
                                "description": f"Test is marked as skipped:\n\n```\n{snippet}\n```",
                                "file_path": rel_path,
                                "line_number": line_no,
                                "external_id": _make_id(rel_path, line_no, "skipped_test", snippet),
                            }
                        )
        except (OSError, UnicodeDecodeError):
            continue

    return findings


def scan_failing_tests(project_path: str) -> list[dict[str, Any]]:
    """
    Detect test framework and run a quick collection check.

    Returns findings for test collection errors, not full test runs
    (which would be too slow for a scan).
    """
    findings: list[dict[str, Any]] = []
    root = Path(project_path)

    # Python: pytest --collect-only
    if (root / "pytest.ini").exists() or (root / "pyproject.toml").exists() or (root / "setup.cfg").exists():
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "--collect-only", "-q", "--no-header"],
                cwd=project_path,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                error_lines = result.stderr.strip().split("\n") if result.stderr else result.stdout.strip().split("\n")
                for line in error_lines[-5:]:
                    if "ERROR" in line or "error" in line.lower():
                        findings.append(
                            {
                                "source": "scanner",
                                "source_type": "failing_test",
                                "title": f"Test collection error: {line[:120]}",
                                "description": f"pytest --collect-only failed:\n\n```\n{result.stderr[-500:] or result.stdout[-500:]}\n```",
                                "file_path": "",
                                "line_number": 0,
                                "external_id": _make_id("pytest", 0, "failing_test", line),
                            }
                        )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    # JS/TS: check for package.json test script existence (don't run — too slow)
    pkg_json = root / "package.json"
    if pkg_json.exists():
        try:
            pkg = json.loads(pkg_json.read_text())
            scripts = pkg.get("scripts", {})
            if "test" not in scripts:
                findings.append(
                    {
                        "source": "scanner",
                        "source_type": "coverage",
                        "title": "No test script defined in package.json",
                        "description": "package.json has no `test` script. Consider adding one.",
                        "file_path": "package.json",
                        "line_number": 0,
                        "external_id": _make_id("package.json", 0, "coverage", "no-test-script"),
                    }
                )
        except (json.JSONDecodeError, OSError):
            pass

    return findings


def scan_stale_deps(project_path: str) -> list[dict[str, Any]]:
    """Check for potentially stale or vulnerable dependencies."""
    findings: list[dict[str, Any]] = []
    root = Path(project_path)

    # Python: pip-audit if available
    req_file = root / "requirements.txt"
    if req_file.exists():
        try:
            result = subprocess.run(
                ["pip-audit", "-r", str(req_file), "--format", "json", "--progress-spinner", "off"],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=project_path,
            )
            if result.returncode == 0 and result.stdout.strip():
                vulns = json.loads(result.stdout)
                for vuln in vulns.get("dependencies", []):
                    if vuln.get("vulns"):
                        for v in vuln["vulns"]:
                            findings.append(
                                {
                                    "source": "scanner",
                                    "source_type": "stale_dep",
                                    "title": f"Vulnerability in {vuln['name']} ({v.get('id', 'unknown')})",
                                    "description": f"Package: {vuln['name']} {vuln.get('version', '')}\n{v.get('description', '')}",
                                    "file_path": "requirements.txt",
                                    "line_number": 0,
                                    "external_id": _make_id(
                                        "requirements.txt", 0, "stale_dep", f"{vuln['name']}:{v.get('id', '')}"
                                    ),
                                }
                            )
        except (subprocess.TimeoutExpired, FileNotFoundError, json.JSONDecodeError):
            pass

    # JS: npm audit (quick check)
    pkg_lock = root / "package-lock.json"
    yarn_lock = root / "yarn.lock"
    if pkg_lock.exists() or yarn_lock.exists():
        try:
            cmd = ["npm", "audit", "--json"] if pkg_lock.exists() else ["yarn", "audit", "--json"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=project_path,
            )
            if result.stdout.strip():
                try:
                    audit = json.loads(result.stdout)
                    advisories = audit.get("advisories", audit.get("vulnerabilities", {}))
                    if isinstance(advisories, dict):
                        for name, info in list(advisories.items())[:20]:
                            sev = info.get("severity", "unknown") if isinstance(info, dict) else "unknown"
                            title_text = info.get("title", name) if isinstance(info, dict) else name
                            findings.append(
                                {
                                    "source": "scanner",
                                    "source_type": "stale_dep",
                                    "title": f"npm audit: {title_text} ({sev})",
                                    "description": f"Package: {name}\nSeverity: {sev}",
                                    "file_path": "package.json",
                                    "line_number": 0,
                                    "external_id": _make_id("package.json", 0, "stale_dep", f"npm:{name}"),
                                }
                            )
                except json.JSONDecodeError:
                    pass
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    return findings


def scan_coverage(project_path: str) -> list[dict[str, Any]]:
    """
    Find source files that have no corresponding test file.

    Only scans key directories containing business logic (API handlers, helpers,
    tools, library code, instruments). Skips config, docs, prompts, agents, and
    framework boilerplate to keep findings actionable.

    Returns findings with source_type='coverage'.
    """
    findings: list[dict[str, Any]] = []
    root = Path(project_path)
    source_extensions = {".py", ".ts", ".js", ".tsx", ".jsx"}

    # Only scan directories that contain testable business logic
    key_dirs = [
        "python/api",
        "python/helpers",
        "python/tools",
        "python/extensions",
        "python/cli",
        "instruments/custom",
        "instruments/default",
        "lib",
        "web/lib",
        "web/hooks",
    ]
    # Minimum line count — files under this threshold are likely thin wrappers
    min_lines = 50

    for full_path, rel_path in _walk_files(project_path, source_extensions):
        # Filter to key directories only
        if not any(rel_path.startswith(d + "/") or rel_path.startswith(d + "\\") for d in key_dirs):
            continue

        fname = Path(rel_path).name
        stem = Path(fname).stem
        ext = Path(fname).suffix

        if _is_test_or_config_file(fname, stem):
            continue

        # Skip small files — wrappers and re-exports don't need dedicated tests
        try:
            with open(full_path, errors="ignore") as _fh:
                line_count = sum(1 for _ in _fh)
            if line_count < min_lines:
                continue
        except OSError:
            continue

        if _has_matching_test(root, rel_path, stem, ext):
            continue

        findings.append(
            {
                "source": "scanner",
                "source_type": "coverage",
                "title": f"No test file for {rel_path}",
                "description": f"Source file `{rel_path}` ({line_count} lines) has no corresponding test file.",
                "file_path": rel_path,
                "line_number": 0,
                "external_id": _make_id(rel_path, 0, "coverage", f"no-test:{rel_path}"),
            }
        )

    return findings


def _is_test_or_config_file(fname: str, stem: str) -> bool:
    """Return True if the file is a test, config, or utility that doesn't need its own test."""
    skip_prefixes = ("test_", "conftest")
    skip_suffixes = (
        "_test",
        ".test",
        ".spec",
        ".config",
        ".d",
        "__init__",
        "setup",
        "manage",
        "main",
    )
    skip_exact = {"index", "page", "layout", "loading", "error", "not-found", "types", "constants"}

    if fname.startswith(skip_prefixes):
        return True
    if any(stem.endswith(s) for s in skip_suffixes):
        return True
    if stem in skip_exact:
        return True
    return False


def _has_matching_test(root: Path, rel_path: str, stem: str, ext: str) -> bool:
    """Return True if a plausible test file exists for the given source file."""
    if ext == ".py":
        test_names = {f"test_{stem}.py", f"{stem}_test.py"}
    else:
        test_names = {f"{stem}.test{ext}", f"{stem}.spec{ext}", f"{stem}.test.tsx", f"{stem}.spec.tsx"}

    # Check co-located
    source_dir = (root / rel_path).parent
    for tn in test_names:
        if (source_dir / tn).exists():
            return True

    # Check common test directories (flat and mirrored)
    test_dirs = ["tests", "test", "__tests__", "spec"]
    for td in test_dirs:
        rel_dir = Path(rel_path).parent
        for tn in test_names:
            if (root / td / tn).exists():
                return True
            if (root / td / rel_dir / tn).exists():
                return True

    return False


def scan_all(
    project_path: str,
    scan_types: list[str] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    """
    Run all (or selected) scan types and return results grouped by type.

    scan_types: list of 'todos', 'skipped_tests', 'failing_tests', 'stale_deps', 'coverage'
    """
    available = {
        "todos": scan_todos,
        "skipped_tests": scan_skipped_tests,
        "failing_tests": scan_failing_tests,
        "stale_deps": scan_stale_deps,
        "coverage": scan_coverage,
    }

    if scan_types is None:
        scan_types = list(available.keys())

    results: dict[str, list[dict[str, Any]]] = {}
    for st in scan_types:
        fn = available.get(st)
        if fn:
            results[st] = fn(project_path)

    return results
