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
