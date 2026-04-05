#!/usr/bin/env python3
"""
agent-jumbo init — interactive zero-to-running wizard.

Usage:
    python3 scripts/init.py
    # or via shell wrapper:
    ./init.sh

Detects OS, Docker, Ollama, writes .env, and launches the stack.
Requires only Python 3.9+ stdlib — no pip install needed.
"""

from __future__ import annotations

import platform
import secrets
import shutil
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ── ANSI colours ──────────────────────────────────────────────────────────────
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
RED = "\033[31m"
CYAN = "\033[36m"
DIM = "\033[2m"


def c(colour: str, text: str) -> str:
    if sys.stdout.isatty():
        return f"{colour}{text}{RESET}"
    return text


def ok(msg: str) -> None:
    print(c(GREEN, f"  ✓ {msg}"))


def warn(msg: str) -> None:
    print(c(YELLOW, f"  ! {msg}"))


def err(msg: str) -> None:
    print(c(RED, f"  ✗ {msg}"))


def step(n: int, total: int, msg: str) -> None:
    print(f"\n{c(BOLD, f'[{n}/{total}]')} {c(CYAN, msg)}")


def ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    try:
        val = input(f"  {prompt}{suffix}: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)
    return val or default


def ask_choice(prompt: str, choices: list[str], default: str) -> str:
    opts = "/".join(f"{c(BOLD, ch)}" if ch == default else ch for ch in choices)
    while True:
        val = ask(f"{prompt} ({opts})", default).lower()
        if val in choices:
            return val
        err(f"Please enter one of: {', '.join(choices)}")


def run(cmd: list[str], capture: bool = True, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=capture, text=True, check=check)


# ── Detection helpers ─────────────────────────────────────────────────────────


def detect_os() -> str:
    s = platform.system()
    if s == "Darwin":
        return "macos"
    if s == "Windows":
        return "windows"
    return "linux"


def has_docker() -> bool:
    return shutil.which("docker") is not None


def docker_running() -> bool:
    try:
        run(["docker", "info"])
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def has_ollama() -> bool:
    return shutil.which("ollama") is not None


def ollama_running() -> bool:
    try:
        urllib.request.urlopen("http://localhost:11434/api/tags", timeout=2)
        return True
    except Exception:
        return False


def ollama_has_model(model: str) -> bool:
    try:
        result = run(["ollama", "list"])
        return model.split(":")[0] in result.stdout
    except Exception:
        return False


def check_port_free(port: int) -> bool:
    import socket

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) != 0


# ── .env writing ──────────────────────────────────────────────────────────────


def read_existing_env() -> dict[str, str]:
    env_path = ROOT / ".env"
    if not env_path.exists():
        return {}
    values: dict[str, str] = {}
    for line in env_path.read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, _, v = line.partition("=")
            values[k.strip()] = v.strip().strip('"').strip("'")
    return values


def write_env(values: dict[str, str]) -> None:
    env_path = ROOT / ".env"
    example_path = ROOT / ".env.example"

    # Start from example to preserve all documented keys and comments
    if example_path.exists():
        template = example_path.read_text()
    else:
        template = ""

    # Apply our values by replacing bare KEY=... lines
    lines = template.splitlines()
    applied: set[str] = set()
    out: list[str] = []
    for line in lines:
        if "=" in line and not line.startswith("#"):
            key = line.split("=", 1)[0].strip()
            if key in values:
                out.append(f"{key}={values[key]}")
                applied.add(key)
                continue
        out.append(line)

    # Append any keys not present in the template
    for key, val in values.items():
        if key not in applied:
            out.append(f"{key}={val}")

    env_path.write_text("\n".join(out) + "\n")


# ── Provider selection ────────────────────────────────────────────────────────

PROVIDER_MODELS: dict[str, list[str]] = {
    "ollama": ["qwen2.5:3b", "llama3.2:3b", "deepseek-r1:8b"],
    "anthropic": ["claude-haiku-4-5-20251001", "claude-sonnet-4-6", "claude-opus-4-6"],
    "openai": ["gpt-4o-mini", "gpt-4o", "o3-mini"],
    "google": ["gemini/gemini-2.0-flash", "gemini/gemini-2.0-pro"],
    "groq": ["groq/llama-3.1-8b-instant", "groq/llama-3.3-70b-versatile"],
}

PROVIDER_KEY_VARS: dict[str, str] = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "google": "GOOGLE_API_KEY",
    "groq": "GROQ_API_KEY",
}

PROVIDER_KEY_URLS: dict[str, str] = {
    "anthropic": "https://console.anthropic.com/keys",
    "openai": "https://platform.openai.com/api-keys",
    "google": "https://aistudio.google.com/app/apikey",
    "groq": "https://console.groq.com/keys",
}


def select_provider(existing: dict[str, str]) -> tuple[str, str, str | None]:
    """Returns (provider, model, api_key_or_none)."""
    providers = list(PROVIDER_MODELS.keys())
    default = existing.get("CHAT_MODEL_PROVIDER", "ollama")
    if default not in providers:
        default = "ollama"

    print(f"\n  Available providers: {', '.join(providers)}")
    provider = ask("LLM provider", default)
    if provider not in providers:
        provider = "ollama"

    models = PROVIDER_MODELS[provider]
    default_model = existing.get("CHAT_MODEL_NAME", models[0])
    if default_model not in models:
        default_model = models[0]

    print(f"  Models: {', '.join(models)}")
    model = ask("Model", default_model)

    api_key: str | None = None
    if provider != "ollama":
        key_var = PROVIDER_KEY_VARS[provider]
        existing_key = existing.get(key_var, "")
        key_url = PROVIDER_KEY_URLS[provider]
        if not existing_key:
            print(f"\n  {c(DIM, f'Get your key at: {key_url}')}")
        raw = ask(f"{key_var}", existing_key or "sk-...")
        api_key = raw if raw != "sk-..." else None

    return provider, model, api_key


# ── Main wizard ───────────────────────────────────────────────────────────────

TOTAL_STEPS = 6


def main() -> None:
    print()
    print(c(BOLD, "  ╔══════════════════════════════════════╗"))
    print(c(BOLD, "  ║   Agent Jumbo — Quick Setup Wizard   ║"))
    print(c(BOLD, "  ╚══════════════════════════════════════╝"))
    print(f"  {c(DIM, 'Zero-to-running in under 5 minutes.')}")
    print()

    os_name = detect_os()
    ok(f"OS detected: {platform.system()} {platform.machine()}")

    existing = read_existing_env()
    env_values: dict[str, str] = {}

    # ── Step 1: Docker ────────────────────────────────────────────────────────
    step(1, TOTAL_STEPS, "Docker")
    if not has_docker():
        err("Docker not found.")
        install_urls = {
            "macos": "https://docs.docker.com/desktop/install/mac-install/",
            "windows": "https://docs.docker.com/desktop/install/windows-install/",
            "linux": "https://docs.docker.com/engine/install/",
        }
        warn(f"Install Docker first: {install_urls[os_name]}")
        warn("Re-run this wizard after Docker is installed.")
        sys.exit(1)
    ok("Docker found")

    if not docker_running():
        err("Docker daemon is not running.")
        if os_name == "macos":
            warn("Open Docker Desktop and wait for the whale icon.")
        elif os_name == "windows":
            warn("Start Docker Desktop from the Start Menu.")
        else:
            warn("Run: sudo systemctl start docker")
        sys.exit(1)
    ok("Docker daemon is running")

    # ── Step 2: Port check ────────────────────────────────────────────────────
    step(2, TOTAL_STEPS, "Port availability")
    port = int(existing.get("HOST_PORT", "6274"))
    if not check_port_free(port):
        alt = ask(f"Port {port} is in use. Use a different port", "6275")
        port = int(alt)
    env_values["HOST_PORT"] = str(port)
    ok(f"Using port {port}")

    # ── Step 3: LLM provider ──────────────────────────────────────────────────
    step(3, TOTAL_STEPS, "LLM provider")
    provider, model, api_key = select_provider(existing)
    env_values["CHAT_MODEL_PROVIDER"] = provider
    env_values["CHAT_MODEL_NAME"] = model
    env_values["UTIL_MODEL_PROVIDER"] = provider
    env_values["UTIL_MODEL_NAME"] = model
    if api_key:
        key_var = PROVIDER_KEY_VARS[provider]
        env_values[key_var] = api_key
        ok(f"API key set ({key_var})")
    ok(f"Provider: {provider} / {model}")

    # ── Step 4: Ollama (if local) ─────────────────────────────────────────────
    step(4, TOTAL_STEPS, "Local model setup (Ollama)")
    if provider == "ollama":
        if not has_ollama():
            warn("Ollama not found. Installing via Docker Compose (bundled).")
            env_values["OLLAMA_ENABLED"] = "true"
        else:
            ok("Ollama found")
            if not ollama_running():
                warn("Ollama not running — it will start with the stack.")
            else:
                ok("Ollama is running")
                if not ollama_has_model(model):
                    pull = ask_choice(f"Pull model {model} now? (~2-5 GB)", ["yes", "no"], "yes")
                    if pull == "yes":
                        print(f"  {c(DIM, f'Pulling {model}...')}", flush=True)
                        subprocess.run(["ollama", "pull", model], check=False)
                        ok(f"Model {model} ready")
                else:
                    ok(f"Model {model} already available")
    else:
        ok("Skipped (cloud provider selected)")

    # ── Step 5: Credentials ───────────────────────────────────────────────────
    step(5, TOTAL_STEPS, "Admin credentials")

    default_login = existing.get("AUTH_LOGIN", "admin")
    login = ask("Admin username", default_login)
    env_values["AUTH_LOGIN"] = login

    if existing.get("AUTH_PASSWORD"):
        change = ask_choice("Admin password already set. Change it?", ["yes", "no"], "no")
        if change == "yes":
            pw = ask("New admin password")
            if pw:
                env_values["AUTH_PASSWORD"] = pw
    else:
        pw = ask("Admin password (leave blank to generate)")
        env_values["AUTH_PASSWORD"] = pw if pw else secrets.token_urlsafe(16)
        if not pw:
            ok(f"Generated password: {c(BOLD, env_values['AUTH_PASSWORD'])}")
            warn("Save this — it won't be shown again.")

    if not existing.get("FLASK_SECRET_KEY"):
        env_values["FLASK_SECRET_KEY"] = secrets.token_hex(32)
        ok("Flask secret key generated")

    # ── Step 6: Write .env and launch ─────────────────────────────────────────
    step(6, TOTAL_STEPS, "Write config and launch")
    write_env(env_values)
    ok(".env written")

    launch = ask_choice("Launch Agent Jumbo now?", ["yes", "no"], "yes")
    if launch == "no":
        print()
        print(c(GREEN, "  Setup complete. To start later:"))
        print(f"    {c(BOLD, './scripts/docker-deploy.sh deploy')}")
        print()
        return

    print(f"  {c(DIM, 'Starting stack (this may take a minute on first run)...')}")
    deploy_script = ROOT / "scripts" / "docker-deploy.sh"
    if deploy_script.exists():
        result = subprocess.run(
            ["bash", str(deploy_script), "deploy"],
            cwd=ROOT,
            check=False,
        )
        if result.returncode != 0:
            err("Stack failed to start. Check output above for errors.")
            sys.exit(1)
    else:
        # Fallback: docker compose directly
        result = subprocess.run(
            ["docker", "compose", "up", "-d", "--build"],
            cwd=ROOT,
            check=False,
        )
        if result.returncode != 0:
            err("docker compose failed. Check output above.")
            sys.exit(1)

    print()
    print(c(GREEN, c(BOLD, "  ✓ Agent Jumbo is running!")))
    print()
    print(f"  Open: {c(BOLD, c(CYAN, f'http://localhost:{port}'))}")
    print(f"  Login: {c(BOLD, login)}")
    print(f"  Health: curl http://localhost:{port}/health")
    print()
    print(f"  {c(DIM, 'Tip: run ./scripts/docker-deploy.sh logs to tail the logs.')}")
    print()


if __name__ == "__main__":
    main()
