# Agent-Zero → Agent-Jumbo Full Rebrand Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rename all references from agent-jumbo/Agent Jumbo/a0 to agent-jumbo/Agent Jumbo/aj across the entire codebase, completing the clean fork break from upstream.

**Architecture:** Systematic find-and-replace across 7 layers: Docker infrastructure, container paths, Python code, JavaScript/HTML UI, prompts/knowledge, scripts/configs, and directory structure. Each layer is committed independently for clean git history and easy rollback.

**Tech Stack:** sed, Python scripts for complex renames, git

**Naming Convention:**

| Old | New | Context |
|-----|-----|---------|
| `agent-jumbo` | `agent-jumbo` | Kebab-case (Docker, URLs, filenames) |
| `agent_jumbo` | `agent_jumbo` | Snake_case (Python, env vars) |
| `Agent Jumbo` | `Agent Jumbo` | Display name (UI, docs) |
| `AgentZero` | `AgentJumbo` | PascalCase (if any) |
| `agent0` | `agent-jumbo` | Agent directory name |
| `/aj/` `/a0` | `/aj/` `/aj` | Container internal path |
| `.a0proj` | `.ajproj` | Project metadata directory |
| `agent_jumbo_data` | `agent_jumbo_data` | Docker volume name |
| `agent-jumbo-local` | `agent-jumbo:latest` | Docker image name |
| `agent0ai/agent-jumbo-base` | kept as-is | Base image (external dependency — rename later if we build our own base) |

**IMPORTANT EXCLUSIONS:**

- `docker/run/agent-jumbo/` — Will be REMOVED entirely (upstream copy)
- `logs/*.html` — Historical logs, not worth touching
- `.git/` — Never touch
- `__pycache__/` — Will be regenerated
- `ollama_models/`, `.buildx-cache/`, `memory/embeddings/` — Binary blobs with SHA hashes in names, not "a0" references

---

### Task 1: Remove Upstream Copy + Remote

**Files:**

- Remove: `docker/run/agent-jumbo/` (entire directory)
- Modify: `.git/config` (remove upstream remote)

- [ ] **Step 1: Remove the upstream git remote**

```bash
git remote remove upstream
```

- [ ] **Step 2: Remove the upstream agent-jumbo directory**

```bash
rm -rf docker/run/agent-jumbo/
```

Note: This directory is root-owned from Docker. May need `sudo rm -rf docker/run/agent-jumbo/`.

- [ ] **Step 3: Commit**

```bash
git add -A docker/run/agent-jumbo/
git commit -m "chore: remove upstream agent-jumbo copy — clean fork break"
```

---

### Task 2: Docker Infrastructure Rename

**Files:**

- Modify: `docker/run/docker-compose.yml`
- Modify: `docker/run/fs/exe/run_A0.sh` → rename to `run_aj.sh`
- Modify: `docker/run/fs/exe/run_tunnel_api.sh`
- Modify: `docker/run/fs/ins/install_A0.sh` → rename to `install_aj.sh`
- Modify: `docker/run/fs/ins/install_A02.sh` → rename to `install_aj2.sh`
- Modify: `docker/run/fs/ins/copy_A0.sh` → rename to `copy_aj.sh`
- Modify: `docker/run/fs/ins/install_playwright.sh`
- Modify: `docker/run/build.txt`
- Modify: `docker/run/Dockerfile`
- Modify: `docker/build-fast.sh`
- Modify: `docker/build-base-local.sh`
- Modify: `docker/base/build.txt`

- [ ] **Step 1: Update docker-compose.yml**

In `docker/run/docker-compose.yml`:

- Service name: `agent-jumbo` → `agent-jumbo`
- Container name: `agent-jumbo` → `agent-jumbo`
- Image: `agent-jumbo-local:latest` → `agent-jumbo:latest`
- Volume: `./agent-jumbo:/a0` → `./agent-jumbo:/aj`
- Volume name: `agent_jumbo_data` → `agent_jumbo_data`
- Named volume definition: `agent_jumbo_data` → `agent_jumbo_data`
- Mount path: `/aj/data` → `/aj/data`

- [ ] **Step 2: Update Dockerfile**

In `docker/run/Dockerfile`:

- All `/a0` paths → `/aj`
- References to `install_A0.sh` → `install_aj.sh`
- References to `install_A02.sh` → `install_aj2.sh`
- References to `copy_A0.sh` → `copy_aj.sh`
- References to `run_A0.sh` → `run_aj.sh`

- [ ] **Step 3: Rename and update shell scripts in fs/**

```bash
# Rename files
git mv docker/run/fs/exe/run_A0.sh docker/run/fs/exe/run_aj.sh
git mv docker/run/fs/ins/install_A0.sh docker/run/fs/ins/install_aj.sh
git mv docker/run/fs/ins/install_A02.sh docker/run/fs/ins/install_aj2.sh
git mv docker/run/fs/ins/copy_A0.sh docker/run/fs/ins/copy_aj.sh
```

Then update content inside each script:

- `run_aj.sh`: `/aj/` → `/aj/`
- `run_tunnel_api.sh`: `/aj/` → `/aj/`
- `install_aj.sh`: all `/a0` paths → `/aj`, any "agent-jumbo" references → "agent-jumbo"
- `install_aj2.sh`: same
- `copy_aj.sh`: `/a0` → `/aj`
- `install_playwright.sh`: `/a0` → `/aj`

- [ ] **Step 4: Update build scripts**

- `docker/build-fast.sh`: `agent-jumbo` → `agent-jumbo`, image names
- `docker/build-base-local.sh`: `agent-jumbo` → `agent-jumbo`
- `docker/base/build.txt`: `agent-jumbo` → `agent-jumbo`
- `docker/run/build.txt`: `agent-jumbo` → `agent-jumbo`

- [ ] **Step 5: Commit**

```bash
git add docker/
git commit -m "feat(docker): rename agent-jumbo → agent-jumbo across all Docker infrastructure"
```

---

### Task 3: Python Code — /aj/ Path References

**Files (project's own code, NOT upstream copy):**

- `python/helpers/files.py` (5 refs)
- `python/helpers/backup.py` (2 refs)
- `python/helpers/docker.py` (1 ref)
- `python/helpers/update_check.py` (1 ref)
- `python/helpers/email_client.py` (3 refs)
- `python/helpers/settings_core.py` (1 ref)
- `python/helpers/skill_registry.py` (1 ref)
- `python/helpers/cowork.py` (1 ref)
- `python/helpers/db_manager.py` (2 refs)
- `python/helpers/projects.py` (`.a0proj` → `.ajproj`)
- `python/api/api_files_get.py` (4 refs)
- `python/api/message.py` (1 ref)
- `python/api/api_message.py` (1 ref)
- `python/api/get_work_dir_files.py` (1 ref)
- `python/api/cowork_folders_set.py` (2 refs)
- `python/tools/diagram_tool.py` (3 refs)
- `python/tools/portfolio_manager_tool.py` (1 ref)
- `instruments/custom/diagram_generator/test_diagrams.py` (1 ref)
- `instruments/default/yt_download/yt_download.sh` (1 ref)

- [ ] **Step 1: Run sed replacement for /aj/ → /aj/ in Python files**

```bash
# Replace /aj/ with /aj/ and /a0 (end of string/line) with /aj
find python/ instruments/ -name "*.py" -exec sed -i 's|/aj/|/aj/|g; s|/a0"|/aj"|g; s|/a0$|/aj|g' {} +
```

- [ ] **Step 2: Update .a0proj → .ajproj**

In `python/helpers/projects.py`:

```python
PROJECT_META_DIR = ".ajproj"
```

- [ ] **Step 3: Update yt_download.sh**

```bash
sed -i 's|/aj/|/aj/|g' instruments/default/yt_download/yt_download.sh
```

- [ ] **Step 4: Run tests to verify nothing broke**

```bash
python -m pytest tests/ -k "not e2e" -q --tb=short 2>&1 | tail -10
```

- [ ] **Step 5: Commit**

```bash
git add python/ instruments/
git commit -m "refactor: rename /aj/ container paths to /aj/ in Python code"
```

---

### Task 4: Python Code — agent-jumbo/agent_jumbo Name References

**Files:**

- `python/helpers/api.py` (1 ref — Flask app name)
- `python/helpers/backup.py` (6 refs — backup paths/names)
- `python/helpers/update_check.py` (1 ref — GitHub repo URL)
- `python/helpers/fasta2a_server.py` (3 refs — A2A agent name)
- `python/helpers/settings_ui.py` (1 ref)
- `python/api/passkey_auth.py` (1 ref)
- `models.py` (1 ref)
- `instruments/custom/project_scaffold/scaffold_manager.py` (5 refs)
- `instruments/custom/claude_sdk/__init__.py` (1 ref)
- `instruments/custom/claude_sdk/sdk_manager.py` (7 refs)
- `instruments/custom/customer_lifecycle/lifecycle_manager.py` (3 refs)
- `instruments/custom/ai_migration/migration_manager.py` (1 ref)
- `instruments/custom/skill_importer/__init__.py` (1 ref)
- `instruments/custom/skill_importer/importer_manager.py` (7 refs)
- `instruments/custom/plugin_marketplace/marketplace_manager.py` (1 ref)
- `instruments/custom/knowledge_ingest/knowledge_ingest_manager.py` (1 ref)
- `instruments/custom/diagram_generator/generate_drawio.py` (1 ref)
- `instruments/custom/diagram_generator/generate_excalidraw.py` (1 ref)
- `instruments/custom/diagram_generator/test_diagrams.py` (1 ref)
- `instruments/custom/_TEMPLATE/template_db.py` (1 ref)
- `instruments/custom/_TEMPLATE/template_manager.py` (1 ref)
- `tests/test_sales_generator_db.py` (1 ref)
- `tests/e2e/conftest.py` (1 ref)
- `tests/e2e/test_security.py` (1 ref)
- `tests/e2e/test_performance.py` (1 ref)
- `tests/e2e/test_functional.py` (1 ref)
- `tests/e2e/test_accessibility.py` (1 ref)

- [ ] **Step 1: Bulk sed replacement across Python files**

```bash
# Case-sensitive replacements
find . -maxdepth 1 -name "*.py" -exec sed -i 's/agent-jumbo/agent-jumbo/g; s/agent_jumbo/agent_jumbo/g; s/Agent Jumbo/Agent Jumbo/g; s/AgentZero/AgentJumbo/g' {} +
find python/ instruments/ tests/ -name "*.py" -exec sed -i 's/agent-jumbo/agent-jumbo/g; s/agent_jumbo/agent_jumbo/g; s/Agent Jumbo/Agent Jumbo/g; s/AgentZero/AgentJumbo/g' {} +
```

- [ ] **Step 2: Special case — update_check.py GitHub URL**

Verify `python/helpers/update_check.py` — the GitHub repo URL `agent0ai/agent-jumbo` should be updated to point to your fork or disabled entirely since we're no longer tracking upstream.

- [ ] **Step 3: Run tests**

```bash
python -m pytest tests/ -k "not e2e" -q --tb=short 2>&1 | tail -10
```

- [ ] **Step 4: Commit**

```bash
git add *.py python/ instruments/ tests/
git commit -m "refactor: rename agent-jumbo → agent-jumbo in all Python code"
```

---

### Task 5: JavaScript, HTML, and JSON — UI Branding

**Files:**

- `webui/components/welcome/welcome-store.js` (2 refs — welcome message)
- `webui/components/settings/external/passkey-auth-store.js` (1 ref)
- `webui/components/projects/projects-store.js` (1 ref — `/aj/` path)
- `webui/components/chat/attachments/attachmentsStore.js` (2 refs — `/aj/` path)
- `webui/components/settings/cowork/cowork-manager-store.js` (1 ref — `/aj/` path)
- `webui/components/settings/external/api-examples.html` (4 refs — `/aj/` path)
- `.mcp.json` (1 ref)
- `.devcontainer/devcontainer.json` (4 refs — `/aj/` path)
- `app_spec/acceptance_tests.json` (2 refs)
- `tmp/settings.json` (1 ref)
- `memory/default/knowledge_import.json` (1 ref)
- Workflow engine JSON schemas and templates (6 files with refs)

- [ ] **Step 1: Bulk sed replacement across JS/HTML/JSON**

```bash
find webui/ -name "*.js" -o -name "*.html" | xargs sed -i 's/agent-jumbo/agent-jumbo/g; s/agent_jumbo/agent_jumbo/g; s/Agent Jumbo/Agent Jumbo/g; s|/aj/|/aj/|g; s|/a0"|/aj"|g'

# JSON files
find . -maxdepth 1 -name "*.json" -exec sed -i 's/agent-jumbo/agent-jumbo/g; s/agent_jumbo/agent_jumbo/g; s/Agent Jumbo/Agent Jumbo/g; s|/aj/|/aj/|g' {} +
find .devcontainer/ app_spec/ memory/ instruments/ -name "*.json" -exec sed -i 's/agent-jumbo/agent-jumbo/g; s/agent_jumbo/agent_jumbo/g; s/Agent Jumbo/Agent Jumbo/g; s|/aj/|/aj/|g' {} +
```

- [ ] **Step 2: Verify JSON validity**

```bash
find . -name "*.json" -not -path "./.git/*" -not -path "*/node_modules/*" -exec python3 -c "import json,sys; json.load(open(sys.argv[1]))" {} \; 2>&1 | head -20
```

- [ ] **Step 3: Commit**

```bash
git add webui/ .mcp.json .devcontainer/ app_spec/ memory/ instruments/ tmp/
git commit -m "feat(ui): rebrand Agent Jumbo → Agent Jumbo in all UI and JSON files"
```

---

### Task 6: Prompts, Knowledge, and Agent Configs

**Files:**

- `prompts/agent.system.main.role.md` (1 ref)
- `prompts/agent.system.main.environment.md` (1 ref)
- `prompts/agent.system.tool.linear_integration.md` (1 ref)
- `agents/agent0/prompts/agent.system.main.role.md` (1 ref)
- `agents/hacker/prompts/agent.system.main.role.md` (1 ref)
- `agents/hacker/prompts/agent.system.main.environment.md` (1 ref)
- `knowledge/default/main/about/installation.md` (14 refs)
- `knowledge/default/main/about/github_readme.md` (2 refs)
- `conf/model_providers.yaml` (3 refs)

- [ ] **Step 1: Rename agent0 directory**

```bash
git mv agents/agent0 agents/agent-jumbo
```

- [ ] **Step 2: Bulk sed replacement in prompts, knowledge, agents, conf**

```bash
find prompts/ agents/ knowledge/ conf/ -type f \( -name "*.md" -o -name "*.yaml" -o -name "*.yml" \) -exec sed -i 's/agent-jumbo/agent-jumbo/g; s/agent_jumbo/agent_jumbo/g; s/Agent Jumbo/Agent Jumbo/g; s/agent0/agent-jumbo/g; s|/aj/|/aj/|g; s|/a0 |/aj |g' {} +
```

- [ ] **Step 3: Update initialize.py to reference new agent directory**

Check if `initialize.py` or any config references `agents/agent0` as the default agent and update to `agents/agent-jumbo`.

```bash
grep -rn "agent0" initialize.py python/helpers/ --include="*.py" | grep -v __pycache__
```

Update any matches.

- [ ] **Step 4: Run tests**

```bash
python -m pytest tests/ -k "not e2e" -q --tb=short 2>&1 | tail -10
```

- [ ] **Step 5: Commit**

```bash
git add prompts/ agents/ knowledge/ conf/ initialize.py
git commit -m "refactor: rebrand prompts, agents, knowledge to Agent Jumbo"
```

---

### Task 7: Scripts, Docs, and Configs

**Files:**

- `scripts/validate.sh` (3 refs)
- `scripts/health_check.sh` (2 refs)
- `scripts/mcp/setup_claude_desktop.sh` (2 refs + `/aj/` ref)
- `scripts/validate_deployment.sh` (6 `/aj/` refs)
- `init_mcp.sh` (2 `/aj/` refs)
- `docs/installation.md` (9 refs)
- `docs/development.md` (4 refs)
- `docs/README.md` (2 refs)
- `docs/PRODUCTION_DEPLOY.md` (4 refs)
- `docs/SECURITY_UPDATES.md` (1 ref)
- `docs/LEGAL_COMPLIANCE_BRIEF_AGENT_JUMBO.md` (3 refs)
- `docs/COMMUNICATION_PACK_AGENT_JUMBO.md` (3 refs)
- `docs/GO_BLUE_EXECUTION_PLAN_AGENT_JUMBO.md` (2 refs)
- `docs/AGENT_ZERO_PRODUCT_UPDATE_DRAFT.md` (3 refs)
- `docs/superpowers/plans/2026-03-19-post-stabilization-remaining.md` (6 refs)
- `docs/superpowers/plans/2026-03-16-dependency-modernization.md` (10 refs)
- `DEV_CONTAINER_FIX.md` (1 ref)
- `DEV_CONTAINER_READY.md` (2 refs)
- `.github/copilot-instructions.md` (2 refs)
- `.claude/settings.local.json` (11 refs + `/aj/` refs)
- `.env` (check for any agent-jumbo refs)

- [ ] **Step 1: Bulk sed replacement in scripts**

```bash
find scripts/ -name "*.sh" -exec sed -i 's/agent-jumbo/agent-jumbo/g; s/agent_jumbo/agent_jumbo/g; s/Agent Jumbo/Agent Jumbo/g; s|/aj/|/aj/|g; s|/a0"|/aj"|g' {} +
sed -i 's/agent-jumbo/agent-jumbo/g; s/agent_jumbo/agent_jumbo/g; s|/aj/|/aj/|g' init_mcp.sh
```

- [ ] **Step 2: Bulk sed replacement in docs**

```bash
find docs/ -name "*.md" -exec sed -i 's/agent-jumbo/agent-jumbo/g; s/agent_jumbo/agent_jumbo/g; s/Agent Jumbo/Agent Jumbo/g; s|/aj/|/aj/|g' {} +
```

- [ ] **Step 3: Update top-level markdown files**

```bash
for f in DEV_CONTAINER_FIX.md DEV_CONTAINER_READY.md .github/copilot-instructions.md; do
  sed -i 's/agent-jumbo/agent-jumbo/g; s/agent_jumbo/agent_jumbo/g; s/Agent Jumbo/Agent Jumbo/g; s|/aj/|/aj/|g' "$f"
done
```

- [ ] **Step 4: Rename docs/AGENT_ZERO_PRODUCT_UPDATE_DRAFT.md**

```bash
git mv docs/AGENT_ZERO_PRODUCT_UPDATE_DRAFT.md docs/AGENT_JUMBO_PRODUCT_UPDATE_DRAFT.md
```

- [ ] **Step 5: Update .claude/settings.local.json**

```bash
sed -i 's/agent-jumbo/agent-jumbo/g; s/agent_jumbo/agent_jumbo/g; s|/aj/|/aj/|g; s|/a0"|/aj"|g' .claude/settings.local.json
```

- [ ] **Step 6: Commit**

```bash
git add scripts/ docs/ init_mcp.sh *.md .github/ .claude/ .env
git commit -m "refactor: rename agent-jumbo → agent-jumbo in scripts, docs, and configs"
```

---

### Task 8: Directory Renames

**Directories/files to rename:**

- `docs/res/a0-vector-graphics/` → `docs/res/aj-vector-graphics/` (contains `a0LogoVector.ai`)
- `docs/res/setup/6-docker-aj-running.png` — rename to `6-docker-aj-running.png`
- `usr/projects/*/.a0proj` → `usr/projects/*/.ajproj` (7 directories)

- [ ] **Step 1: Rename vector graphics directory**

```bash
git mv docs/res/a0-vector-graphics docs/res/aj-vector-graphics
```

- [ ] **Step 2: Rename setup screenshot**

```bash
git mv "docs/res/setup/6-docker-aj-running.png" "docs/res/setup/6-docker-aj-running.png"
```

Update any references to this filename in docs:

```bash
grep -rl "6-docker-aj-running" docs/ | xargs sed -i 's/6-docker-aj-running/6-docker-aj-running/g'
```

- [ ] **Step 3: Rename .a0proj directories**

```bash
for d in usr/projects/*/.a0proj; do
  parent=$(dirname "$d")
  git mv "$d" "$parent/.ajproj"
done
```

- [ ] **Step 4: Commit**

```bash
git add docs/ usr/
git commit -m "refactor: rename a0 directories and files to aj"
```

---

### Task 9: Instrument Markdown and Template References

**Files:**

- `instruments/custom/business_xray/business_xray.md` (3 refs)
- `instruments/custom/diagram_generator/README.md` (2 refs)
- `instruments/custom/pms_hub/README.md` (1 ref)
- `instruments/custom/knowledge_ingest/knowledge_ingest.md` (1 ref)
- `instruments/custom/_TEMPLATE/template.md` (2 refs)

- [ ] **Step 1: Bulk sed replacement in instrument markdown**

```bash
find instruments/ -name "*.md" -exec sed -i 's/agent-jumbo/agent-jumbo/g; s/agent_jumbo/agent_jumbo/g; s/Agent Jumbo/Agent Jumbo/g; s|/aj/|/aj/|g' {} +
```

- [ ] **Step 2: Commit**

```bash
git add instruments/
git commit -m "refactor: rename agent-jumbo refs in instrument documentation"
```

---

### Task 10: Verification and Smoke Test

- [ ] **Step 1: Verify no remaining agent-jumbo references in project code**

```bash
grep -rl "agent.zero\|agent-jumbo\|agent_jumbo\|Agent Jumbo\|AgentZero" --include="*.py" --include="*.js" --include="*.html" --include="*.json" --include="*.yml" --include="*.yaml" --include="*.md" --include="*.sh" --include="*.cfg" --include="*.conf" --include="*.toml" . | grep -v ".git/" | grep -v "logs/" | grep -v "__pycache__/" | grep -v "node_modules/" | grep -v "vendor/"
```

Expected: Empty output (no remaining references).

- [ ] **Step 2: Verify no remaining /aj/ path references**

```bash
grep -rl "/aj/" --include="*.py" --include="*.js" --include="*.html" --include="*.json" --include="*.sh" . | grep -v ".git/" | grep -v "logs/" | grep -v "__pycache__/"
```

Expected: Empty output.

- [ ] **Step 3: Run full test suite**

```bash
python -m pytest tests/ -k "not e2e" -q --tb=short 2>&1 | tail -10
```

Expected: All tests pass (same count as before rename).

- [ ] **Step 4: Verify git log shows clean commits**

```bash
git log --oneline -10
```

Expected: 8-9 clean rename commits visible.

- [ ] **Step 5: Final commit count check**

Verify we have these commits from the rename:

1. Remove upstream agent-jumbo copy
2. Docker infrastructure rename
3. Python /aj/ path references
4. Python agent-jumbo name references
5. JavaScript/HTML/JSON UI branding
6. Prompts, knowledge, agent configs
7. Scripts, docs, configs
8. Directory renames
9. Instrument documentation

---

## Post-Rename: Docker Rebuild Required

After all commits, rebuild the Docker image to use the new paths:

```bash
cd docker/run
# Create the agent-jumbo directory (replaces old agent-jumbo mount)
# This should be a fresh checkout or copy of the project
cp -r /mnt/wdblack/dev/projects/agent-jumbo docker/run/agent-jumbo

# Rebuild with new image name
docker build --build-arg BRANCH=main -t agent-jumbo:latest .

# Start with new names
docker compose up -d
```

## Notes

- The `agent0ai/agent-jumbo-base:latest` base Docker image reference in `Dockerfile` is kept as-is for now — it's an external dependency. Building our own base image is a separate task.
- Old HTML log files in `logs/` are left as-is — they're historical artifacts.
- The `memory/embeddings/` directories contain hash-based names that happen to include "a0" substrings in SHA hashes — these are NOT agent-jumbo references and should not be touched.
