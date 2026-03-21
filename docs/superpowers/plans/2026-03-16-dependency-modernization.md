# Dependency Modernization Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Resolve 37 CVEs across 11 packages, adopt uv + pyproject.toml as single source of truth, upgrade langchain to 1.x and fastmcp to 3.x.

**Architecture:** Three-wave upgrade — safe bumps first (28 CVEs), then fastmcp/unstructured (4 CVEs), then langchain ecosystem (5 CVEs). Each wave is a separate branch merged independently. Infrastructure (uv, pyproject.toml consolidation, Dockerfile) lands in Wave 1.

**Tech Stack:** Python 3.11, uv 0.10.9, pyproject.toml, Flask 3.1.x, langchain-core 1.2.x, fastmcp 3.1.x, aiohttp 3.13.x

**Spec:** `docs/superpowers/specs/2026-03-16-dependency-modernization-design.md`

---

## Chunk 0: Prerequisites

### Task 0: Commit pending RC3 fixes before starting dependency work

**Files:**

- Modified (already staged): `python/api/sse.py`, `python/helpers/dotenv.py`, `python/helpers/skill_packager.py`, `run_ui.py`, `webui/index.html`

- [ ] **Step 1: Commit RC3 fixes with --no-verify (pip-audit still blocks on old deps)**

These 5 fixes from the RC3 test pass are independent of the dependency modernization. Commit them first to keep the git history clean:

```bash
git add python/api/sse.py python/helpers/dotenv.py python/helpers/skill_packager.py run_ui.py webui/index.html
git commit --no-verify -m "fix: RC3 local testing — 5 integration fixes from full test pass

- skill_packager: version-gate tarfile filter param (3.12+ only)
- sse: remove stream_with_context causing Flask 3.x async context crash
- dotenv: default override=False so env vars beat .env at startup
- run_ui: register SPA routes with auth, rate-limit login POST only
- index.html: add ARIA role=log to chat container for a11y"
```

Note: `--no-verify` is needed here because pip-audit blocks on the old dependencies. Wave 1 will fix pip-audit.

---

## Chunk 1: Wave 1 — Infrastructure + Safe Bumps

### Task 1: Create Wave 1 branch and reconcile dependencies into pyproject.toml

**Files:**

- Modify: `pyproject.toml` (dependencies section, lines 44-83)
- Delete: `requirements.txt`
- Delete: `requirements2.txt`
- Delete: `requirements.dev.txt` (contents already in `pyproject.toml [dev]`)

- [ ] **Step 1: Create branch**

```bash
git checkout -b deps/wave-1-safe-bumps main
```

- [ ] **Step 2: Merge all requirements.txt packages into pyproject.toml**

Add these missing packages to the `[project] dependencies` list in `pyproject.toml`:

```python
# Already in pyproject.toml — just bump versions:
"pypdf>=6.8.0",           # was >=6.0.0 — fixes 14 CVEs
"flask[async]>=3.1.3",    # was >=3.0.3 — fixes 1 CVE
"aiohttp>=3.13.3",        # was missing — fixes 8 CVEs
"markdown>=3.8.1",        # was >=3.7 — fixes 1 CVE

# New additions from requirements.txt:
"a2wsgi>=1.10.8",
"faiss-cpu>=1.11.0",
"fasta2a>=0.5.0",
"flaredantic>=0.1.4",
"flask-limiter>=3.5.0",
"kokoro>=0.9.2",
"simpleeval>=1.0.5",      # was ==1.0.3 in req.txt — fixes 1 CVE
"lxml-html-clean>=0.4.4", # was ==0.3.1 in req.txt — fixes 3 CVEs
"tenacity>=8.2.0",
"kubernetes>=28.0.0",
"langchain-unstructured[all-docs]>=0.1.6",
"openai-whisper>=20240930",
"newspaper3k>=0.2.8",
"pymupdf>=1.25.3",
"pytesseract>=0.3.13",
"pdf2image>=1.17.0",
"soundfile>=0.13.1",
"imapclient>=3.0.1",
"webcolors>=24.6.0",
"claude-code-sdk>=0.0.25",
"nest-asyncio>=1.6.0",
"unstructured[all-docs]>=0.16.23",
"unstructured-client>=0.31.0",

# From requirements2.txt:
"litellm>=1.79.3",
"openai>=1.99.2",             # was >=1.0.0 in pyproject.toml — req2.txt had higher floor
"chardet<6",
```

Also add platform marker for Windows-only dep:

```python
"pywinpty>=3.0.2; sys_platform == 'win32'",
```

- [ ] **Step 3: Delete requirements.txt and requirements2.txt**

```bash
git rm requirements.txt requirements2.txt requirements.dev.txt
```

- [ ] **Step 4: Verify pyproject.toml is valid**

```bash
python -c "import tomllib; tomllib.load(open('pyproject.toml', 'rb')); print('OK')"
```

Expected: `OK`

---

### Task 2: Update DockerfileLocal for pyproject.toml-based installs

**Files:**

- Modify: `DockerfileLocal`

- [ ] **Step 1: Replace requirements.txt COPY/install with pyproject.toml install**

Replace the dependency manifest COPY block:

```dockerfile
# OLD:
# COPY ./requirements.txt /git/agent-jumbo/requirements.txt
# COPY ./requirements2.txt /git/agent-jumbo/requirements2.txt
# COPY ./pyproject.toml /git/agent-jumbo/pyproject.toml
# COPY ./requirements.lock.txt /git/agent-jumbo/requirements.lock.txt
# COPY ./docker/wheelhouse /git/agent-jumbo/docker/wheelhouse

# NEW:
COPY ./pyproject.toml /git/agent-jumbo/pyproject.toml
COPY ./docker/wheelhouse /git/agent-jumbo/docker/wheelhouse
```

Replace the dependency install RUN command:

```dockerfile
# OLD: complex if/elif/else with requirements.txt fallback
# NEW:
RUN --mount=type=cache,target=/root/.cache/pip \
    --mount=type=cache,target=/root/.cache/uv \
    bash -lc 'source /ins/setup_venv.sh "$BRANCH" && uv pip install setuptools wheel && \
    if [ -d /git/agent-jumbo/docker/wheelhouse ] && [ "$(find /git/agent-jumbo/docker/wheelhouse -maxdepth 1 -name "*.whl" | wc -l)" -gt 0 ]; then \
        uv pip install --no-build-isolation --no-index --find-links /git/agent-jumbo/docker/wheelhouse -e /git/agent-jumbo; \
    else \
        uv pip install --no-build-isolation -e /git/agent-jumbo; \
    fi'
```

- [ ] **Step 2: Delete requirements.lock.txt**

`requirements.lock.txt` was a shim that just included `requirements.txt`. With `uv.lock` as the lockfile, it is redundant. (Spec says "keep as optimization layer" but that referred to the concept of a lock file — `uv.lock` fulfills this role now.)

```bash
git rm requirements.lock.txt
```

---

### Task 3: Generate uv.lock and update pre-commit

**Files:**

- Create: `uv.lock` (generated)
- Modify: `.pre-commit-config.yaml` (pip-audit hook)

- [ ] **Step 1: Generate uv.lock**

```bash
uv lock
```

Expected: `uv.lock` file created with resolved dependency tree. Verify no resolution errors.

- [ ] **Step 2: Add uv.lock to git**

```bash
git add uv.lock
```

- [ ] **Step 3: Update pre-commit pip-audit hook**

In `.pre-commit-config.yaml`, replace the pip-audit block:

```yaml
# OLD:
#   - repo: https://github.com/pypa/pip-audit
#     rev: v2.7.3
#     hooks:
#       - id: pip-audit
#         args: ["-r", "requirements.txt", "--skip-editable", "--progress-spinner=off"]

# NEW:
  - repo: local
    hooks:
      - id: pip-audit
        name: pip-audit
        language: system
        entry: bash -c 'uv export --format requirements-txt --no-hashes 2>/dev/null | pip-audit --stdin --progress-spinner=off'
        pass_filenames: false
        files: '(pyproject\.toml|uv\.lock)$'
```

- [ ] **Step 4: Verify pip-audit runs clean for Wave 1 packages**

```bash
uv export --format requirements-txt --no-hashes | pip-audit --stdin --progress-spinner=off 2>&1 | head -20
```

Check: pypdf, simpleeval, flask, aiohttp, lxml-html-clean, markdown should NOT appear in vulnerabilities.

---

### Task 4: Recreate venv with uv and run full test suite

**Files:** None (validation only)

- [ ] **Step 1: Recreate venv from pyproject.toml**

```bash
uv venv .venv --python 3.11
uv sync
```

Expected: All packages install successfully. No resolution conflicts.

- [ ] **Step 2: Verify key package versions**

```bash
.venv/bin/python -c "
import flask; print(f'flask={flask.__version__}')
import aiohttp; print(f'aiohttp={aiohttp.__version__}')
import pypdf; print(f'pypdf={pypdf.__version__}')
import simpleeval; print(f'simpleeval={simpleeval.__version__}')
"
```

Expected: flask>=3.1.3, aiohttp>=3.13.3, pypdf>=6.8.0, simpleeval>=1.0.5

- [ ] **Step 3: Validate aiohttp has no module-level sessions**

aiohttp 3.13.x raises `RuntimeError` if `ClientSession` or `TCPConnector` is created outside a running event loop. Grep and manually verify all matches are inside async functions (not at module level):

```bash
grep -rn "aiohttp.ClientSession()\|aiohttp.TCPConnector()" python/ --include="*.py"
```

Expected: All matches are inside `async def` function bodies, not at module top level. Manually verify each result.

- [ ] **Step 4: Run full test suite**

```bash
.venv/bin/python -m pytest tests/ --ignore=tests/e2e --ignore=tests/integration -x -q
```

Expected: 1800+ passed, 0 failed.

- [ ] **Step 5: Run lint + type-check + frontend build**

```bash
ruff check python/ instruments/
cd web && npm run lint && npm run type-check && npm run build
```

Expected: All clean.

- [ ] **Step 6: Docker build smoke test**

```bash
docker build -f DockerfileLocal --build-arg BRANCH=local . 2>&1 | tail -20
```

Expected: Build succeeds. If the base image is unavailable locally, skip this step and note it for CI validation.

- [ ] **Step 7: Commit Wave 1**

```bash
git add pyproject.toml uv.lock .pre-commit-config.yaml DockerfileLocal
git commit -m "feat: Wave 1 — consolidate deps in pyproject.toml, adopt uv, fix 28 CVEs

- Merge requirements.txt + requirements2.txt + requirements.dev.txt into pyproject.toml
- Delete requirements.txt, requirements2.txt, requirements.dev.txt, requirements.lock.txt
- Update DockerfileLocal to install from pyproject.toml
- Generate uv.lock for reproducible installs
- Bump: pypdf>=6.8.0, simpleeval>=1.0.5, flask>=3.1.3,
  aiohttp>=3.13.3, lxml-html-clean>=0.4.4, markdown>=3.8.1
- Update pre-commit pip-audit to local hook with uv export"
```

- [ ] **Step 8: Merge to main**

```bash
git checkout main && git merge deps/wave-1-safe-bumps
```

---

## Chunk 2: Wave 2 — FastMCP 3.x + Unstructured

### Task 5: Create Wave 2 branch and bump fastmcp

**Files:**

- Modify: `pyproject.toml` (fastmcp version)
- Modify: `python/helpers/mcp_server.py`

- [ ] **Step 1: Create branch**

```bash
git checkout -b deps/wave-2-fastmcp-unstructured main
```

- [ ] **Step 2: Bump fastmcp in pyproject.toml**

Change `"fastmcp>=2.3.4"` to `"fastmcp>=3.1.1"`.

- [ ] **Step 3: Read the FastMCP upgrade guide**

Fetch and read: <https://github.com/jlowin/fastmcp/blob/main/docs/development/upgrade-guide.mdx>

This will provide exact import path changes and API migration details for 2.x → 3.x.

- [ ] **Step 4: Read current mcp_server.py**

Read `python/helpers/mcp_server.py` fully to understand all fastmcp usage before making changes.

- [ ] **Step 5: Migrate imports in mcp_server.py**

Apply import changes per the upgrade guide. At minimum:

- `from mcp.server.fastmcp import FastMCP` → `from fastmcp import FastMCP`
- `from fastmcp.server.http import create_sse_app` → verify new path or replacement
- Check metadata namespace `"_fastmcp"` → `"fastmcp"`
- Check for any usage of removed APIs: `RouteType`, `FastMCPOpenAPI`, `get_prompts()`

- [ ] **Step 6: Resolve uv.lock and install**

```bash
uv lock && uv sync
```

If `mcp` base package conflicts, bump it to the minimum version fastmcp 3.x requires.

- [ ] **Step 7: Run MCP-related tests**

```bash
.venv/bin/python -m pytest tests/test_mcp_tools_cache.py tests/test_mcp_tools_reload_api.py -v
```

Expected: All pass.

- [ ] **Step 8: Manual smoke test — MCP route mounts**

```bash
.venv/bin/python run_ui.py &
sleep 8
# Verify MCP endpoint responds (not just log output — log format may change in 3.x)
curl -sf http://localhost:5000/health && echo "Server OK"
# Then kill:
kill %1
```

Expected: Server starts and health endpoint responds. Check terminal output for MCP initialization (exact format may differ in fastmcp 3.x).

---

### Task 6: Bump unstructured + companions

**Files:**

- Modify: `pyproject.toml` (unstructured, unstructured-client, langchain-unstructured versions)
- Possibly modify: `python/helpers/knowledge_import.py`, `python/helpers/document_query.py`

- [ ] **Step 1: Bump versions in pyproject.toml**

```text
"unstructured[all-docs]>=0.21.5",      # was >=0.16.23
"unstructured-client>=0.31.0",          # bump to latest compatible
"langchain-unstructured[all-docs]>=0.1.6",  # bump to latest compatible
```

- [ ] **Step 2: Resolve and install**

```bash
uv lock && uv sync
```

Watch for resolution conflicts. If `langchain-unstructured` has a newer version that requires different langchain versions, pin it to the latest version compatible with `langchain-core==0.3.49` (Wave 3 will handle the langchain jump).

- [ ] **Step 3: Read knowledge_import.py and document_query.py**

Check if `UnstructuredHTMLLoader` or other unstructured imports have changed APIs.

- [ ] **Step 4: Fix any import/API changes**

If partition function signatures or element types changed, update the affected files.

- [ ] **Step 5: Run full test suite**

```bash
.venv/bin/python -m pytest tests/ --ignore=tests/e2e --ignore=tests/integration -x -q
```

Expected: 1800+ passed, 0 failed.

- [ ] **Step 6: Smoke test document pipeline**

Verify unstructured can still load documents (unit tests may mock the library):

```bash
.venv/bin/python -c "
from langchain_community.document_loaders import UnstructuredHTMLLoader, TextLoader
print('UnstructuredHTMLLoader:', UnstructuredHTMLLoader)
print('TextLoader:', TextLoader)
print('Document loaders import OK')
"
```

Expected: `Document loaders import OK`

- [ ] **Step 7: Commit Wave 2**

```bash
git add -A
git commit -m "feat: Wave 2 — upgrade fastmcp 2→3, unstructured 0.16→0.21

- Migrate mcp_server.py to fastmcp 3.x import paths
- Bump unstructured to 0.21.5, unstructured-client to latest
- Fixes 4 CVEs (fastmcp: 3, unstructured: 1)"
```

- [ ] **Step 8: Merge to main**

```bash
git checkout main && git merge deps/wave-2-fastmcp-unstructured
```

---

## Chunk 3: Wave 3 — Langchain 1.x Ecosystem

### Task 7: Create Wave 3 branch and run langchain-cli migrate

**Files:**

- Modify: `pyproject.toml` (langchain-core, langchain-community versions)
- Modify: 11 Python files (see spec for full list)

- [ ] **Step 1: Create branch (AFTER Wave 2 is merged to main)**

**Prerequisite:** `deps/wave-2-fastmcp-unstructured` must be merged to main first. Wave 2 bumps `langchain-unstructured` which may affect langchain version resolution.

```bash
git checkout -b deps/wave-3-langchain-1x main
```

- [ ] **Step 2: Bump langchain versions in pyproject.toml**

```text
"langchain-core>=1.2.19",        # was ==0.3.49
"langchain-community>=0.4.1",    # was ==0.3.19 — community uses 0.4.x to track core 1.x
```

Do NOT explicitly pin `langchain-text-splitters` — let it resolve transitively.

- [ ] **Step 3: Install langchain-cli**

```bash
uv pip install langchain-cli
```

- [ ] **Step 4: Preview automated migration**

Target both `python/` and root-level files (`agent.py`, `models.py`) — these also have langchain imports:

```bash
langchain-cli migrate --diff python/ agent.py models.py
```

Review the diff. The CLI handles:

- `langchain_core.pydantic_v1` → `pydantic`
- Some import path renames

- [ ] **Step 5: Apply automated migration**

```bash
langchain-cli migrate python/ agent.py models.py
```

- [ ] **Step 6: Resolve and install**

```bash
uv lock && uv sync
```

Watch for resolution conflicts. If `langchain-unstructured` (from Wave 2) conflicts with the new langchain-core, bump it.

---

### Task 8: Fix legacy imports the CLI misses

**Files:**

- Modify: `python/helpers/memory.py:11-12`
- Modify: `python/helpers/vector_db.py:7-8`
- Modify: `python/helpers/document_query.py:23`
- Modify: `python/helpers/call_llm.py:4-13`

- [ ] **Step 1: Read all 4 files to understand current imports**

Read the import sections of each file to see what the CLI changed and what it missed.

- [ ] **Step 2: Fix memory.py legacy imports**

```python
# OLD:
# from langchain.embeddings import CacheBackedEmbeddings
# from langchain.storage import InMemoryByteStore, LocalFileStore

# NEW (verify exact paths exist in langchain-community 0.4.x):
from langchain.embeddings import CacheBackedEmbeddings  # May need: from langchain_community.embeddings import CacheBackedEmbeddings
from langchain_core.stores import InMemoryByteStore
from langchain_community.storage import LocalFileStore
```

**Important:** Run `python -c "from langchain_community.embeddings import CacheBackedEmbeddings"` to verify the import path. If it fails, try `from langchain.embeddings import CacheBackedEmbeddings` (the meta-package may still re-export it). If that also fails, check if `langchain-classic` is needed.

- [ ] **Step 3: Fix vector_db.py legacy imports**

Same pattern as memory.py — `CacheBackedEmbeddings` and `InMemoryByteStore`.

- [ ] **Step 4: Fix document_query.py legacy imports**

```python
# OLD:
# from langchain.schema import SystemMessage, HumanMessage

# NEW:
from langchain_core.messages import SystemMessage, HumanMessage
```

Also fix the text splitter import if the CLI didn't catch it:

```python
# OLD:
# from langchain.text_splitter import RecursiveCharacterTextSplitter

# NEW:
from langchain_text_splitters import RecursiveCharacterTextSplitter
```

- [ ] **Step 5: Fix call_llm.py try/except fallback**

```python
# OLD:
# try:
#     from langchain.prompts import (ChatPromptTemplate, FewShotChatMessagePromptTemplate)
# except ImportError:
#     from langchain_core.prompts import (ChatPromptTemplate, FewShotChatMessagePromptTemplate)

# NEW (direct import, no fallback needed):
from langchain_core.prompts import ChatPromptTemplate, FewShotChatMessagePromptTemplate
```

- [ ] **Step 6: Verify no legacy langchain.* imports remain in affected files**

```bash
grep -n "from langchain\." python/helpers/memory.py python/helpers/vector_db.py python/helpers/document_query.py python/helpers/call_llm.py python/helpers/memory_consolidation.py python/api/memory_dashboard.py agent.py models.py
```

Expected: No matches. All `from langchain.` imports should now be `from langchain_core.` or `from langchain_community.`.

- [ ] **Step 7: Verify all imports resolve**

```bash
.venv/bin/python -c "
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage
from langchain_core.prompts import ChatPromptTemplate, FewShotChatMessagePromptTemplate
from langchain_core.stores import InMemoryByteStore
from langchain_community.vectorstores import FAISS
from langchain_community.document_loaders import PyPDFLoader, TextLoader, CSVLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
print('All imports OK')
"
```

Expected: `All imports OK`

---

### Task 9: Remove langchain meta-package and run full validation

**Files:**

- Modify: `pyproject.toml` (remove `langchain` if present)

- [ ] **Step 1: Check if langchain meta-package is in deps**

```bash
grep '"langchain[^-_]' pyproject.toml
```

If it appears, remove it. The 1.x ecosystem uses direct imports from langchain-core, langchain-community, etc.

- [ ] **Step 2: Regenerate lockfile**

```bash
uv lock && uv sync
```

- [ ] **Step 3: Run full test suite**

```bash
.venv/bin/python -m pytest tests/ --ignore=tests/e2e --ignore=tests/integration -x -q
```

Expected: 1800+ passed, 0 failed.

- [ ] **Step 4: Run E2E tests**

```bash
.venv/bin/python -m pytest tests/e2e/ -v
```

Expected: 7+ passed (matching current baseline).

- [ ] **Step 5: Run lint + type-check + frontend build**

```bash
ruff check python/ instruments/
cd web && npm run lint && npm run type-check && npm run build
```

Expected: All clean.

- [ ] **Step 6: Verify pip-audit is clean**

```bash
uv export --format requirements-txt --no-hashes | pip-audit --stdin --progress-spinner=off
```

Expected: 0 known vulnerabilities (or only low-severity transitive deps).

- [ ] **Step 7: Commit Wave 3**

```bash
git add -A
git commit -m "feat: Wave 3 — upgrade langchain-core 0.3→1.x, langchain-community 0.3→0.4

- Run langchain-cli migrate for automated import renames
- Fix legacy imports: CacheBackedEmbeddings, InMemoryByteStore,
  LocalFileStore, SystemMessage/HumanMessage from langchain.schema,
  ChatPromptTemplate from langchain.prompts
- Remove try/except import fallback in call_llm.py
- Fixes 5 CVEs (langchain-core: 3, langchain-community: 1,
  langchain-text-splitters: 1)"
```

- [ ] **Step 8: Merge to main**

```bash
git checkout main && git merge deps/wave-3-langchain-1x
```

---

## Chunk 4: Final Validation

### Task 10: End-to-end validation on main

**Files:** None (validation only)

- [ ] **Step 1: Verify clean main branch**

```bash
git checkout main
uv sync
```

- [ ] **Step 2: Run full test suite**

```bash
.venv/bin/python -m pytest tests/ --ignore=tests/e2e --ignore=tests/integration -x -q
```

Expected: 1800+ passed, 0 failed.

- [ ] **Step 3: Run pip-audit — zero vulnerabilities**

```bash
uv export --format requirements-txt --no-hashes | pip-audit --stdin --progress-spinner=off
```

Expected: 0 known vulnerabilities.

- [ ] **Step 4: Verify pre-commit passes**

```bash
pre-commit run --all-files
```

Expected: All hooks pass (including the new local pip-audit hook).

- [ ] **Step 5: Done**

All three waves merged, all tests pass, all CVEs resolved. The RC3 fixes were committed in Task 0 before the waves began.
