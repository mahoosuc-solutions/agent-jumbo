"""Extract and process media from Telegram messages."""

from __future__ import annotations

import asyncio
import base64
import os
import time
import uuid
from dataclasses import dataclass, field

from python.helpers import files
from python.helpers.print_style import PrintStyle
from python.helpers.telegram_client import download_file

UPLOAD_DIR = "tmp/uploads"
STALE_THRESHOLD_SECONDS = 3600
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "base")


@dataclass
class TelegramMedia:
    text: str
    attachment_paths: list[str] = field(default_factory=list)
    cleanup_paths: list[str] = field(default_factory=list)

    def cleanup(self) -> None:
        for path in self.cleanup_paths:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception:
                pass


def _ext_from_mime(mime_type: str | None, default: str) -> str:
    if not mime_type:
        return default
    mapping = {
        "video/mp4": "mp4",
        "video/quicktime": "mov",
        "video/webm": "webm",
        "audio/ogg": "ogg",
        "audio/mpeg": "mp3",
        "audio/mp4": "m4a",
        "image/jpeg": "jpg",
        "image/png": "png",
    }
    return mapping.get(mime_type, default)


def _ensure_upload_dir() -> str:
    upload_dir = files.get_abs_path(UPLOAD_DIR)
    os.makedirs(upload_dir, exist_ok=True)
    return upload_dir


async def _download_and_save(token: str, file_id: str, suggested_name: str, upload_dir: str) -> tuple[str, str] | None:
    data = await asyncio.to_thread(download_file, token, file_id)
    if not data:
        return None
    safe_name = os.path.basename(suggested_name)
    suffix = uuid.uuid4().hex[:8]
    _, ext = os.path.splitext(safe_name)
    if not ext:
        ext = ".bin"
    filename = f"{os.path.splitext(safe_name)[0]}_{suffix}{ext}"
    abs_path = os.path.join(upload_dir, filename)
    with open(abs_path, "wb") as f:
        f.write(data)
    internal_path = f"/a0/{UPLOAD_DIR}/{filename}"
    return abs_path, internal_path


async def _transcribe_voice_async(token: str, file_id: str) -> str | None:
    try:
        data = await asyncio.to_thread(download_file, token, file_id)
        if not data:
            return None
        audio_b64 = base64.b64encode(data).decode("ascii")
        from python.helpers.whisper import transcribe

        result = await transcribe(WHISPER_MODEL, audio_b64)
        if result and isinstance(result, dict):
            text = result.get("text", "").strip()
            return text if text else None
    except Exception as e:
        PrintStyle.error(f"Voice transcription failed: {e}")
    return None


async def extract_media(message: dict, token: str) -> TelegramMedia:
    text = message.get("text") or message.get("caption") or ""
    attachment_paths: list[str] = []
    cleanup_paths: list[str] = []
    upload_dir = _ensure_upload_dir()

    # Photo: array of sizes, pick the largest (last element)
    if message.get("photo"):
        photo = message["photo"][-1]
        file_id = photo.get("file_id")
        if file_id:
            result = await _download_and_save(token, file_id, "photo.jpg", upload_dir)
            if result:
                cleanup_paths.append(result[0])
                attachment_paths.append(result[1])
            if not text:
                text = "[Photo]"

    # Video
    if message.get("video"):
        video = message["video"]
        file_id = video.get("file_id")
        if file_id:
            ext = _ext_from_mime(video.get("mime_type"), "mp4")
            result = await _download_and_save(token, file_id, f"video.{ext}", upload_dir)
            if result:
                cleanup_paths.append(result[0])
                attachment_paths.append(result[1])
            if not text:
                text = "[Video]"

    # Voice message
    if message.get("voice"):
        voice = message["voice"]
        file_id = voice.get("file_id")
        if file_id:
            transcription = await _transcribe_voice_async(token, file_id)
            if transcription:
                prefix = f"[Voice message transcription]: {transcription}"
                text = f"{prefix}\n{text}" if text and text != "[Voice message]" else prefix
            else:
                result = await _download_and_save(token, file_id, "voice.ogg", upload_dir)
                if result:
                    cleanup_paths.append(result[0])
                    attachment_paths.append(result[1])
            if not text:
                text = "[Voice message]"

    # Audio file
    if message.get("audio"):
        audio = message["audio"]
        file_id = audio.get("file_id")
        if file_id:
            transcription = await _transcribe_voice_async(token, file_id)
            if transcription:
                prefix = f"[Audio transcription]: {transcription}"
                text = f"{prefix}\n{text}" if text and text not in ("[Audio]", "") else prefix
            else:
                ext = _ext_from_mime(audio.get("mime_type"), "ogg")
                name = audio.get("file_name", f"audio.{ext}")
                result = await _download_and_save(token, file_id, name, upload_dir)
                if result:
                    cleanup_paths.append(result[0])
                    attachment_paths.append(result[1])
            if not text:
                text = "[Audio]"

    # Document (generic file)
    if message.get("document"):
        doc = message["document"]
        file_id = doc.get("file_id")
        if file_id:
            name = doc.get("file_name", "document.bin")
            result = await _download_and_save(token, file_id, name, upload_dir)
            if result:
                cleanup_paths.append(result[0])
                attachment_paths.append(result[1])
            if not text:
                text = "[Document]"

    return TelegramMedia(text=text, attachment_paths=attachment_paths, cleanup_paths=cleanup_paths)


def cleanup_stale_uploads() -> None:
    try:
        upload_dir = files.get_abs_path(UPLOAD_DIR)
        if not os.path.isdir(upload_dir):
            return
        now = time.time()
        for filename in os.listdir(upload_dir):
            filepath = os.path.join(upload_dir, filename)
            if os.path.isfile(filepath) and (now - os.path.getmtime(filepath)) > STALE_THRESHOLD_SECONDS:
                try:
                    os.remove(filepath)
                except Exception:
                    pass
    except Exception:
        pass
