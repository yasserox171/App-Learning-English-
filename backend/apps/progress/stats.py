"""Advanced stats dashboard (UX prompt 2.2) — everything computed at read
time from existing tracking rows, in the same spirit as services.overview:

GET /user/stats/overview            headline numbers
GET /user/stats/vocabulary-heatmap  per-unit vocabulary mastery
GET /user/stats/grammar-skills      per-unit exercise accuracy chain
GET /user/stats/weak-areas          weakest units + a lesson to practice
GET /user/stats/time-investment     daily/weekly study time (last 30 days)
"""
from datetime import timedelta

from django.db.models import Count, Q, Sum
from django.utils import timezone
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.content.models import Lesson, Unit, VocabularyItem
from apps.exercises.models import ExerciseAttempt

from .models import Progress, VocabularyProgress
from .services import compute_streak, total_xp


def _accuracy_status(percent: int) -> str:
    """Shared bucket labels the app maps to ✅ / ⭐ / ⚠️ / ❌."""
    if percent >= 80:
        return "strong"
    if percent >= 50:
        return "growing"
    return "weak"


class StatsOverviewView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        total_lessons = Lesson.objects.count()
        completed = Progress.objects.filter(
            user=user, status=Progress.Status.COMPLETED
        ).count()
        vocab = VocabularyProgress.objects.filter(user=user)
        return Response({
            "overall_percent": round(completed * 100 / total_lessons)
            if total_lessons else 0,
            "lessons_completed": completed,
            "total_lessons": total_lessons,
            "words_learned": vocab.filter(
                status__in=[
                    VocabularyProgress.Status.LEARNED,
                    VocabularyProgress.Status.MASTERED,
                ]
            ).count(),
            "words_mastered": vocab.filter(
                status=VocabularyProgress.Status.MASTERED
            ).count(),
            "streak": compute_streak(user),
            "xp": total_xp(user),
            "total_time_seconds": Progress.objects.filter(user=user)
            .aggregate(s=Sum("time_spent"))["s"] or 0,
        })


class VocabularyHeatmapView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        # Words the user got right, grouped by the unit the word belongs to.
        learned_by_unit = dict(
            VocabularyProgress.objects.filter(
                user=user,
                status__in=[
                    VocabularyProgress.Status.LEARNED,
                    VocabularyProgress.Status.MASTERED,
                ],
            )
            .values_list("vocabulary_item__component__lesson__unit")
            .annotate(n=Count("id"))
        )
        units = (
            Unit.objects.filter(
                lessons__components__vocabulary_items__isnull=False
            )
            .distinct()
            .select_related("level")
            .annotate(total=Count("lessons__components__vocabulary_items"))
            .order_by("level__order", "order")
        )
        rows = []
        for unit in units:
            learned = learned_by_unit.get(unit.id, 0)
            percent = round(learned * 100 / unit.total) if unit.total else 0
            rows.append({
                "unit_id": str(unit.id),
                "title": unit.title,
                "level_code": unit.level.code,
                "total_words": unit.total,
                "learned_words": learned,
                "percent": percent,
                "status": _accuracy_status(percent),
            })
        return Response({"units": rows})


def _unit_accuracy(user):
    """(unit, attempts, correct) rows for every unit the user practised."""
    rows = (
        ExerciseAttempt.objects.filter(user=user)
        .values_list(
            "exercise__component__lesson__unit",
            "exercise__component__lesson__unit__title",
            "exercise__component__lesson__unit__level__code",
        )
        .annotate(attempts=Count("id"), correct=Count("id", filter=Q(is_correct=True)))
        .order_by(
            "exercise__component__lesson__unit__level__order",
            "exercise__component__lesson__unit__order",
        )
    )
    return [
        {
            "unit_id": str(unit_id),
            "title": title,
            "level_code": level_code,
            "attempts": attempts,
            "correct": correct,
            "accuracy": round(correct * 100 / attempts) if attempts else 0,
        }
        for unit_id, title, level_code, attempts, correct in rows
        if unit_id is not None
    ]


class GrammarSkillsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        skills = []
        for row in _unit_accuracy(request.user):
            skills.append({**row, "status": _accuracy_status(row["accuracy"])})
        return Response({"skills": skills})


class WeakAreasView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        MIN_ATTEMPTS = 3
        weakest = sorted(
            (
                r for r in _unit_accuracy(request.user)
                if r["attempts"] >= MIN_ATTEMPTS and r["accuracy"] < 80
            ),
            key=lambda r: r["accuracy"],
        )[:3]
        # Attach a lesson to jump into from the "Practice Now" button.
        for row in weakest:
            lesson = (
                Lesson.objects.filter(unit_id=row["unit_id"])
                .order_by("order")
                .first()
            )
            row["practice_lesson_id"] = str(lesson.id) if lesson else None
        return Response({"areas": weakest})


class TimeInvestmentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        """Daily study seconds over the last 30 days. time_spent accumulates
        on the lesson's progress row, so each row is attributed to the day it
        was last worked on — an approximation that is right for the common
        one-sitting lesson."""
        user = request.user
        today = timezone.localdate()
        start = today - timedelta(days=29)
        per_day = {start + timedelta(days=i): 0 for i in range(30)}
        rows = Progress.objects.filter(
            user=user, time_spent__gt=0, updated_at__date__gte=start
        ).values_list("updated_at", "time_spent")
        for updated_at, seconds in rows:
            day = timezone.localtime(updated_at).date()
            if day in per_day:
                per_day[day] += seconds

        days = [
            {"date": day.isoformat(), "seconds": secs}
            for day, secs in sorted(per_day.items())
        ]
        # Four 7-day windows covering the most recent 28 of the 30 days.
        weeks = []
        for w in range(4):
            chunk = days[2 + w * 7: 2 + (w + 1) * 7]
            weeks.append({
                "label": f"W{w + 1}",
                "seconds": sum(d["seconds"] for d in chunk),
            })
        return Response({
            "days": days,
            "weeks": weeks,
            "total_seconds": sum(d["seconds"] for d in days),
        })
