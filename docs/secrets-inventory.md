<!-- markdownlint-disable MD013 -->

# Secrets Inventory

All secrets are stored in `/mnt/wdblack/dev/secrets/agent-mahoo.env` (outside the project bind mount). This file is loaded via `env_file` in docker-compose.yml.

## Critical Secrets (rotate quarterly)

| Secret | Purpose | Service |
|--------|---------|---------|
| `TELEGRAM_BOT_TOKEN` | Telegram Bot API authentication | Telegram webhook |
| `TELEGRAM_WEBHOOK_SECRET` | Webhook signature verification | Telegram webhook |
| `API_KEY_GOOGLE` / `GOOGLE_API_KEY` | Gemini API access | LLM provider |
| `API_KEY_ANTHROPIC` | Claude API access | LLM provider |
| `API_KEY_OPENAI` | GPT API access | LLM provider |
| `ROOT_PASSWORD` | Agent Mahoo root auth | Web UI auth |
| `AUTH_LOGIN` | Web UI login credentials | Web UI auth |

## Integration Secrets (rotate on compromise)

| Secret | Purpose | Service |
|--------|---------|---------|
| `LINEAR_API_KEY` | Linear issue management | Linear integration |
| `MOTION_API_KEY` | Motion calendar/task sync | Motion integration |
| `NOTION_API_KEY` | Notion page/database access | Notion integration |
| `TWILIO_ACCOUNT_SID` | Twilio voice/SMS | Voice calls |
| `TWILIO_AUTH_TOKEN` | Twilio API auth | Voice calls |
| `HCLOUD_TOKEN` | Hetzner Cloud API | VPS management |
| `BRAVE_API_KEY` | Brave Search API | Web search |
| `CLAUDE_CODE_OAUTH_TOKEN` | Claude Code CLI auth | External agent |

## Observability Secrets

| Secret | Purpose | Service |
|--------|---------|---------|
| `LANGSMITH_API_KEY` | LangSmith tracing | Observability |
| `LANGFUSE_PUBLIC_KEY` | Langfuse tracing | Observability |
| `LANGFUSE_SECRET_KEY` | Langfuse tracing | Observability |

## Other API Keys (rotate as needed)

| Secret | Purpose |
|--------|---------|
| `API_KEY_DEEPSEEK` | DeepSeek LLM |
| `API_KEY_GROQ` | Groq inference |
| `API_KEY_HUGGINGFACE` | HuggingFace models |
| `API_KEY_MISTRAL` | Mistral LLM |
| `API_KEY_OPENROUTER` | OpenRouter proxy |
| `API_KEY_XAI` | xAI/Grok LLM |
| `API_KEY_SAMBANOVA` | SambaNova inference |

## Configuration (not secrets, but in .env)

These are configuration values, not secrets. They do not need rotation:
`OLLAMA_BASE_URL`, `CHAT_MODEL_*`, `UTIL_MODEL_*`, `BROWSER_MODEL_*`, `DEPLOYMENT_MODE`, `TUNNEL_PROVIDER`, `DEFAULT_USER_TIMEZONE`, `MAHOOSUC_*_DIR`, feature flags (`ANTHROPIC_*`, `LLM_*`, `TELEMETRY_*`)

## Rotation Procedure

1. Generate new key/token from the provider's dashboard
2. Update `/mnt/wdblack/dev/secrets/agent-mahoo.env`
3. Restart the container: `docker compose restart agent-mahoo`
4. Verify the service works with the new key
5. Revoke the old key from the provider's dashboard

## Security Notes

- The `.env` file at the project root is a **symlink or copy** for local development only
- The Docker container reads secrets from `/mnt/wdblack/dev/secrets/agent-mahoo.env` which is NOT inside the `/aj` bind mount
- Never commit secrets to git — `.env` is in `.gitignore`
- The `SecurityVaultManager` in `python/helpers/security.py` provides AES-256-GCM encryption for sensitive data stored in SQLite
