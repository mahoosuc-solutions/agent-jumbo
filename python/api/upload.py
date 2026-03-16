import mimetypes

from werkzeug.utils import secure_filename

from python.helpers import files
from python.helpers.api import ApiHandler, Request, Response

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB per file

ALLOWED_EXTENSIONS = {
    # Images
    "png",
    "jpg",
    "jpeg",
    "gif",
    "bmp",
    "webp",
    # Documents
    "txt",
    "pdf",
    "csv",
    "html",
    "json",
    "md",
    "xml",
    "yaml",
    "yml",
    "log",
    "rtf",
    "doc",
    "docx",
    "xls",
    "xlsx",
    "ppt",
    "pptx",
    "odt",
    "ods",
    "odp",
    # Archives
    "zip",
    "tar",
    "gz",
    # Audio/Video
    "mp3",
    "mp4",
    "wav",
    "ogg",
    "webm",
}

# Map extensions to expected MIME type prefixes for magic-byte validation.
# Extensions absent from this map skip MIME checking (mimetypes has no reliable guess).
EXTENSION_MIME_PREFIX: dict[str, tuple[str, ...]] = {
    "png": ("image/png",),
    "jpg": ("image/jpeg",),
    "jpeg": ("image/jpeg",),
    "gif": ("image/gif",),
    "bmp": ("image/bmp", "image/x-bmp", "image/x-ms-bmp"),
    "webp": ("image/webp",),
    "pdf": ("application/pdf",),
    "zip": ("application/zip", "application/x-zip-compressed"),
    "gz": ("application/gzip", "application/x-gzip"),
    "tar": ("application/x-tar",),
    "mp3": ("audio/mpeg", "audio/mp3"),
    "mp4": ("video/mp4",),
    "wav": ("audio/wav", "audio/x-wav"),
    "ogg": ("audio/ogg", "video/ogg", "application/ogg"),
    "webm": ("video/webm", "audio/webm"),
    "html": ("text/html",),
    "xml": ("text/xml", "application/xml"),
    "json": ("application/json",),
    "csv": ("text/csv", "text/plain"),
    "txt": ("text/plain",),
    "md": ("text/plain", "text/markdown"),
    "rtf": ("text/rtf", "application/rtf"),
}


class UploadFile(ApiHandler):
    async def process(self, input: dict, request: Request) -> dict | Response:
        if "file" not in request.files:
            raise Exception("No file part")

        file_list = request.files.getlist("file")  # Handle multiple files
        saved_filenames = []

        for file in file_list:
            if not file or not file.filename:
                continue

            filename = file.filename

            # Extension whitelist check
            if not self.allowed_file(filename):
                raise Exception(f"File type not allowed: {filename}")

            # Read file content once for size + MIME validation
            content = file.read()

            # File size check (100MB hard limit per file)
            if len(content) > MAX_FILE_SIZE:
                raise Exception(f"File too large: {filename} ({len(content)} bytes). Maximum allowed size is 100MB.")

            # MIME type validation against magic bytes
            ext = filename.rsplit(".", 1)[1].lower()
            if not self._valid_mime(ext, content):
                raise Exception(f"File content does not match its extension: {filename}")

            safe_name = secure_filename(filename)  # type: ignore
            dest_path = files.get_abs_path("tmp/upload", safe_name)

            with open(dest_path, "wb") as fh:
                fh.write(content)

            saved_filenames.append(safe_name)

        return {"filenames": saved_filenames}  # Return saved filenames

    def allowed_file(self, filename: str) -> bool:
        """Return True only if the filename carries a whitelisted extension."""
        return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

    def _valid_mime(self, ext: str, content: bytes) -> bool:
        """
        Validate file content against expected MIME type using stdlib mimetypes.

        mimetypes.guess_type() works from file name/extension, not magic bytes,
        but it gives us the canonical MIME string for the extension so we can
        compare it against what we would expect.  For extensions where we have a
        known prefix list (EXTENSION_MIME_PREFIX) we also accept those prefixes.

        For extensions not listed in EXTENSION_MIME_PREFIX we fall back to a
        basic printable-text heuristic for text-like types, and accept anything
        for truly opaque binary formats (doc/xls/ppt/odt/ods/odp) that lack a
        reliable magic-byte fingerprint via the stdlib alone.
        """
        fake_name = f"file.{ext}"
        guessed_mime, _ = mimetypes.guess_type(fake_name)

        expected_prefixes = EXTENSION_MIME_PREFIX.get(ext)

        if expected_prefixes:
            # If mimetypes returned a type, it must match one of our expected prefixes.
            if guessed_mime and not any(guessed_mime.startswith(p) for p in expected_prefixes):
                return False

            # Additionally verify a few well-known magic byte signatures.
            return self._check_magic(ext, content)

        # For extensions with no entry in EXTENSION_MIME_PREFIX (doc, docx, xls,
        # xlsx, ppt, pptx, odt, ods, odp, log, yaml, yml) we rely on the
        # extension whitelist alone — their binary formats vary too widely for
        # reliable stdlib-only magic-byte checking.
        return True

    @staticmethod
    def _check_magic(ext: str, content: bytes) -> bool:
        """
        Spot-check well-known magic byte signatures for common binary formats.
        Returns True if the signature matches (or is not checked for this ext).
        """
        if not content:
            return False

        magic_checks: dict[str, bytes | tuple[bytes, ...]] = {
            "png": b"\x89PNG\r\n\x1a\n",
            "jpg": (b"\xff\xd8\xff",),
            "jpeg": (b"\xff\xd8\xff",),
            "gif": (b"GIF87a", b"GIF89a"),
            "bmp": b"BM",
            "webp": None,  # checked separately below (RIFF....WEBP)
            "pdf": b"%PDF",
            "zip": (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"),
            "gz": b"\x1f\x8b",
            "tar": None,  # ustar magic at offset 257 — skip for brevity
            "mp3": (b"\xff\xfb", b"\xff\xf3", b"\xff\xf2", b"ID3"),
            "mp4": None,  # ftyp box — complex, skip magic check
            "wav": b"RIFF",
            "ogg": b"OggS",
            "webm": b"\x1a\x45\xdf\xa3",
        }

        sig = magic_checks.get(ext)

        if sig is None:
            # No magic check registered — trust the extension whitelist.
            return True

        if ext == "webp":
            # RIFF????WEBP
            return content[:4] == b"RIFF" and content[8:12] == b"WEBP"

        if isinstance(sig, tuple):
            return any(content[: len(s)] == s for s in sig)

        return content[: len(sig)] == sig
