"""Progress, placement, and certificate views (master prompt §10, Phase 5)."""
from django.http import HttpResponse
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.content.models import Lesson, Level

from . import placement
from .models import Certificate, PlacementResult, Progress
from .serializers import (
    CertificateSerializer,
    PlacementSubmitSerializer,
    ProgressUpdateSerializer,
)
from .services import generate_certificate_pdf, maybe_issue_certificate, overview


# --- Placement ------------------------------------------------------------- #
class PlacementTestView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({"questions": placement.public_questions()})


class PlacementSubmitView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = PlacementSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        answers = serializer.validated_data["answers"]

        correct = placement.grade(answers)
        code = placement.level_code_for_score(correct)
        level = get_object_or_404(Level, code=code)

        PlacementResult.objects.create(
            user=request.user, assigned_level=level, score=correct
        )
        return Response(
            {
                "score": correct,
                "total": len(placement.QUESTIONS),
                "assigned_level": {
                    "id": str(level.id),
                    "code": level.code,
                    "name": level.name,
                },
            }
        )


# --- Progress -------------------------------------------------------------- #
class ProgressOverviewView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(overview(request.user))


class LessonProgressView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        lesson = get_object_or_404(Lesson, pk=pk)
        serializer = ProgressUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        progress, _ = Progress.objects.get_or_create(
            user=request.user, lesson=lesson
        )
        progress.status = data["status"]
        if "score" in data:
            progress.score = data["score"]
        if "time_spent" in data:
            progress.time_spent = data["time_spent"]
        if data["status"] == Progress.Status.COMPLETED and not progress.completed_at:
            progress.completed_at = timezone.now()
        progress.save()

        # Issue a certificate if this completion finished the whole level.
        certificate = None
        if data["status"] == Progress.Status.COMPLETED:
            certificate = maybe_issue_certificate(
                request.user, lesson.unit.level
            )

        return Response(
            {
                "lesson_id": str(lesson.id),
                "status": progress.status,
                "score": progress.score,
                "time_spent": progress.time_spent,
                "certificate_issued": bool(certificate),
                "certificate_id": str(certificate.id) if certificate else None,
            },
            status=status.HTTP_200_OK,
        )


# --- Certificates ---------------------------------------------------------- #
class CertificateListView(generics.ListAPIView):
    serializer_class = CertificateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Certificate.objects.filter(user=self.request.user)


class CertificatePdfView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        certificate = get_object_or_404(
            Certificate, pk=pk, user=request.user
        )
        pdf_bytes = generate_certificate_pdf(certificate)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = (
            f'inline; filename="{certificate.certificate_number}.pdf"'
        )
        return response


# --- Micro-learning phases ------------------------------------------------- #
class LessonPhaseView(APIView):
    """POST /progress/lesson/{id}/phase — mark a lesson phase completed."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        from .models import LessonPhaseProgress
        from .serializers import PhaseSerializer

        lesson = get_object_or_404(Lesson, pk=pk)
        serializer = PhaseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        row, _ = LessonPhaseProgress.objects.update_or_create(
            user=request.user,
            lesson=lesson,
            phase=data["phase"],
            defaults={"score": data.get("score") or 0},
        )
        # Touching a phase means the lesson is at least in progress.
        Progress.objects.get_or_create(
            user=request.user,
            lesson=lesson,
            defaults={"status": Progress.Status.IN_PROGRESS},
        )
        phases = list(
            LessonPhaseProgress.objects.filter(
                user=request.user, lesson=lesson
            ).values_list("phase", flat=True)
        )
        return Response({"lesson_id": str(lesson.id), "phases": sorted(phases)})


# --- Unit mastery assessment ------------------------------------------------ #
class UnitAssessmentView(APIView):
    """GET: 10 random sanitized questions. POST: grade + store the attempt."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        from apps.content.models import Unit

        from . import assessment

        unit = get_object_or_404(Unit, pk=pk)
        return Response(
            {
                "unit_id": str(unit.id),
                "pass_score": assessment.PASS_RATIO,
                "questions": assessment.build_questions(unit),
            }
        )

    def post(self, request, pk):
        from apps.content.models import Unit

        from . import assessment
        from .serializers import AssessmentSubmitSerializer

        unit = get_object_or_404(Unit, pk=pk)
        serializer = AssessmentSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        result = assessment.grade(
            request.user, unit, serializer.validated_data["answers"]
        )
        return Response(
            {
                "score": result.score,
                "max_score": result.max_score,
                "passed": result.passed,
                "attempt": result.attempt,
            },
            status=status.HTTP_201_CREATED,
        )


class UnitRatingView(APIView):
    """POST /units/{id}/rating {rating: up|down}."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        from apps.content.models import Unit

        from .models import ContentRating
        from .serializers import RatingSerializer

        unit = get_object_or_404(Unit, pk=pk)
        serializer = RatingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ContentRating.objects.update_or_create(
            user=request.user,
            unit=unit,
            defaults={"rating": serializer.validated_data["rating"]},
        )
        return Response({"ok": True})


# --- Vocabulary tracking ----------------------------------------------------- #
class VocabTrackView(APIView):
    """POST /vocab/track {results: [{item_id, correct}]} — batch quiz results."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        from apps.content.models import VocabularyItem

        from .models import VocabularyProgress
        from .serializers import VocabTrackSerializer

        serializer = VocabTrackSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        results = serializer.validated_data["results"]

        items = {
            str(v.id): v
            for v in VocabularyItem.objects.filter(
                id__in=[r["item_id"] for r in results]
            )
        }
        updated = 0
        for r in results:
            item = items.get(str(r["item_id"]))
            if item is None:
                continue
            row, _ = VocabularyProgress.objects.get_or_create(
                user=request.user, vocabulary_item=item
            )
            row.record(r["correct"])
            updated += 1
        return Response({"updated": updated})
