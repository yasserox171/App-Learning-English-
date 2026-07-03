"""Exercise engine views (master prompt §10, Phase 4)."""
import random

from rest_framework import permissions, status
from rest_framework.generics import get_object_or_404
from rest_framework.response import Response
from rest_framework.views import APIView

from .correctors import answer_text, get_corrector
from .models import Exercise, ExerciseAttempt


class AttemptView(APIView):
    """POST /api/v1/exercises/{id}/attempt -> {is_correct, score, ...}.

    Extras: `used_hint: true` halves the awarded points; a wrong answer
    additionally returns `correct_answer` so the app can show the fix."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        exercise = get_object_or_404(
            Exercise.objects.select_related("template"), pk=pk
        )
        answer = request.data.get("answer", request.data)
        used_hint = bool(request.data.get("used_hint"))

        corrector = get_corrector(exercise.template.code)
        is_correct, fraction = corrector.check(exercise.content, answer)
        if used_hint:
            fraction *= 0.5
        score = round(exercise.points * fraction)

        attempt = ExerciseAttempt.objects.create(
            user=request.user,
            exercise=exercise,
            answer=answer,
            is_correct=is_correct,
            score=score,
        )

        # Keep a pronunciation log for later error analysis (feature 11).
        if exercise.template.code == "pronunciation" and isinstance(answer, dict):
            spoken = answer.get("spoken_text", answer.get("transcript"))
            if spoken is not None:
                from .models import PronunciationAttempt

                PronunciationAttempt.objects.create(
                    user=request.user,
                    exercise=exercise,
                    spoken_text=str(spoken),
                    target_text=exercise.content.get("target_text", ""),
                    score=fraction,
                    passed=is_correct,
                    attempt_number=PronunciationAttempt.objects.filter(
                        user=request.user, exercise=exercise
                    ).count()
                    + 1,
                )

        payload = {
            "attempt_id": str(attempt.id),
            "is_correct": is_correct,
            "score": score,
            "max_score": exercise.points,
        }
        if not is_correct:
            payload["correct_answer"] = answer_text(
                exercise.template.code, exercise.content
            )
        return Response(payload, status=status.HTTP_201_CREATED)


class HintView(APIView):
    """POST /api/v1/exercises/{id}/hint {level: 1|2}.

    Level 1: first letter of the answer, or two wrong options to eliminate.
    Level 2: the full answer. Using a hint halves the attempt's points
    (client sends `used_hint` with the attempt)."""

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        exercise = get_object_or_404(
            Exercise.objects.select_related("template"), pk=pk
        )
        try:
            level = int(request.data.get("level", 1))
        except (TypeError, ValueError):
            level = 1
        code = exercise.template.code
        content = exercise.content

        if level >= 2:
            return Response(
                {"level": 2, "hint": answer_text(code, content)}
            )

        if code in ("multiple_choice", "listening"):
            options = content.get("options", [])
            correct = content.get("correct_index")
            wrong = [i for i in range(len(options)) if i != correct]
            random.shuffle(wrong)
            return Response({"level": 1, "eliminate": wrong[:2]})

        full = answer_text(code, content)
        return Response(
            {"level": 1, "hint": f"{full[:1]}…" if full else ""}
        )
