"""Exercise engine views (master prompt §10, Phase 4)."""
from rest_framework import permissions, status
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from .correctors import get_corrector
from .models import Exercise, ExerciseAttempt


class AttemptView(APIView):
    """POST /api/v1/exercises/{id}/attempt -> {is_correct, score}."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        exercise = get_object_or_404(
            Exercise.objects.select_related("template"), pk=pk
        )
        answer = request.data.get("answer", request.data)

        corrector = get_corrector(exercise.template.code)
        is_correct, fraction = corrector.check(exercise.content, answer)
        score = round(exercise.points * fraction)

        attempt = ExerciseAttempt.objects.create(
            user=request.user,
            exercise=exercise,
            answer=answer,
            is_correct=is_correct,
            score=score,
        )

        return Response(
            {
                "attempt_id": str(attempt.id),
                "is_correct": is_correct,
                "score": score,
                "max_score": exercise.points,
            },
            status=status.HTTP_201_CREATED,
        )
