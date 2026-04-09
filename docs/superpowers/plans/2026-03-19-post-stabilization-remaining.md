# Post-Stabilization Remaining Work — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the post-stabilization sprint by integrating Docker deployment config from worktrees into main, cleaning up stale worktree directories, and running a full verification pass to confirm all prior work (P1-P4) is solid.

**Architecture:** Copy the Docker runtime config (`Dockerfile`, `docker-compose.yml`, `fs/` tree) from `.worktrees/ai-ops/docker/run/` into `docker/run/` (which currently has a `.gitkeep` and an empty `agent-mahoo/` subdirectory). Delete all 3 remaining worktree directories plus 10 previously-deleted worktree stubs. Verify E2E tests pass end-to-end.

**Tech Stack:** Docker, docker-compose, bash, pytest, Playwright

---

## Status of Original 5 Priorities

| Priority | Status | Evidence |
|----------|--------|----------|
| P1: Work Queue Alpine.js UI | **DONE** | `webui/dashboards/work-queue/` (store + HTML + router + sidebar nav all exist) |
| P2: Expand API Test Coverage | **DONE** | `tests/e2e/helpers.py` + `test_settings_api.py` (5 tests) + `test_skills_api.py` (7 tests) + `test_gateway_api.py` (5 tests) all exist |
| P3: Scheduler Precision Bug | **DONE** | Commit `64b0af69` — minute-level de-duplication in `check_schedule()` |
| P4: Settings Persistence Refactor | **DONE** | Commit `70ac9fd2` — replaced `DeferredTask` with direct `EventLoopThread` calls |
| P5: Docker Integration + Worktree Cleanup | **TODO** | `docker/run/` has only `.gitkeep`; `.worktrees/` still has 3 directories |

---

## File Structure

| Action | Path | Responsibility |
|--------|------|---------------|
| Create | `docker/run/Dockerfile` | Runtime container build (from `agent0ai/agent-mahoo-base`) |
| Create | `docker/run/docker-compose.yml` | Ollama + Agent-Zero service definitions |
| Create | `docker/run/build.txt` | Build command reference |
| Create | `docker/run/fs/ins/pre_install.sh` | Pre-installation setup |
| Create | `docker/run/fs/ins/install_A0.sh` | Agent-Zero installation |
| Create | `docker/run/fs/ins/install_A02.sh` | Agent-Zero install (cache-busted layer) |
| Create | `docker/run/fs/ins/install_additional.sh` | Additional software installation |
| Create | `docker/run/fs/ins/install_playwright.sh` | Playwright browser install |
| Create | `docker/run/fs/ins/post_install.sh` | Post-installation cleanup |
| Create | `docker/run/fs/ins/copy_A0.sh` | Copy Agent-Zero files |
| Create | `docker/run/fs/ins/setup_ssh.sh` | SSH server setup |
| Create | `docker/run/fs/ins/setup_venv.sh` | Python venv setup |
| Create | `docker/run/fs/exe/initialize.sh` | Container entrypoint (supervisord) |
| Create | `docker/run/fs/exe/run_A0.sh` | Agent-Zero run script |
| Create | `docker/run/fs/exe/run_searxng.sh` | SearXNG run script |
| Create | `docker/run/fs/exe/run_tunnel_api.sh` | Tunnel API run script |
| Create | `docker/run/fs/exe/node_eval.js` | Node.js eval helper |
| Create | `docker/run/fs/exe/supervisor_event_listener.py` | Supervisor event listener |
| Create | `docker/run/fs/etc/nginx/nginx.conf` | Nginx reverse proxy config |
| Create | `docker/run/fs/etc/searxng/settings.yml` | SearXNG search engine config |
| Create | `docker/run/fs/etc/searxng/limiter.toml` | SearXNG rate limiter config |
| Create | `docker/run/fs/etc/supervisor/conf.d/supervisord.conf` | Supervisor process manager config |
| Create | `docker/run/fs/per/root/.bashrc` | Container root bashrc |
| Create | `docker/run/fs/per/root/.profile` | Container root profile |
| Delete | `docker/run/.gitkeep` | No longer needed with real files |
| Delete | `.worktrees/ai-ops/` | Stale worktree (content integrated) |
| Delete | `.worktrees/ai-research/` | Stale worktree (code-identical to ai-ops) |
| Delete | `.worktrees/ai-writer/` | Stale worktree (subset of ai-ops) |

---

### Task 1: Copy Docker Runtime Config from Worktree to Main

**Files:**

- Source: `.worktrees/ai-ops/docker/run/` (24 files)
- Target: `docker/run/` (currently has `.gitkeep` + empty `agent-mahoo/` subdir)

- [ ] **Step 1: Copy all files from ai-ops docker/run/ to main docker/run/**

```bash
cd /mnt/wdblack/dev/projects/agent-mahoo
# Copy Dockerfile, docker-compose.yml, build.txt
cp .worktrees/ai-ops/docker/run/Dockerfile docker/run/Dockerfile
cp .worktrees/ai-ops/docker/run/docker-compose.yml docker/run/docker-compose.yml
cp .worktrees/ai-ops/docker/run/build.txt docker/run/build.txt

# Copy the entire fs/ tree (install scripts, exec scripts, configs, user files)
cp -r .worktrees/ai-ops/docker/run/fs docker/run/fs
```

- [ ] **Step 2: Remove the .gitkeep (no longer needed)**

```bash
rm docker/run/.gitkeep
```

- [ ] **Step 3: Verify the copy is complete**

```bash
# Should show 24 files (matching ai-ops source, minus .gitkeep)
find docker/run/ -type f | wc -l
# Compare file lists (ignore agent-mahoo subdir which pre-existed)
diff <(cd .worktrees/ai-ops/docker/run && find . -type f | sort) <(cd docker/run && find . -type f -not -path './agent-mahoo/*' | sort)
```

Expected: 24 files, no diff.

- [ ] **Step 4: Make shell scripts executable**

```bash
chmod +x docker/run/fs/exe/*.sh docker/run/fs/exe/*.py
chmod +x docker/run/fs/ins/*.sh
```

- [ ] **Step 5: Commit**

```bash
git add docker/run/
git rm docker/run/.gitkeep 2>/dev/null || true
git commit -m "$(cat <<'EOF'
feat(docker): integrate Docker deployment config from worktree archive

Copy the complete runtime container config (Dockerfile, docker-compose.yml,
nginx, supervisor, install/run scripts) from .worktrees/ai-ops/docker/run/
into the main tree. This was the only unique content across all 3 remaining
worktree directories.

Note: The Dockerfile references the upstream agent0ai/agent-mahoo-base image
and uses a BRANCH build arg. Path updates may be needed for the current
project structure — tracked as future work.

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Delete Stale Worktree Directories

**Files:**

- Delete: `.worktrees/ai-ops/`, `.worktrees/ai-research/`, `.worktrees/ai-writer/`

**Context:** Deep comparison confirmed:

- `ai-ops` and `ai-research` are code-identical (differ only in agent test specs)
- `ai-writer` is a leaner subset
- Zero unique Python application code vs main
- The only unique content (docker/run/) was integrated in Task 1

- [ ] **Step 1: Verify git worktree list doesn't reference these as active worktrees**

```bash
git worktree list
```

Expected: Only the main working tree listed. If any are listed as worktrees, prune them first with `git worktree remove`.

- [ ] **Step 2: Delete the 3 worktree directories**

```bash
rm -rf .worktrees/ai-ops/
rm -rf .worktrees/ai-research/
rm -rf .worktrees/ai-writer/
```

- [ ] **Step 3: Remove any remaining files/dirs in .worktrees/ and the directory itself**

Note: Git status also shows 10 previously-deleted worktree stubs (explainability-framework,
learning-improvement-system, life-calendar, etc.) as staged deletions. We'll clean up everything.

```bash
# Remove any remaining files in .worktrees/
rm -rf .worktrees/
```

- [ ] **Step 4: Prune any orphaned git worktree refs**

```bash
git worktree prune
```

- [ ] **Step 5: Verify cleanup**

```bash
# Should fail (directory gone)
ls .worktrees/ 2>/dev/null && echo "FAIL: .worktrees/ still exists" || echo "OK: .worktrees/ removed"
# Should show only main
git worktree list
```

- [ ] **Step 6: Stage and commit the deletion of ALL tracked worktree files**

```bash
# Stage all .worktrees/ deletions (3 directories + 10 previously-deleted stubs)
git add -u .worktrees/
git commit -m "$(cat <<'EOF'
chore: remove all stale worktree directories and stubs

Delete .worktrees/ entirely:
- ai-ops/, ai-research/, ai-writer/: unique content (docker/run/) integrated
  into main in the previous commit; all Python app code already in main
- 10 previously-deleted stubs (explainability-framework, life-calendar,
  life-finance, life-os, oversight-security-framework, etc.): empty
  placeholders that were never populated

Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Verification Pass — Confirm P1-P4 Are Solid

**Files:**

- Read-only verification of existing test infrastructure

- [ ] **Step 1: Run unit tests**

```bash
cd /mnt/wdblack/dev/projects/agent-mahoo
python -m pytest tests/ -v --timeout=60 -k "not e2e" 2>&1 | tail -20
```

Expected: 59 pass (matching stabilization baseline).

- [ ] **Step 2: Run E2E API tests only (fast, no browser)**

```bash
python -m pytest tests/e2e/test_work_queue_e2e.py tests/e2e/test_settings_api.py tests/e2e/test_skills_api.py tests/e2e/test_gateway_api.py -v --timeout=120 -k "not (page_loads or stats_cards or filter_dropdown)" 2>&1 | tail -30
```

Expected: All API-level E2E tests pass.

- [ ] **Step 3: Run E2E browser tests for work queue**

```bash
python -m pytest tests/e2e/test_work_queue_e2e.py -v --timeout=120 -k "page_loads or stats_cards or filter_dropdown" 2>&1 | tail -20
```

Expected: 3 browser tests pass (previously skipped, now active with Alpine.js UI).

- [ ] **Step 4: Run full E2E suite**

```bash
python -m pytest tests/e2e/ -v --timeout=180 2>&1 | tail -40
```

Expected: 49/52 pass (3 env-limited skips remain).

- [ ] **Step 5: TypeScript check**

```bash
cd web && npx tsc --noEmit 2>&1 | tail -5
```

Expected: Clean (no errors).

- [ ] **Step 6: Verify Docker files are present and syntactically valid**

```bash
# Dockerfile exists and has FROM directive
head -3 docker/run/Dockerfile
# docker-compose.yml is valid YAML
python3 -c "import yaml; yaml.safe_load(open('docker/run/docker-compose.yml'))" && echo "YAML valid"
# All shell scripts are executable
find docker/run/fs -name "*.sh" ! -executable -print | head -5
```

Expected: FROM line visible, YAML valid, no non-executable .sh files.

- [ ] **Step 7: Document results**

If all pass: Sprint complete. No additional commits needed.
If failures: Debug, fix, commit with descriptive message.

---

## Summary

| Task | Estimated Steps | Dependencies |
|------|----------------|--------------|
| Task 1: Docker config integration | 5 steps | None |
| Task 2: Worktree cleanup | 6 steps | Task 1 (content must be copied first) |
| Task 3: Verification pass | 7 steps | Tasks 1-2 (verify final state) |

**Total: 18 steps across 3 tasks.**

After completion:

- `docker/run/` contains full deployment config (Dockerfile, docker-compose, nginx, supervisor, scripts)
- `.worktrees/` directory no longer exists
- All E2E tests confirmed passing (49/52, 3 env-limited skips)
- Unit tests confirmed passing (59)
- TypeScript clean
