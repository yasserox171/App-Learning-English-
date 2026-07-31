"""Media upload helpers (content pipeline support).

Pure functions — no HTTP — so the rules are testable on their own.

Design notes:
  * Files stream to disk in chunks; a video may be tens of MB and must never
    be buffered whole in memory.
  * sha256 is computed during that same pass, and the digest names the file.
    Re-uploading identical bytes therefore resolves to the same key and skips
    the write entirely, which makes orchestrator retries free.
  * storage_key is always relative to MEDIA_ROOT ("videos/ab12….mp4"), the
    same relative form Video.storage_key and VideoService expect.
"""
import hashlib
import os
import tempfile
from pathlib import Path

from django.conf import settings
from django.utils.text import get_valid_filename

# kind → (subdirectory, allowed extensions, settings key for the size cap)
KINDS = {
    "video": ("videos", {".mp4", ".m3u8", ".mov", ".webm", ".mkv"},
              "MEDIA_MAX_VIDEO_MB"),
    "image": ("images", {".png", ".jpg", ".jpeg", ".webp", ".gif", ".svg"},
              "MEDIA_MAX_IMAGE_MB"),
    "audio": ("audio", {".mp3", ".m4a", ".wav", ".ogg", ".aac", ".opus"},
              "MEDIA_MAX_AUDIO_MB"),
}


class MediaUploadError(Exception):
    """Rejected upload — the message is safe to return to the caller."""


def max_bytes(kind: str) -> int:
    _, _, setting = KINDS[kind]
    return int(getattr(settings, setting)) * 1024 * 1024


def safe_extension(kind: str, filename: str) -> str:
    """Validated, lowercased extension for `kind`, or raise."""
    _, allowed, _ = KINDS[kind]
    ext = Path(filename).suffix.lower()
    if ext not in allowed:
        raise MediaUploadError(
            f"Extension '{ext or '(none)'}' is not allowed for kind "
            f"'{kind}'. Allowed: {', '.join(sorted(allowed))}"
        )
    return ext


def sanitise_filename(raw: str) -> str:
    """Strip every directory component and reject traversal attempts.

    Only the basename survives, so '../../etc/passwd' and 'C:\\x\\y.mp4'
    can never escape MEDIA_ROOT.
    """
    candidate = str(raw or "").replace("\\", "/").strip()
    candidate = candidate.split("/")[-1]          # drop directories
    candidate = get_valid_filename(candidate)     # drop the rest
    if not candidate or candidate in (".", ".."):
        raise MediaUploadError("Invalid filename.")
    return candidate


def store_upload(uploaded, *, kind: str, filename: str = "") -> dict:
    """Stream `uploaded` to MEDIA_ROOT, deduplicating by content hash.

    Returns {storage_key, size, sha256, deduplicated}.
    """
    if kind not in KINDS:
        raise MediaUploadError(
            f"'kind' must be one of: {', '.join(sorted(KINDS))}"
        )

    subdir, _, _ = KINDS[kind]
    # The client-supplied name only decides the extension; the stored name is
    # the content hash, so hostile names cannot influence the path.
    source_name = sanitise_filename(filename or getattr(uploaded, "name", ""))
    ext = safe_extension(kind, source_name)

    limit = max_bytes(kind)
    # Trust the declared size only as an early reject; the real check happens
    # while streaming, since size can be absent or wrong.
    declared = getattr(uploaded, "size", None)
    if declared is not None and declared > limit:
        raise MediaUploadError(
            f"File exceeds the {limit // (1024 * 1024)} MB limit for "
            f"kind '{kind}'."
        )

    dest_dir = Path(settings.MEDIA_ROOT) / subdir
    dest_dir.mkdir(parents=True, exist_ok=True)

    digest = hashlib.sha256()
    size = 0
    tmp_fd, tmp_path = tempfile.mkstemp(dir=str(dest_dir), suffix=".part")
    try:
        with os.fdopen(tmp_fd, "wb") as out:
            for chunk in uploaded.chunks():
                size += len(chunk)
                if size > limit:
                    raise MediaUploadError(
                        f"File exceeds the {limit // (1024 * 1024)} MB limit "
                        f"for kind '{kind}'."
                    )
                digest.update(chunk)
                out.write(chunk)
        if size == 0:
            raise MediaUploadError("Uploaded file is empty.")

        sha256 = digest.hexdigest()
        final_name = f"{sha256[:32]}{ext}"
        final_path = dest_dir / final_name

        if final_path.exists():
            # Identical bytes already stored — keep the original file.
            os.unlink(tmp_path)
            deduplicated = True
        else:
            os.replace(tmp_path, final_path)   # atomic within the same dir
            os.chmod(final_path, 0o644)
            deduplicated = False
    except Exception:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)
        raise

    return {
        "storage_key": f"{subdir}/{final_name}",
        "size": size,
        "sha256": sha256,
        "deduplicated": deduplicated,
    }
