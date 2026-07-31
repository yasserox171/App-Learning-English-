"""Video hosting isolation layer (master prompt §7).

The hosting decision is deferred. Code and DB never reference final URLs —
only an abstract ``storage_key``. A swappable VideoService turns that key
into a playback URL at request time. The MVP ships a trivial implementation
that points at a base URL; later this is replaced by signed HLS (private
server, Bunny, Cloudflare Stream, ...) WITHOUT touching the rest of the code.
"""
from abc import ABC, abstractmethod

from django.conf import settings


class VideoService(ABC):
    """Interface for resolving a stored video into a playable URL."""

    @abstractmethod
    def get_playback_url(self, video) -> str:
        """Return a playback URL for the given Video instance."""
        raise NotImplementedError

    @abstractmethod
    def media_url(self, storage_key: str) -> str:
        """Absolute URL for any storage key (video, image or audio).

        Vocabulary image_url/audio_url are URLFields and reject relative
        paths, so the upload API has to hand back an absolute URL — built
        from the same base as playback so there is only ever one setting.
        """
        raise NotImplementedError


class LocalVideoService(VideoService):
    """Default MVP implementation: build a URL from the storage key.

    Final delivery will be HLS (.m3u8 + .ts) with signed/protected links;
    swapping this class out is all that's required.
    """

    def get_playback_url(self, video) -> str:
        return self.media_url(video.storage_key or "")

    def media_url(self, storage_key: str) -> str:
        key = (storage_key or "").lstrip("/")
        # Absolute URLs (e.g. imported media) are used as-is.
        if key.startswith("http://") or key.startswith("https://"):
            return key
        base = settings.VIDEO_PLAYBACK_BASE_URL.rstrip("/")
        return f"{base}/{key}"


# Single shared instance — import this everywhere video URLs are needed.
video_service: VideoService = LocalVideoService()
