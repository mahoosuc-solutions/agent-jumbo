"""
Unit tests for codebase_scanner — stateless discovery of work items from source code.
"""

import os
import shutil
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from instruments.custom.work_queue.codebase_scanner import (
    _make_id,
    _should_skip_dir,
    _walk_files,
    scan_all,
    scan_coverage,
    scan_skipped_tests,
    scan_todos,
)


def _write(path: str, content: str) -> None:
    """Write content to path, creating parent dirs as needed."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def _make_long_py(lines: int = 60) -> str:
    """Return a syntactically valid Python file body of the given line count."""
    body = ["# auto-generated source file\n", "def placeholder():\n", "    pass\n"]
    while len(body) < lines:
        body.append(f"# line {len(body)}\n")
    return "".join(body)


class TestMakeId:
    """Tests for the _make_id deterministic hashing helper."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_deterministic_same_inputs(self):
        id1 = _make_id("some/file.py", 10, "todo", "TODO: fix this")
        id2 = _make_id("some/file.py", 10, "todo", "TODO: fix this")
        assert id1 == id2

    def test_changes_with_different_file(self):
        id1 = _make_id("some/file.py", 10, "todo", "TODO: fix this")
        id2 = _make_id("other/file.py", 10, "todo", "TODO: fix this")
        assert id1 != id2

    def test_changes_with_different_line(self):
        id1 = _make_id("some/file.py", 10, "todo", "TODO: fix this")
        id2 = _make_id("some/file.py", 99, "todo", "TODO: fix this")
        assert id1 != id2

    def test_changes_with_different_source_type(self):
        id1 = _make_id("some/file.py", 10, "todo", "TODO: fix this")
        id2 = _make_id("some/file.py", 10, "fixme", "TODO: fix this")
        assert id1 != id2

    def test_returns_16_char_hex_string(self):
        result = _make_id("a.py", 1, "todo", "x")
        assert len(result) == 16
        assert all(c in "0123456789abcdef" for c in result)


class TestShouldSkipDir:
    """Tests for the _should_skip_dir directory filter."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_skips_known_ignore_dirs(self):
        for name in ("node_modules", "__pycache__", ".venv", "dist", "build", ".git"):
            assert _should_skip_dir(name) is True, f"Expected {name!r} to be skipped"

    def test_skips_dot_prefixed_dirs(self):
        assert _should_skip_dir(".hidden") is True
        assert _should_skip_dir(".cache") is True

    def test_allows_normal_dirs(self):
        for name in ("src", "tests", "python", "instruments", "lib", "api"):
            assert _should_skip_dir(name) is False, f"Expected {name!r} NOT to be skipped"


class TestWalkFiles:
    """Tests for the _walk_files generator."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_yields_files_in_directory(self):
        _write(os.path.join(self.tmpdir, "src", "app.py"), "x = 1\n")
        _write(os.path.join(self.tmpdir, "src", "util.py"), "y = 2\n")
        found = [rel for _, rel in _walk_files(self.tmpdir)]
        assert any("app.py" in p for p in found)
        assert any("util.py" in p for p in found)

    def test_extension_filter_limits_results(self):
        _write(os.path.join(self.tmpdir, "code.py"), "x = 1\n")
        _write(os.path.join(self.tmpdir, "readme.txt"), "hello\n")
        py_files = [rel for _, rel in _walk_files(self.tmpdir, {".py"})]
        assert any("code.py" in p for p in py_files)
        assert not any("readme.txt" in p for p in py_files)

    def test_skips_ignored_dirs(self):
        _write(os.path.join(self.tmpdir, "node_modules", "pkg", "index.js"), "module.exports = {};\n")
        _write(os.path.join(self.tmpdir, "__pycache__", "cached.py"), "# cached\n")
        _write(os.path.join(self.tmpdir, "src", "real.py"), "x = 1\n")
        found = [rel for _, rel in _walk_files(self.tmpdir)]
        assert not any("node_modules" in p for p in found)
        assert not any("__pycache__" in p for p in found)
        assert any("real.py" in p for p in found)


class TestScanTodos:
    """Tests for scan_todos."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_finds_todo_fixme_hack_xxx(self):
        content = (
            "x = 1  # TODO: clean this up\n"
            "y = 2  # FIXME: broken edge case\n"
            "z = 3  # HACK: workaround\n"
            "w = 4  # XXX: revisit later\n"
        )
        _write(os.path.join(self.tmpdir, "code.py"), content)
        results = scan_todos(self.tmpdir)
        tags = {r["title"].split(":")[0] for r in results}
        assert "TODO" in tags
        assert "FIXME" in tags
        assert "HACK" in tags
        assert "XXX" in tags

    def test_extracts_tag_and_comment_text(self):
        _write(os.path.join(self.tmpdir, "module.py"), "# TODO: refactor this function\n")
        results = scan_todos(self.tmpdir)
        assert len(results) == 1
        item = results[0]
        assert item["title"] == "TODO: refactor this function"
        assert item["source_type"] == "todo"
        assert item["source"] == "scanner"
        assert item["line_number"] == 1

    def test_fixme_uses_fixme_source_type(self):
        _write(os.path.join(self.tmpdir, "broken.py"), "# FIXME: this crashes on None\n")
        results = scan_todos(self.tmpdir)
        assert len(results) == 1
        assert results[0]["source_type"] == "fixme"

    def test_skips_non_code_extensions(self):
        _write(os.path.join(self.tmpdir, "notes.txt"), "# TODO: remember to do this\n")
        _write(os.path.join(self.tmpdir, "photo.png"), "# TODO: fake binary\n")
        results = scan_todos(self.tmpdir)
        # .txt and .png are not in CODE_EXTENSIONS
        assert len(results) == 0

    def test_finds_todos_in_yaml_and_toml(self):
        _write(os.path.join(self.tmpdir, "config.yaml"), "# TODO: add production values\nkey: value\n")
        results = scan_todos(self.tmpdir)
        assert any("TODO" in r["title"] for r in results)


class TestScanSkippedTests:
    """Tests for scan_skipped_tests."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_finds_pytest_mark_skip_in_py_test_file(self):
        content = "import pytest\n\n@pytest.mark.skip(reason='not implemented')\ndef test_something():\n    pass\n"
        _write(os.path.join(self.tmpdir, "test_feature.py"), content)
        results = scan_skipped_tests(self.tmpdir)
        assert len(results) == 1
        assert results[0]["source_type"] == "skipped_test"
        assert "test_feature.py" in results[0]["file_path"]

    def test_finds_it_skip_and_test_skip_in_js_test_file(self):
        content = (
            "describe('suite', () => {\n"
            "  it.skip('should do X', () => {});\n"
            "  test.skip('should do Y', () => {});\n"
            "});\n"
        )
        _write(os.path.join(self.tmpdir, "feature.test.js"), content)
        results = scan_skipped_tests(self.tmpdir)
        assert len(results) == 2
        for r in results:
            assert r["source_type"] == "skipped_test"

    def test_ignores_skip_patterns_in_non_test_files(self):
        # A regular Python source file (not named test_*) — should not be scanned
        content = "# @pytest.mark.skip — documenting pattern\nx = 1\n"
        _write(os.path.join(self.tmpdir, "helpers.py"), content)
        results = scan_skipped_tests(self.tmpdir)
        assert len(results) == 0

    def test_finds_xit_and_xdescribe_in_ts_spec_file(self):
        content = "xdescribe('disabled suite', () => {\n  xit('disabled test', () => {});\n});\n"
        _write(os.path.join(self.tmpdir, "widget.spec.ts"), content)
        results = scan_skipped_tests(self.tmpdir)
        assert len(results) == 2


class TestScanCoverage:
    """Tests for scan_coverage."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_finds_source_file_without_test(self):
        # Place a long-enough .py file in a key_dir
        src_path = os.path.join(self.tmpdir, "python", "api", "handlers.py")
        _write(src_path, _make_long_py(60))
        results = scan_coverage(self.tmpdir)
        assert any("handlers.py" in r["file_path"] for r in results)
        item = next(r for r in results if "handlers.py" in r["file_path"])
        assert item["source_type"] == "coverage"
        assert item["source"] == "scanner"

    def test_skips_files_below_min_lines_threshold(self):
        # A file with only 10 lines — should be ignored (< 50 lines)
        src_path = os.path.join(self.tmpdir, "python", "api", "tiny.py")
        _write(src_path, "x = 1\n" * 10)
        results = scan_coverage(self.tmpdir)
        assert not any("tiny.py" in r["file_path"] for r in results)

    def test_no_finding_when_test_file_exists(self):
        src_path = os.path.join(self.tmpdir, "python", "api", "parser.py")
        _write(src_path, _make_long_py(60))
        # Co-located test file matching the naming convention
        test_path = os.path.join(self.tmpdir, "python", "api", "test_parser.py")
        _write(test_path, "def test_placeholder(): pass\n")
        results = scan_coverage(self.tmpdir)
        assert not any("parser.py" in r["file_path"] and "test_" not in r["file_path"] for r in results)

    def test_no_finding_for_files_outside_key_dirs(self):
        # A file outside any key_dir should not produce a coverage finding
        src_path = os.path.join(self.tmpdir, "scripts", "migrate.py")
        _write(src_path, _make_long_py(60))
        results = scan_coverage(self.tmpdir)
        assert not any("migrate.py" in r["file_path"] for r in results)

    def test_instruments_custom_is_a_key_dir(self):
        src_path = os.path.join(self.tmpdir, "instruments", "custom", "my_tool.py")
        _write(src_path, _make_long_py(60))
        results = scan_coverage(self.tmpdir)
        assert any("my_tool.py" in r["file_path"] for r in results)


class TestScanAll:
    """Tests for scan_all orchestrator."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()

    def teardown_method(self):
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_returns_dict_grouped_by_type(self):
        # Plant a TODO so there is at least one finding
        _write(os.path.join(self.tmpdir, "code.py"), "# TODO: something\n")
        results = scan_all(self.tmpdir, scan_types=["todos", "skipped_tests", "coverage"])
        assert isinstance(results, dict)
        assert "todos" in results
        assert "skipped_tests" in results
        assert "coverage" in results
        assert isinstance(results["todos"], list)

    def test_scan_types_filter_limits_keys(self):
        results = scan_all(self.tmpdir, scan_types=["todos"])
        assert set(results.keys()) == {"todos"}

    def test_all_scan_types_run_when_none_specified(self):
        results = scan_all(self.tmpdir)
        expected_keys = {"todos", "skipped_tests", "failing_tests", "stale_deps", "coverage"}
        assert set(results.keys()) == expected_keys

    def test_unknown_scan_type_is_silently_ignored(self):
        results = scan_all(self.tmpdir, scan_types=["todos", "nonexistent_scanner"])
        assert "todos" in results
        assert "nonexistent_scanner" not in results
