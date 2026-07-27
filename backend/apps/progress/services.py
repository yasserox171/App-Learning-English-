"""Progress computation & certificate issuance (master prompt §8, §5).

Level progress is COMPUTED here, never stored.
"""
import uuid
from datetime import timedelta

from django.db.models import Sum
from django.db.models.functions import TruncDate
from django.utils import timezone

from apps.content.models import Lesson, LessonComponent, Level, Unit

from .models import (
    Certificate,
    LessonPhaseProgress,
    PlacementResult,
    Progress,
    UnitAssessment,
)

# Per-lesson progress is binary (completed / not), so map status -> percent for
# a friendlier UI ("متابعة 50%").
_STATUS_PERCENT = {
    Progress.Status.COMPLETED: 100,
    Progress.Status.IN_PROGRESS: 50,
    Progress.Status.NOT_STARTED: 0,
}

# Micro-learning phase number per step type (master UX prompt, feature 1).
PHASE_OF = {
    "text": 1,
    "vocabulary": 2,
    "video": 3,
    "exercise": 4,
    "evaluation": 5,
}


def compute_level_progress(user, level: Level) -> dict:
    """Aggregate a user's progress across all lessons in a level."""
    lesson_ids = list(
        Lesson.objects.filter(
            unit__level=level, status=Lesson.Status.PUBLISHED
        ).values_list("id", flat=True)
    )
    total = len(lesson_ids)

    qs = Progress.objects.filter(user=user, lesson_id__in=lesson_ids)
    completed = qs.filter(status=Progress.Status.COMPLETED).count()
    agg = qs.aggregate(points=Sum("score"), time=Sum("time_spent"))
    percent = round((completed / total) * 100) if total else 0

    return {
        "level_id": str(level.id),
        "level_code": level.code,
        "level_name": level.name,
        "total_lessons": total,
        "completed_lessons": completed,
        "percent": percent,
        "points": agg["points"] or 0,
        "time_spent": agg["time"] or 0,
        "is_completed": total > 0 and completed == total,
    }


def compute_streak(user) -> int:
    """Consecutive days (ending today or yesterday) with a completed lesson."""
    dates = set(
        Progress.objects.filter(user=user, completed_at__isnull=False)
        .annotate(day=TruncDate("completed_at"))
        .values_list("day", flat=True)
    )
    if not dates:
        return 0
    today = timezone.localdate()
    if today in dates:
        cursor = today
    elif (today - timedelta(days=1)) in dates:
        cursor = today - timedelta(days=1)
    else:
        return 0
    streak = 0
    while cursor in dates:
        streak += 1
        cursor -= timedelta(days=1)
    return streak


def total_xp(user) -> int:
    """Total XP = sum of all lesson scores earned by the user."""
    return Progress.objects.filter(user=user).aggregate(x=Sum("score"))["x"] or 0


def current_level(user, level_stats: list | None = None) -> dict | None:
    """The level the learner is actively on: the highest in-progress level,
    else the placement level, else the first not-yet-completed level."""
    levels = list(Level.objects.all().order_by("order"))
    if not levels:
        return None
    stats = {s["level_id"]: s for s in (level_stats or [])}

    def stat_for(level):
        return stats.get(str(level.id)) or compute_level_progress(user, level)

    chosen = None
    for level in levels:  # last (highest) with some progress but unfinished
        s = stat_for(level)
        if s["percent"] > 0 and not s["is_completed"]:
            chosen = level
    if chosen is None:
        placement = (
            PlacementResult.objects.filter(user=user)
            .order_by("-taken_at")
            .first()
        )
        if placement:
            chosen = placement.assigned_level
    if chosen is None:
        chosen = next(
            (l for l in levels if not stat_for(l)["is_completed"]), levels[-1]
        )
    s = stat_for(chosen)
    return {"code": chosen.code, "name": chosen.name, "percent": s["percent"]}


def continue_lesson(user) -> dict | None:
    """The most recently touched in-progress lesson, for the home dashboard."""
    progress = (
        Progress.objects.filter(user=user, status=Progress.Status.IN_PROGRESS)
        .select_related("lesson__unit__level")
        .order_by("-updated_at")
        .first()
    )
    if not progress:
        return None
    lesson = progress.lesson
    return {
        "lesson_id": str(lesson.id),
        "lesson_title": lesson.title,
        "unit_title": lesson.unit.title,
        "level_code": lesson.unit.level.code,
        "percent": _STATUS_PERCENT[Progress.Status.IN_PROGRESS],
        "thumbnail": _lesson_thumbnail(lesson),
    }


def _lesson_thumbnail(lesson) -> str:
    """First non-empty vocabulary image in the lesson — used as its card image."""
    for component in sorted(lesson.components.all(), key=lambda c: c.order):
        if component.type != LessonComponent.Type.VOCABULARY:
            continue
        for item in component.vocabulary_items.all():
            if item.image_url:
                return item.image_url
    return ""


def _lesson_steps(lesson) -> list:
    """Ordered step summary [{type, count, minutes}] derived from components.

    Pronunciation and final_test exercises are excluded from the count (the
    app hides the former and expands the latter into its referenced items)."""
    steps = []
    for component in sorted(lesson.components.all(), key=lambda c: c.order):
        ctype = component.type
        if ctype == LessonComponent.Type.TEXT:
            steps.append({"type": "text", "count": 1, "minutes": 1})
        elif ctype == LessonComponent.Type.VOCABULARY:
            n = len(component.vocabulary_items.all())
            if n:
                steps.append(
                    {"type": "vocabulary", "count": n, "minutes": max(1, n // 4)}
                )
        elif ctype == LessonComponent.Type.VIDEO:
            video = getattr(component, "video", None)
            if video:
                steps.append(
                    {
                        "type": "video",
                        "count": 1,
                        "minutes": max(1, (video.duration or 0) // 60),
                    }
                )
        elif ctype == LessonComponent.Type.EXERCISE:
            n = sum(
                1
                for e in component.exercises.all()
                if e.template.code not in ("pronunciation", "final_test")
            )
            if n:
                steps.append(
                    {"type": "exercise", "count": n, "minutes": max(1, round(n * 0.7))}
                )
    return steps


def units_overview(user, level_id) -> list:
    """Units of a level with progress, lock state, and embedded lesson rows —
    one response builds the whole level path (ABA-style timeline).

    Mastery gate: the next unit unlocks only when the previous unit's lessons
    are ALL completed AND its assessment was passed (>= 80%)."""
    units = list(Unit.objects.filter(level_id=level_id).order_by("order"))
    passed_units = set(
        UnitAssessment.objects.filter(
            user=user, unit__level_id=level_id, passed=True
        ).values_list("unit_id", flat=True)
    )
    result = []
    prev_mastered = True
    for i, unit in enumerate(units):
        lessons = lessons_overview(user, unit.id)
        total = len(lessons)
        completed = sum(
            1 for l in lessons if l["status"] == Progress.Status.COMPLETED
        )
        percent = round((completed / total) * 100) if total else 0
        is_completed = total > 0 and completed == total
        assessment_passed = unit.id in passed_units
        locked = not (i == 0 or prev_mastered)
        if locked:  # a locked unit locks all its lessons
            for l in lessons:
                l["locked"] = True
        result.append(
            {
                "id": str(unit.id),
                "title": unit.title,
                "description": unit.description,
                "order": unit.order,
                "total": total,
                "completed": completed,
                "percent": percent,
                "is_completed": is_completed,
                "locked": locked,
                "assessment_passed": assessment_passed,
                "assessment_ready": is_completed and not assessment_passed,
                "thumbnail": next(
                    (l["thumbnail"] for l in lessons if l["thumbnail"]), ""
                ),
                "lessons": lessons,
            }
        )
        prev_mastered = is_completed and assessment_passed
    return result


def lessons_overview(user, unit_id) -> list:
    """Lessons of a unit with per-lesson status/percent and sequential lock."""
    lessons = list(
        Lesson.objects.filter(unit_id=unit_id, status=Lesson.Status.PUBLISHED)
        .order_by("order")
        .prefetch_related(
            "components__vocabulary_items",
            "components__video",
            "components__exercises__template",
        )
    )
    by_lesson = {
        p.lesson_id: p
        for p in Progress.objects.filter(user=user, lesson__unit_id=unit_id)
    }
    phases_by_lesson: dict = {}
    for row in LessonPhaseProgress.objects.filter(
        user=user, lesson__unit_id=unit_id
    ):
        phases_by_lesson.setdefault(row.lesson_id, set()).add(row.phase)

    result = []
    prev_completed = True
    for i, lesson in enumerate(lessons):
        progress = by_lesson.get(lesson.id)
        status = progress.status if progress else Progress.Status.NOT_STARTED
        is_done = status == Progress.Status.COMPLETED
        done_phases = phases_by_lesson.get(lesson.id, set())
        steps = _lesson_steps(lesson)
        for s in steps:  # real partial progress, not all-or-nothing
            s["completed"] = is_done or PHASE_OF.get(s["type"], 0) in done_phases
        result.append(
            {
                "id": str(lesson.id),
                "title": lesson.title,
                "description": lesson.description,
                "order": lesson.order,
                "status": status,
                "percent": _STATUS_PERCENT.get(status, 0),
                "locked": not (i == 0 or prev_completed),
                "thumbnail": _lesson_thumbnail(lesson),
                "steps": steps,
            }
        )
        prev_completed = is_done
    return result


def overview(user) -> dict:
    """Per-level progress (with sequential lock) plus a gamification summary."""
    levels = list(Level.objects.all().order_by("order"))
    level_stats = []
    prev_completed = True
    for i, level in enumerate(levels):
        stats = compute_level_progress(user, level)
        stats["locked"] = not (level.is_free or i == 0 or prev_completed)
        level_stats.append(stats)
        prev_completed = stats["is_completed"]

    summary = {
        "xp": total_xp(user),
        "streak": compute_streak(user),
        "completed_lessons": sum(s["completed_lessons"] for s in level_stats),
        "total_lessons": sum(s["total_lessons"] for s in level_stats),
        "current_level": current_level(user, level_stats),
        "continue": continue_lesson(user),
    }
    return {"levels": level_stats, "summary": summary}


def maybe_issue_certificate(user, level: Level):
    """Issue a certificate when every lesson in the level is completed."""
    stats = compute_level_progress(user, level)
    if not stats["is_completed"]:
        return None
    certificate, _ = Certificate.objects.get_or_create(
        user=user,
        level=level,
        defaults={"certificate_number": _generate_number(level)},
    )
    return certificate


def _generate_number(level: Level) -> str:
    return f"CERT-{level.code}-{uuid.uuid4().hex[:8].upper()}"


def generate_certificate_pdf(certificate: Certificate) -> bytes:
    """Render the branded certificate PDF (dependency-free renderer — works
    on the Termux deployment, where reportlab isn't installed)."""
    from .certificate_pdf import generate_certificate_pdf as render

    return render(certificate)
