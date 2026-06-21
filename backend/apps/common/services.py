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


class LocalVideoService(VideoService):
    """Default MVP implementation: build a URL from the storage key.

    Final delivery will be HLS (.m3u8 + .ts) with signed/protected links;
    swapping this class out is all that's required.
    """

    def get_playback_url(self, video) -> str:
        base = settings.VIDEO_PLAYBACK_BASE_URL.rstrip("/")
        return f"{base}/{video.storage_key}"


# Single shared instance — import this everywhere video URLs are needed.
video_service: VideoService = LocalVideoService()
