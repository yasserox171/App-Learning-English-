"""External providers for the AI Tutor pipeline (v2 §3.1/§3.3).

STT: Whisper API (OpenAI) — chosen for accuracy with Arabic-accented English.
LLM: Claude API (Anthropic SDK).
TTS: Google Cloud TTS — natural enough for conversation, generous free tier.

Each provider is a small class so it can be swapped or mocked in tests.
"""
import base64
import json
import urllib.request

from django.conf import settings


class ProviderError(Exception):
    pass


# --------------------------------------------------------------------------- #
# Speech-to-text — Whisper
# --------------------------------------------------------------------------- #
class WhisperSTT:
    URL = "https://api.openai.com/v1/audio/transcriptions"

    @property
    def configured(self):
        return bool(getattr(settings, "OPENAI_API_KEY", ""))

    def transcribe(self, audio_bytes: bytes, filename: str = "audio.m4a") -> str:
        if not self.configured:
            raise ProviderError("OPENAI_API_KEY is not configured (Whisper STT)")

        boundary = "----FocusLanguagesBoundary"
        parts = []
        for name, value in (("model", "whisper-1"), ("language", "en")):
            parts.append(
                f"--{boundary}\r\nContent-Disposition: form-data; "
                f'name="{name}"\r\n\r\n{value}\r\n'.encode()
            )
        parts.append(
            f"--{boundary}\r\nContent-Disposition: form-data; "
            f'name="file"; filename="{filename}"\r\n'
            "Content-Type: application/octet-stream\r\n\r\n".encode()
        )
        body = b"".join(parts) + audio_bytes + f"\r\n--{boundary}--\r\n".encode()

        req = urllib.request.Request(
            self.URL,
            data=body,
            headers={
                "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                "Content-Type": f"multipart/form-data; boundary={boundary}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.load(resp)
        except Exception as exc:
            raise ProviderError(f"Whisper transcription failed: {exc}") from exc
        return (data.get("text") or "").strip()


# --------------------------------------------------------------------------- #
# LLM — Claude
# --------------------------------------------------------------------------- #
class ClaudeTutor:
    @property
    def configured(self):
        return bool(getattr(settings, "ANTHROPIC_API_KEY", ""))

    def _client(self):
        try:
            import anthropic
        except ImportError as exc:
            raise ProviderError("anthropic SDK is not installed") from exc
        if not self.configured:
            raise ProviderError("ANTHROPIC_API_KEY is not configured")
        return anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    def reply(self, system_prompt: str, turns: list) -> str:
        """turns: [{"role": "assistant"|"user", "text": ...}] → next reply.

        Latency-sensitive voice exchange (§3.3 target: <3-4s end to end), so
        effort is kept low and replies are capped short.
        """
        client = self._client()
        messages = [
            {"role": t["role"], "content": t["text"]}
            for t in turns
            if t.get("text")
        ]
        if not messages:
            messages = [{"role": "user", "content": "Please start the conversation."}]
        elif messages[0]["role"] == "assistant":
            messages.insert(
                0, {"role": "user", "content": "Please start the conversation."}
            )

        response = client.messages.create(
            model=getattr(settings, "CLAUDE_MODEL", "claude-opus-5"),
            max_tokens=150,  # 1-2 short sentences, keeps TTS cost/latency down
            output_config={"effort": "low"},
            system=system_prompt,
            messages=messages,
        )
        if response.stop_reason == "refusal":
            return "Let's talk about something else from our lesson. What do you think?"
        return next(
            (b.text for b in response.content if b.type == "text"), ""
        ).strip()


# --------------------------------------------------------------------------- #
# Text-to-speech — Google Cloud TTS
# --------------------------------------------------------------------------- #
class GoogleTTS:
    URL = "https://texttospeech.googleapis.com/v1/text:synthesize"

    @property
    def configured(self):
        return bool(getattr(settings, "GOOGLE_TTS_API_KEY", ""))

    def synthesize(self, text: str) -> bytes:
        """Return MP3 bytes for the reply."""
        if not self.configured:
            raise ProviderError("GOOGLE_TTS_API_KEY is not configured")
        payload = json.dumps({
            "input": {"text": text},
            "voice": {
                "languageCode": "en-US",
                "name": getattr(settings, "GOOGLE_TTS_VOICE", "en-US-Neural2-F"),
            },
            "audioConfig": {"audioEncoding": "MP3", "speakingRate": 0.95},
        }).encode()
        req = urllib.request.Request(
            f"{self.URL}?key={settings.GOOGLE_TTS_API_KEY}",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.load(resp)
        except Exception as exc:
            raise ProviderError(f"Google TTS failed: {exc}") from exc
        return base64.b64decode(data.get("audioContent", ""))


stt = WhisperSTT()
llm = ClaudeTutor()
tts = GoogleTTS()
