"""Reprocess existing lessons for selective translation (v2 §1.1).

Runs the 180 existing lessons against the word list + lesson-level rule and
stores WordAnnotations. Only the ambiguous cases (idioms, multi-meaning,
missing translations) are optionally sent to the LLM — lesson content itself
is never regenerated.

Usage:
    python manage.py annotate_lessons              # rule-based pass
    python manage.py annotate_lessons --llm        # + LLM review of flagged
    python manage.py annotate_lessons --lesson <uuid>
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.content.models import Lesson, WordAnnotation
from apps.content.translation import annotate_lesson


class Command(BaseCommand):
    help = "Annotate lessons with selectively-translated words."

    def add_arguments(self, parser):
        parser.add_argument("--lesson", help="Only this lesson id")
        parser.add_argument("--llm", action="store_true",
                            help="Resolve needs_review annotations via Claude")

    def handle(self, *args, **options):
        lessons = Lesson.objects.select_related("unit__level").prefetch_related(
            "components__text_block",
            "components__vocabulary_items",
            "components__exercises",
        )
        if options["lesson"]:
            lessons = lessons.filter(id=options["lesson"])

        totals = {"auto": 0, "idiom": 0, "multi_meaning": 0,
                  "target_vocab": 0, "needs_review": 0}
        for lesson in lessons:
            with transaction.atomic():
                counts = annotate_lesson(lesson)
            for key in totals:
                totals[key] += counts[key]

        self.stdout.write(self.style.SUCCESS(
            f"Annotated {lessons.count()} lesson(s): "
            f"{totals['auto']} auto, {totals['idiom']} idioms, "
            f"{totals['multi_meaning']} multi-meaning, "
            f"{totals['target_vocab']} target vocab "
            f"({totals['needs_review']} flagged for review)."
        ))

        if options["llm"]:
            self._llm_review()

    def _llm_review(self):
        """Send flagged annotations to Claude for context-aware translation."""
        import json

        from django.conf import settings

        try:
            import anthropic
        except ImportError:
            self.stderr.write("anthropic SDK not installed — skipping LLM pass.")
            return
        if not getattr(settings, "ANTHROPIC_API_KEY", ""):
            self.stderr.write("ANTHROPIC_API_KEY not set — skipping LLM pass.")
            return

        from apps.content.translation import lesson_text

        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        pending = (
            WordAnnotation.objects.filter(needs_review=True)
            .select_related("lesson__unit__level")
            .order_by("lesson_id")
        )
        by_lesson: dict = {}
        for ann in pending:
            by_lesson.setdefault(ann.lesson, []).append(ann)

        for lesson, annotations in by_lesson.items():
            context = lesson_text(lesson)[:4000]
            words = [a.word for a in annotations]
            prompt = (
                "For each English word below, give the Arabic translation of "
                "the meaning it has IN THIS LESSON'S CONTEXT (not the most "
                "common meaning).\n\n"
                f"Lesson text:\n{context}\n\nWords: {', '.join(words)}\n\n"
                'Reply with only JSON: {"word": "arabic translation", ...}'
            )
            try:
                response = client.messages.create(
                    model=getattr(settings, "CLAUDE_MODEL", "claude-opus-5"),
                    max_tokens=1024,
                    messages=[{"role": "user", "content": prompt}],
                )
                if response.stop_reason == "refusal":
                    continue
                text = next(
                    (b.text for b in response.content if b.type == "text"), ""
                )
                start, end = text.find("{"), text.rfind("}")
                translations = json.loads(text[start:end + 1])
            except Exception as exc:  # keep the batch going
                self.stderr.write(f"  LLM review failed for {lesson.id}: {exc}")
                continue

            for ann in annotations:
                new_translation = translations.get(ann.word)
                if new_translation:
                    ann.translation_ar = str(new_translation)[:255]
                    ann.needs_review = False
                    ann.save(update_fields=["translation_ar", "needs_review"])
            self.stdout.write(f"  Reviewed {len(annotations)} words in "
                              f"{lesson.title}")
