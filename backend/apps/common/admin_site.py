"""Custom admin site with a statistics dashboard (master prompt §6, Phase 6)."""
from datetime import timedelta

from django.contrib.admin import AdminSite
from django.db.models.functions import TruncDate
from django.db.models import Count
from django.utils import timezone


class LMSAdminSite(AdminSite):
    site_header = "English Learning LMS — Administration"
    site_title = "LMS Admin"
    index_title = "Dashboard"

    def index(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["stats"] = self._stats()
        extra_context["daily_activity"] = self._daily_activity()
        return super().index(request, extra_context)

    def _stats(self):
        from apps.content.models import Lesson, Level, Unit
        from apps.exercises.models import Exercise, ExerciseAttempt
        from apps.progress.models import Certificate
        from apps.users.models import User

        return {
            "users_total": User.objects.count(),
            "students": User.objects.filter(role=User.Role.STUDENT).count(),
            "teachers": User.objects.filter(role=User.Role.TEACHER).count(),
            "admins": User.objects.filter(role=User.Role.ADMIN).count(),
            "levels": Level.objects.count(),
            "units": Unit.objects.count(),
            "lessons": Lesson.objects.count(),
            "exercises": Exercise.objects.count(),
            "attempts": ExerciseAttempt.objects.count(),
            "certificates": Certificate.objects.count(),
        }

    def _daily_activity(self, days=7):
        from apps.exercises.models import ExerciseAttempt

        since = timezone.now() - timedelta(days=days)
        rows = (
            ExerciseAttempt.objects.filter(attempted_at__gte=since)
            .annotate(day=TruncDate("attempted_at"))
            .values("day")
            .annotate(count=Count("id"))
            .order_by("day")
        )
        return [{"day": r["day"], "count": r["count"]} for r in rows]
