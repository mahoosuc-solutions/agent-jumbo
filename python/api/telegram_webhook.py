import os
import random
import uuid

from agent import UserMessage
from python.helpers import extension
from python.helpers.api import ApiHandler, Request, Response
from python.helpers.print_style import PrintStyle
from python.helpers.telegram_bridge import (
    build_title,
    clear_context_for_chat,
    extract_tags,
    get_context_for_chat,
    get_session_meta,
    set_context_for_chat,
    set_session_meta,
    should_ignore_update,
)
from python.helpers.telegram_client import send_long_message, send_message
from python.helpers.telegram_media import TelegramMedia, cleanup_stale_uploads, extract_media
from python.helpers.telegram_orchestrator import (
    HELP_TEXT,
    build_orchestrator_context,
    format_for_telegram,
    parse_slash_command,
    slash_command_to_prompt,
)


class TelegramWebhook(ApiHandler):
    @classmethod
    def requires_auth(cls) -> bool:
        return False

    @classmethod
    def requires_csrf(cls) -> bool:
        return False

    async def process(self, input: dict, request: Request):
        secret = os.getenv("TELEGRAM_WEBHOOK_SECRET")
        if secret:
            header = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
            if header != secret:
                return Response(response="forbidden", status=403, mimetype="text/plain")

        req_data = request.get_json(silent=True) or {}
        update_id = req_data.get("update_id")
        message = req_data.get("message") or req_data.get("edited_message") or {}
        chat = message.get("chat") or {}
        chat_id = chat.get("id")

        if not chat_id:
            return {"status": "ignored"}

        chat_id_str = str(chat_id)
        if isinstance(update_id, int) and should_ignore_update(chat_id_str, update_id):
            return {"status": "duplicate"}

        # Check for reset commands before media extraction
        raw_text = message.get("text") or ""
        if raw_text.strip().lower() in {"/new", "/reset"}:
            clear_context_for_chat(chat_id_str)
            token = os.getenv("TELEGRAM_BOT_TOKEN")
            if token:
                send_message(token, chat_id_str, "Context reset. Start a new thread.")
            return {"status": "reset"}

        # Handle orchestrator slash commands
        cmd, cmd_args = parse_slash_command(raw_text)
        if cmd == "help":
            token = os.getenv("TELEGRAM_BOT_TOKEN")
            if token:
                send_message(token, chat_id_str, HELP_TEXT)
            return {"status": "ok"}
        if cmd in ("status", "sync"):
            # Auto-sync core projects into portfolio before status/sync commands
            try:
                from python.helpers.portfolio_sync import sync_core_projects_to_portfolio

                sync_core_projects_to_portfolio()
            except Exception as e:
                PrintStyle.error(f"Portfolio sync failed: {e}")
        translated_text = None
        if cmd is not None:
            # Translate slash command to natural language for the agent
            translated_text = slash_command_to_prompt(cmd, cmd_args)

        # Extract media (photos, video, voice, audio, documents)
        token = os.getenv("TELEGRAM_BOT_TOKEN", "")
        if not token:
            PrintStyle.error("[TelegramWebhook] TELEGRAM_BOT_TOKEN not set; media downloads will fail")
        media: TelegramMedia | None = None
        try:
            media = await extract_media(message, token)
        except Exception as e:
            PrintStyle.error(f"Media extraction failed: {e}")
            media = TelegramMedia(text=raw_text)

        # Persist vision context for follow-up messages
        if media and media.attachment_paths:
            vision_summary = {
                "description": f"Image received with message: {(media.text or 'no caption')[:200]}",
                "attachment_count": len(media.attachment_paths),
                "has_image": any(
                    p.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp")) for p in media.attachment_paths
                ),
            }
            set_session_meta(chat_id_str, "vision_context", vision_summary)

        # Use translated slash command prompt if available, otherwise use media text
        text = translated_text or media.text
        attachment_paths = media.attachment_paths

        if not text and not attachment_paths:
            return {"status": "ignored"}

        shared_context = os.getenv("TELEGRAM_AGENT_CONTEXT")
        ctxid = shared_context or get_context_for_chat(chat_id_str)
        if not ctxid:
            ctxid = f"telegram-{uuid.uuid4().hex}"
        if not shared_context:
            set_context_for_chat(chat_id_str, ctxid)

        context = self.use_context(ctxid)

        ext_data = {"message": text, "attachment_paths": attachment_paths}
        await extension.call_extensions("user_message_ui", agent=context.get_agent(), data=ext_data)
        text = ext_data.get("message", "")
        attachment_paths = ext_data.get("attachment_paths", attachment_paths)

        tags = extract_tags(text)
        tags.append(f"chat:{chat_id_str}")
        tags = sorted(set(tags))
        title = build_title(text)

        PrintStyle(font_color="white", padding=True).print(f"[Telegram] {chat_id_str}: {text}")

        await self._store_telegram_message(text, title, tags)

        try:
            # Inject orchestrator context
            orch_context = build_orchestrator_context(
                chat_id=chat_id_str,
                vision_context=get_session_meta(chat_id_str, "vision_context"),
                active_project=get_session_meta(chat_id_str, "active_project"),
                last_tool=get_session_meta(chat_id_str, "last_tool"),
            )
            if orch_context:
                text = f"{orch_context}\n\n{text}"

            task = context.communicate(UserMessage(message=text, attachments=attachment_paths))
            result = await task.result()  # type: ignore

            if token:
                formatted = format_for_telegram(result)
                send_long_message(token, chat_id_str, formatted)
        finally:
            if media:
                media.cleanup()
            if random.random() < 0.05:
                cleanup_stale_uploads()

        return {"status": "ok"}

    async def _store_telegram_message(self, text: str, title: str, tags: list[str]) -> None:
        try:
            from instruments.custom.knowledge_ingest.knowledge_ingest_db import KnowledgeIngestDatabase
            from instruments.custom.knowledge_ingest.knowledge_ingest_manager import KnowledgeIngestManager
            from python.helpers import files

            db_path = files.get_abs_path("./instruments/custom/knowledge_ingest/data/knowledge_ingest.db")
            db = KnowledgeIngestDatabase(db_path)
            source_name = "Telegram Inbox"
            source_uri = "telegram://inbox"
            source_id = db.find_source(source_name, source_uri)
            if not source_id:
                source_id = db.add_source(
                    name=source_name,
                    source_type="telegram",
                    uri=source_uri,
                    tags=["telegram"],
                    cadence="daily",
                    config={},
                )

            source = db.get_source(source_id)
            if not source:
                return

            manager = KnowledgeIngestManager(db_path)
            item = {
                "title": title,
                "url": None,
                "published_at": None,
                "content": text,
                "tags": tags,
                "confidence": 0.8,
            }
            manager.store_external_items(source, [item])
        except Exception as exc:
            PrintStyle.error(f"Telegram ingestion failed: {exc}")
