"""LLM content pipeline for News & Stories (v2 §2.2).

News articles are NEVER shown verbatim (copyright risk): the source article is
fed to Claude with instructions to fully REWRITE it as an original, simplified
educational article at a target CEFR level. Stories are generated from scratch.
Each piece gets 2-3 auto-generated comprehension questions.

Requires ANTHROPIC_API_KEY. Everything returns structured dicts so the
management command can store results as reviewable drafts.
"""
import json

from django.conf import settings

CLAUDE_MODEL = getattr(settings, "CLAUDE_MODEL", "claude-opus-5")

_QUESTION_SCHEMA = """
Return ONLY valid JSON with this exact shape:
{
  "title_en": "...",
  "title_ar": "...(Arabic translation of the title)",
  "summary": "...(~40 words, simple English)",
  "body": "...(the full article/story text)",
  "questions": [
    {"template": "multiple_choice",
     "content": {"question": "...", "options": ["...","...","..."], "correct_index": 0}},
    {"template": "true_false",
     "content": {"statement": "...", "answer": true}},
    {"template": "multiple_choice",
     "content": {"question": "...", "options": ["...","...","..."], "correct_index": 1}}
  ]
}
"""


class LLMUnavailable(Exception):
    pass


def _client():
    try:
        import anthropic
    except ImportError as exc:
        raise LLMUnavailable("anthropic SDK is not installed") from exc
    api_key = getattr(settings, "ANTHROPIC_API_KEY", "")
    if not api_key:
        raise LLMUnavailable("ANTHROPIC_API_KEY is not configured")
    return anthropic.Anthropic(api_key=api_key)


def _generate(prompt: str) -> dict:
    client = _client()
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=2048,
        system=(
            "You create original English-learning content for Arabic-speaking "
            "learners. You always answer with only the requested JSON — no "
            "markdown fences, no commentary."
        ),
        messages=[{"role": "user", "content": prompt}],
    )
    if response.stop_reason == "refusal":
        raise LLMUnavailable("Model declined to generate this content")
    text = next((b.text for b in response.content if b.type == "text"), "")
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        raise LLMUnavailable("Model returned no JSON")
    return json.loads(text[start : end + 1])


def rewrite_news_article(*, source_title: str, source_text: str,
                         level: str) -> dict:
    """Full rewrite — original wording and structure, never a translation or
    summary that mirrors the source (v2 §2.2)."""
    prompt = f"""A news event is described below. Write a COMPLETELY ORIGINAL short
educational news article about the same event for an English learner at CEFR
level {level}.

Rules:
- Do NOT reuse the source's sentences, phrasing, or structure. Write it fresh,
  as if you were a teacher explaining the event.
- Vocabulary and grammar must match CEFR {level}. Keep it to 120-180 words.
- Neutral, positive-leaning educational tone. No opinions, no politics beyond
  the facts, nothing graphic.
- Then write exactly 3 comprehension questions about YOUR article
  (not the source).

Source event (for facts only):
Title: {source_title}
Text: {source_text}

{_QUESTION_SCHEMA}"""
    return _generate(prompt)


def generate_story(*, topic: str, level: str, country_hint: str = "") -> dict:
    """Entirely original story — no external source (v2 §2.2)."""
    locality = f" The story may be set in or reference {country_hint}." if country_hint else ""
    prompt = f"""Write an original short story for an English learner at CEFR level
{level}, on the topic: "{topic}".{locality}

Rules:
- 120-200 words, vocabulary and grammar strictly at CEFR {level}.
- Engaging, warm, culturally appropriate for readers across the Arab world.
- Then write exactly 3 comprehension questions about the story.

{_QUESTION_SCHEMA}"""
    return _generate(prompt)


def categorize(title: str, text: str, category_codes: list[str]) -> str:
    """Pick the best category code for a source article."""
    prompt = (
        f"Categories: {', '.join(category_codes)}\n"
        f"Title: {title}\nText: {text}\n"
        "Reply with exactly one category code from the list, nothing else."
    )
    client = _client()
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=16,
        output_config={"effort": "low"},
        messages=[{"role": "user", "content": prompt}],
    )
    if response.stop_reason == "refusal":
        return category_codes[0] if category_codes else ""
    text_out = next(
        (b.text for b in response.content if b.type == "text"), ""
    ).strip().lower()
    return text_out if text_out in category_codes else (
        category_codes[0] if category_codes else ""
    )
