"""Adaptive placement logic (v2 §1.2) — simple threshold walking, not CAT.

- Start at A2, rounds of 5 questions.
- >= 4/5 correct  -> move up one level.
- >= 3/5 wrong    -> move down one level.
- Otherwise (3/5 ~ 60-70%)          -> settle at the current level.
- Direction reversal or level edges -> settle (prevents ping-ponging).
- Hard cap of 4 rounds (15-20 questions total).

C2 is intentionally excluded — rarely relevant for placement (§1.2).
"""
import random

from django.db import transaction

from .models import PlacementQuestion, PlacementResult, PlacementSession

LEVELS = ["A1", "A2", "B1", "B2", "C1"]
START_LEVEL = "A2"
ROUND_SIZE = 5
MAX_ROUNDS = 4
UP_THRESHOLD = 4    # correct answers needed to move up
DOWN_THRESHOLD = 2  # correct answers at or below this move down


class PlacementError(Exception):
    pass


def _sanitize(questions):
    return [
        {
            "id": str(q.id),
            "level": q.level,
            "qtype": q.qtype,
            "passage": q.passage,
            "question": q.question,
            "options": q.options,
        }
        for q in questions
    ]


def _pick_round(session: PlacementSession, level: str):
    pool = list(
        PlacementQuestion.objects.filter(level=level, is_active=True)
        .exclude(id__in=session.asked_question_ids)
    )
    if len(pool) < ROUND_SIZE:
        # Bank exhausted at this level — allow repeats rather than crashing.
        pool = list(
            PlacementQuestion.objects.filter(level=level, is_active=True)
        )
    if not pool:
        raise PlacementError(f"No placement questions available for {level}")
    picked = random.sample(pool, min(ROUND_SIZE, len(pool)))
    session.asked_question_ids += [str(q.id) for q in picked]
    session.rounds.append(
        {"level": level, "question_ids": [str(q.id) for q in picked],
         "correct": None}
    )
    session.save()
    return picked


@transaction.atomic
def start_session(user) -> dict:
    """Abandon any dangling session and start fresh at A2."""
    PlacementSession.objects.filter(
        user=user, status=PlacementSession.Status.ACTIVE
    ).update(status=PlacementSession.Status.ABANDONED)

    session = PlacementSession.objects.create(
        user=user, current_level=START_LEVEL
    )
    questions = _pick_round(session, START_LEVEL)
    return {
        "session_id": str(session.id),
        "level": START_LEVEL,
        "round": 1,
        "questions": _sanitize(questions),
    }


def _visited_levels(session) -> list:
    return [r["level"] for r in session.rounds]


@transaction.atomic
def submit_round(session: PlacementSession, answers: dict) -> dict:
    """Grade the current round and either continue or settle."""
    if session.status != PlacementSession.Status.ACTIVE:
        raise PlacementError("Placement session is not active")
    if not session.rounds or session.rounds[-1]["correct"] is not None:
        raise PlacementError("No open round to grade")

    current = session.rounds[-1]
    questions = {
        str(q.id): q
        for q in PlacementQuestion.objects.filter(
            id__in=current["question_ids"]
        )
    }
    correct = sum(
        1
        for qid in current["question_ids"]
        if answers.get(qid) is not None
        and questions.get(qid) is not None
        and int(answers[qid]) == questions[qid].correct_index
    )
    current["correct"] = correct

    level_idx = LEVELS.index(session.current_level)
    settle = False

    if correct >= UP_THRESHOLD:
        if level_idx == len(LEVELS) - 1:
            settle = True  # aced C1 → settle at C1
        else:
            next_level = LEVELS[level_idx + 1]
            if next_level in _visited_levels(session):
                settle = True  # reversal — already tested there
            else:
                session.current_level = next_level
    elif correct <= DOWN_THRESHOLD:
        if level_idx == 0:
            settle = True  # struggling at A1 → settle at A1
        else:
            next_level = LEVELS[level_idx - 1]
            if next_level in _visited_levels(session):
                # Went up earlier, now falling back → the lower level is it.
                session.current_level = next_level
                settle = True
            else:
                session.current_level = next_level
    else:
        settle = True  # ~60-70% correct → this level fits

    if not settle and len(session.rounds) >= MAX_ROUNDS:
        settle = True

    if settle:
        session.status = PlacementSession.Status.COMPLETED
        session.suggested_level = session.current_level
        session.save()

        from apps.content.models import Level

        level = Level.objects.filter(code=session.current_level).first()
        total_correct = sum(r["correct"] or 0 for r in session.rounds)
        total_asked = sum(len(r["question_ids"]) for r in session.rounds)
        if level is not None:
            PlacementResult.objects.create(
                user=session.user, assigned_level=level, score=total_correct
            )
        return {
            "completed": True,
            "suggested_level": session.suggested_level,
            "correct": total_correct,
            "total": total_asked,
            # Result screen (§1.2): suggested level is the prominent default,
            # but the user can always start at A1 or pick manually.
            "options": {
                "default": session.suggested_level,
                "start_from_beginning": "A1",
                "manual_choice": LEVELS,
            },
        }

    session.save()
    next_questions = _pick_round(session, session.current_level)
    return {
        "completed": False,
        "level": session.current_level,
        "round": len(session.rounds),
        "questions": _sanitize(next_questions),
    }
