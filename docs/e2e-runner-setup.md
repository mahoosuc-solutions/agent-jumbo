# E2E Self-Hosted Runner Setup

Prerequisites and provisioning steps for the GitHub Actions self-hosted runner
used by the `e2e-tests` CI job.

## System Requirements

- Ubuntu 22.04+ (or Debian 12+)
- 4 GB RAM minimum (Chromium + app server run concurrently)
- `sudo` access for initial setup (Playwright system deps)
- Network access to PyPI, GitHub, and Playwright CDN

## 1. Install Python 3.12

The CI uses `actions/setup-python@v5`, which downloads Python from the GitHub
tool cache. On a self-hosted runner this works automatically **if** the runner
has write access to `$RUNNER_TOOL_CACHE` (defaults to `_work/_tool`). If the
action fails, install Python manually:

```bash
sudo add-apt-repository ppa:deadsnakes/deadsnakes -y
sudo apt-get update
sudo apt-get install -y python3.12 python3.12-venv python3.12-dev
```

## 2. Install uv

The CI uses `astral-sh/setup-uv@v4`, which installs uv per-job. No
pre-installation needed, but ensure `curl` is available:

```bash
sudo apt-get install -y curl
```

## 3. Playwright System Dependencies

The CI step `playwright install --with-deps chromium` handles both the browser
binary and OS-level libraries. For this to work the runner user must have
passwordless `sudo` for `apt-get`, or the deps must be pre-installed:

```bash
# Pre-install all Playwright deps (avoids needing sudo in CI):
npx playwright install-deps chromium
# Or equivalently:
sudo apt-get install -y \
  libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 libcups2 \
  libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 libxrandr2 \
  libgbm1 libpango-1.0-0 libcairo2 libasound2 libxshmfence1
```

## 4. GitHub Actions Runner

```bash
# Create runner user
sudo useradd -m -s /bin/bash runner
sudo usermod -aG sudo runner

# Download and configure (replace URL/token with your values)
cd /home/runner
curl -o actions-runner.tar.gz -L \
  https://github.com/actions/runner/releases/download/v2.321.0/actions-runner-linux-x64-2.321.0.tar.gz
tar xzf actions-runner.tar.gz
./config.sh --url https://github.com/YOUR_ORG/YOUR_REPO --token YOUR_TOKEN
sudo ./svc.sh install runner
sudo ./svc.sh start
```

## 5. Verify

After the runner is online, trigger a workflow_dispatch run and confirm:

1. `actions/setup-python` resolves Python 3.12
2. `uv sync --extra dev` installs all dev dependencies (including `pytest-json-report`)
3. `playwright install --with-deps chromium` succeeds without errors
4. E2E tests execute and produce `e2e-results.json`

## Dependency Notes

The `[dev]` optional-dependencies group in `pyproject.toml` includes everything
the E2E job needs at the Python level:

- `pytest`, `pytest-asyncio`, `pytest-json-report` -- test runner and reporting
- `playwright` -- browser automation (listed in main dependencies)

System-level dependencies (Chromium shared libraries) are handled by the
`playwright install --with-deps` flag or by pre-installing them as shown above.
