"""AI Tutor endpoints (v2 §3.1 pipeline).

POST /tutor/sessions                {"lesson_id": ...}  → opening line + audio
POST /tutor/sessions/<id>/turn      multipart {audio} OR {"text": ...}
POST /tutor/sessions/<id>/end       → vocab-usage result
GET  /tutor/usage                   → today's count / cap
"""
import base64

from rest_framework import permissions, status
from rest_framework.generics import get_object_or_404
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.content.models import Lesson

from . import providers, services
from .models import AITutorSession


def _tts_or_none(text: str):
    """Synthesize the reply; audio is best-effort (text always returned)."""
    try:
        return base64.b64encode(providers.tts.synthesize(text)).decode()
    except providers.ProviderError:
        return None


class UsageView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(
            {
                "sessions_today": services.sessions_today(request.user),
                "daily_cap": services.daily_cap(request.user),
                "max_exchanges": services.MAX_TURNS,
            }
        )


class SessionStartView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        lesson = get_object_or_404(Lesson, pk=request.data.get("lesson_id"))
        try:
            session = services.start_session(request.user, lesson)
        except services.DailyCapReached as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_429_TOO_MANY_REQUESTS
            )

        # Claude opens with a natural topic-relevant line (§3.1 step 3).
        try:
            opening = providers.llm.reply(session.system_prompt, [])
        except providers.ProviderError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        session.turns.append({"role": "assistant", "text": opening})
        session.save(update_fields=["turns", "updated_at"])

        return Response(
            {
                "session_id": str(session.id),
                "opening_text": opening,
                "opening_audio_b64": _tts_or_none(opening),
                "target_vocabulary": session.target_vocabulary,
                "max_exchanges": services.MAX_TURNS,
            },
            status=status.HTTP_201_CREATED,
        )


class SessionTurnView(APIView):
    """One exchange: audio → Whisper → Claude → Google TTS → audio (§3.1)."""

    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request, pk):
        session = get_object_or_404(
            AITutorSession,
            pk=pk,
            user=request.user,
            status=AITutorSession.Status.ACTIVE,
        )

        if services.exchanges_done(session) >= services.MAX_TURNS:
            services.end_session(session)
            return Response(
                {"detail": "Session exchange limit reached.", "ended": True},
                status=status.HTTP_409_CONFLICT,
            )

        # Learner input: uploaded audio (normal path) or plain text fallback.
        audio_file = request.FILES.get("audio")
        if audio_file is not None:
            try:
                transcript = providers.stt.transcribe(
                    audio_file.read(), filename=audio_file.name or "audio.m4a"
                )
            except providers.ProviderError as exc:
                return Response(
                    {"detail": str(exc)},
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
        else:
            transcript = str(request.data.get("text", "")).strip()
        if not transcript:
            return Response(
                {"detail": "No speech detected. Please try again."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        session.turns.append({"role": "user", "text": transcript})

        try:
            reply = providers.llm.reply(session.system_prompt, session.turns)
        except providers.ProviderError as exc:
            return Response(
                {"detail": str(exc)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        session.turns.append({"role": "assistant", "text": reply})
        session.save(update_fields=["turns", "updated_at"])

        exchanges = services.exchanges_done(session)
        ended = exchanges >= services.MAX_TURNS
        if ended:
            services.end_session(session)

        return Response(
            {
                "transcript": transcript,
                "reply_text": reply,
                "reply_audio_b64": _tts_or_none(reply),
                "exchange": exchanges,
                "max_exchanges": services.MAX_TURNS,
                "ended": ended,
            }
        )


class SessionEndView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        session = get_object_or_404(AITutorSession, pk=pk, user=request.user)
        if session.status == AITutorSession.Status.ACTIVE:
            services.end_session(session)
        return Response(
            {
                "terms_used": session.terms_used,
                "terms_total": session.terms_total,
                "target_vocabulary": session.target_vocabulary,
                "exchanges": services.exchanges_done(session),
            }
        )
