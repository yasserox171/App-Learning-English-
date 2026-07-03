"""Seed data for development & demo (master prompt §12, Phase 1).

Creates:
  - The six CEFR levels (A1..C2)
  - The eight exercise templates with their content schemas
  - A demo admin / teacher / student
  - A sample Unit → Lesson with ordered components (text, vocabulary, video)
    and one Exercise per template (incl. a final_test bundling the rest)

Idempotent: safe to run repeatedly (uses get_or_create / lookups by key).

Usage:  python manage.py seed
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.content.models import (
    Lesson,
    LessonComponent,
    Level,
    TextBlock,
    Unit,
    Video,
    VocabularyItem,
)
from apps.exercises.models import Exercise, ExerciseTemplate
from apps.users.models import User

# --------------------------------------------------------------------------- #
# Static seed definitions
# --------------------------------------------------------------------------- #
LEVELS = [
    ("A1", "A1 - Breakthrough", "Découverte", 1, True),
    ("A2", "A2 - Survival", "Survie", 2, False),
    ("B1", "B1 - Threshold", "Seuil", 3, False),
    ("B2", "B2 - Vantage", "Avancé", 4, False),
    ("C1", "C1 - Advanced", "Autonome", 5, False),
    ("C2", "C2 - Mastery", "Maîtrise", 6, False),
]

TEMPLATES = [
    (
        "multiple_choice", "Multiple Choice",
        {"type": "object",
         "required": ["question", "options", "correct_index"],
         "properties": {
             "question": {"type": "string"},
             "options": {"type": "array", "items": {"type": "string"}},
             "correct_index": {"type": "integer"}}},
    ),
    (
        "true_false", "True / False",
        {"type": "object",
         "required": ["statement", "answer"],
         "properties": {"statement": {"type": "string"},
                        "answer": {"type": "boolean"}}},
    ),
    (
        "fill_blank", "Fill in the Blank",
        {"type": "object",
         "required": ["sentence", "answer"],
         "properties": {"sentence": {"type": "string"},
                        "answer": {"type": "string"}}},
    ),
    (
        "matching", "Matching",
        {"type": "object",
         "required": ["pairs"],
         "properties": {"pairs": {"type": "array", "items": {
             "type": "object",
             "properties": {"left": {"type": "string"},
                            "right": {"type": "string"}}}}}},
    ),
    (
        "reorder", "Reorder",
        {"type": "object",
         "required": ["words", "correct_order"],
         "properties": {"words": {"type": "array", "items": {"type": "string"}},
                        "correct_order": {"type": "array",
                                          "items": {"type": "string"}}}},
    ),
    (
        "listening", "Listening",
        {"type": "object",
         "required": ["audio_url", "question", "options", "correct_index"],
         "properties": {"audio_url": {"type": "string"},
                        "question": {"type": "string"},
                        "options": {"type": "array", "items": {"type": "string"}},
                        "correct_index": {"type": "integer"}}},
    ),
    (
        "pronunciation", "Pronunciation",
        {"type": "object",
         "required": ["target_text"],
         "properties": {"target_text": {"type": "string"},
                        "reference_audio_url": {"type": "string"}}},
    ),
    (
        "dictation", "Dictation",
        {"type": "object",
         "required": ["answer"],
         "properties": {"audio_url": {"type": "string"},
                        "answer": {"type": "string"},
                        "hint": {"type": "string"},
                        "show_hint_after_attempts": {"type": "integer"}}},
    ),
    (
        "final_test", "Final Test",
        {"type": "object",
         "required": ["exercise_ids"],
         "properties": {"exercise_ids": {"type": "array",
                                         "items": {"type": "string"}}}},
    ),
]

DEMO_USERS = [
    ("admin@lms.test", "admin12345", User.Role.ADMIN, "Admin Demo", True, True),
    ("teacher@lms.test", "teacher12345", User.Role.TEACHER, "Teacher Demo", True, False),
    ("student@lms.test", "student12345", User.Role.STUDENT, "Student Demo", False, False),
]


class Command(BaseCommand):
    help = "Seed levels, exercise templates, demo users, and a sample lesson."

    @transaction.atomic
    def handle(self, *args, **options):
        self._seed_levels()
        templates = self._seed_templates()
        self._seed_users()
        self._seed_sample_lesson(templates)
        self.stdout.write(self.style.SUCCESS("Seed complete."))

    # ----------------------------------------------------------------- #
    def _seed_levels(self):
        for code, name, name_fr, order, is_free in LEVELS:
            Level.objects.update_or_create(
                code=code,
                defaults={"name": name, "name_fr": name_fr,
                          "order": order, "is_free": is_free},
            )
        self.stdout.write(f"Levels: {Level.objects.count()}")

    def _seed_templates(self):
        templates = {}
        for code, name, schema in TEMPLATES:
            tpl, _ = ExerciseTemplate.objects.update_or_create(
                code=code,
                defaults={"name": name, "content_schema": schema, "is_active": True},
            )
            templates[code] = tpl
        self.stdout.write(f"Templates: {ExerciseTemplate.objects.count()}")
        return templates

    def _seed_users(self):
        for email, pwd, role, name, is_staff, is_super in DEMO_USERS:
            if User.objects.filter(email=email).exists():
                continue
            if is_super:
                User.objects.create_superuser(email=email, password=pwd, full_name=name)
            else:
                u = User.objects.create_user(
                    email=email, password=pwd, full_name=name,
                    role=role, is_staff=is_staff,
                )
                u.save()
        self.stdout.write(f"Users: {User.objects.count()}")

    def _seed_sample_lesson(self, templates):
        level = Level.objects.get(code="A1")
        unit, _ = Unit.objects.get_or_create(
            level=level, order=1,
            defaults={"title": "At the Airport",
                      "description": "Travel basics: airports and check-in."},
        )
        lesson, _ = Lesson.objects.get_or_create(
            unit=unit, order=1,
            defaults={"title": "Checking in",
                      "description": "Vocabulary and dialogue for checking in."},
        )

        # Avoid duplicating components on re-run.
        if lesson.components.exists():
            self.stdout.write("Sample lesson already populated; skipping components.")
            return

        order = 0

        # 1) Text block (explanation)
        order += 1
        text_comp = LessonComponent.objects.create(
            lesson=lesson, type=LessonComponent.Type.TEXT, order=order)
        TextBlock.objects.create(
            component=text_comp,
            content="# Checking in\nLearn the words you need at the airport "
                    "check-in desk.")

        # 2) Vocabulary
        order += 1
        vocab_comp = LessonComponent.objects.create(
            lesson=lesson, type=LessonComponent.Type.VOCABULARY, order=order)
        # Demo image URLs use placehold.co (always load, show the word).
        # Teachers replace these with real images via Django Admin.
        vocab = [
            ("Airport", "مطار", "I am at the airport.",
             "https://placehold.co/400x300?text=Airport"),
            ("Boarding pass", "بطاقة الصعود", "Here is my boarding pass.",
             "https://placehold.co/400x300?text=Boarding+pass"),
            ("Passport", "جواز السفر", "Show me your passport, please.",
             "https://placehold.co/400x300?text=Passport"),
            ("Luggage", "أمتعة", "My luggage is heavy.",
             "https://placehold.co/400x300?text=Luggage"),
        ]
        for i, (word, tr, ex, img) in enumerate(vocab, start=1):
            VocabularyItem.objects.create(
                component=vocab_comp, word=word, translation=tr,
                example_sentence=ex, image_url=img, order=i)

        # 3) Video (storage_key only — hosting isolated, §7)
        order += 1
        video_comp = LessonComponent.objects.create(
            lesson=lesson, type=LessonComponent.Type.VIDEO, order=order)
        Video.objects.create(
            component=video_comp, title="Check-in dialogue",
            duration=120, storage_key="samples/checking-in.m3u8",
            status=Video.Status.READY)

        # 4) Exercises — one per non-final template, in a single exercise component
        order += 1
        ex_comp = LessonComponent.objects.create(
            lesson=lesson, type=LessonComponent.Type.EXERCISE, order=order)

        created = {}
        ex_order = 0

        def add(code, content, points=1):
            nonlocal ex_order
            ex_order += 1
            ex = Exercise.objects.create(
                component=ex_comp, template=templates[code],
                content=content, points=points, order=ex_order)
            created[code] = ex
            return ex

        add("multiple_choice", {
            "question": "What does 'Airport' mean?",
            "options": ["مدرسة", "مطار", "مستشفى"], "correct_index": 1})
        add("true_false", {
            "statement": "A boarding pass is needed to fly.", "answer": True})
        add("fill_blank", {
            "sentence": "I ___ a passenger.", "answer": "am"})
        add("matching", {"pairs": [
            {"left": "Airport", "right": "مطار"},
            {"left": "Passport", "right": "جواز السفر"}]})
        add("reorder", {
            "words": ["am", "I", "a", "passenger"],
            "correct_order": ["I", "am", "a", "passenger"]})
        add("listening", {
            "audio_url": "samples/airport-announcement.mp3",
            "question": "Which gate is mentioned?",
            "options": ["A1", "B2", "C3"], "correct_index": 1})
        add("pronunciation", {
            "target_text": "Boarding pass",
            "reference_audio_url": "samples/boarding-pass.mp3"})

        # 5) Final test bundling the above exercises
        order += 1
        final_comp = LessonComponent.objects.create(
            lesson=lesson, type=LessonComponent.Type.EXERCISE, order=order)
        Exercise.objects.create(
            component=final_comp, template=templates["final_test"],
            content={"exercise_ids": [str(e.id) for e in created.values()]},
            points=5, order=1)

        self.stdout.write(
            f"Sample lesson: {lesson.components.count()} components, "
            f"{Exercise.objects.count()} exercises.")
