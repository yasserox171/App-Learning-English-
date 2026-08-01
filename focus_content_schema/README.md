# focus_content_schema

Validation and payload building between an LLM's raw content output and the
Focus Languages import API.

## Why this exists

The backend **does not validate exercise `content` at all**. `ExerciseTemplate`
stores a `content_schema`, and the API serves it to clients, but nothing ever
enforces it — the import endpoint checks only that `content` is a dict.

So a `multiple_choice` with no `correct_index` imports cleanly, returns `201`,
appears in the admin panel, and then marks every learner answer wrong forever.
Nothing logs an error. A `matching` pair missing its `right` key is worse: the
grader reads `p["left"]`/`p["right"]` with bracket access, so it raises
`KeyError` **during grading** — a 500 for a learner mid-lesson.

This package is the only line of defence. Validation here is strict and total:
every validator collects *all* errors and never raises.

```bash
pip install -e .
python -m focus_content_schema validate payload.json   # exit 1 + error list
```

---

## The five layers

```
LLM  ──emits──▶  IR  ──validate_ir_dict──▶  build_import_payload  ──validate_payload──▶  POST
                 ▲                                   ▲
            (1) ir.py                        (3) builder.py + media manifest
            (2) templates.py                 (4) payload.py
            (5) prompt.py renders the IR schema into the prompt
```

| Layer | Module | Job |
|---|---|---|
| 1 | `ir.py` | Pydantic models for what the LLM emits |
| 2 | `templates.py` | Strict per-template `content` rules |
| 3 | `builder.py` | IR + media manifest → import payload |
| 4 | `payload.py` | Final gate before the HTTP call |
| 5 | `prompt.py` | JSON Schema + few-shot fragment for the prompt |

---

## The IR contract

**This is what the LLM prompt is written against.** The IR is content only.
Everything positional, infrastructural or operational belongs to the builder,
so the model never has to invent it and can never get it wrong.

### The IR must never contain

| Forbidden | Why | Who supplies it |
|---|---|---|
| `order` | Sequence is list position | Builder, from index, starting at 1 |
| `storage_key` | Media isn't uploaded yet | Builder, from the manifest |
| absolute URLs | Same | Builder, from the manifest |
| `publish_mode` | Pipeline concern | `build_import_payload(...)` |
| `idempotency_key` | Pipeline concern | `build_import_payload(...)` |

These are enforced mechanically: every model sets `extra="forbid"`, so an IR
carrying `order` fails validation instead of being silently ignored.

### Media: logical ids only

The LLM references media by a descriptive local id:

```json
{ "asset": "vocab_passport_image" }
```

The builder resolves each id against the media manifest. An id with no manifest
entry is a hard error — a payload with a dangling reference is never emitted.

### Shape

```jsonc
{
  "components": [                       // ordered; at least one

    { "type": "text",
      "content": "# Markdown heading\n\nBody." },

    { "type": "video",
      "asset": { "asset": "lesson_intro_video" },
      "title": "Checking in",
      "duration": 120,                  // whole seconds, >= 1
      "segments": [                     // optional subtitles
        { "start": 0, "end": 4.5,
          "narration_en": "May I see your passport?",
          "subtitle_ar": "هل يمكنني رؤية جواز سفرك؟" }
      ]},

    { "type": "vocabulary",
      "items": [
        { "word": "passport",                     // required
          "translation": "جواز السفر",            // required
          "example_sentence": "Show your passport.",
          "image": { "asset": "vocab_passport_image" },
          "audio": { "asset": "vocab_passport_audio" },
          "syllables": "pass-port",
          "pronunciation_tip_ar": "",
          "difficulty": "" }
      ]},

    { "type": "exercise",
      "exercises": [
        { "template": "multiple_choice",
          "content": { /* template-specific, see below */ },
          "points": 1 }
      ]}
  ]
}
```

### Template rules

Eight templates. **`final_test` is rejected outright** — its content is
`{"exercise_ids": [...]}` referencing UUIDs of exercises that don't exist until
after this lesson is imported, so it can't be generated. Build it from the
admin panel afterwards.

| Template | `content` | Rules |
|---|---|---|
| `multiple_choice` | `question`, `options[]`, `correct_index` | ≥2 options, all distinct, index an integer in range |
| `true_false` | `statement`, `answer` | `answer` a real JSON boolean — not `"true"`, not `1` |
| `fill_blank` | `sentence`, `answer`, `options?` | `sentence` must contain `___`. `options` **optional** — omit it and the backend builds a word bank; if supplied it must contain the answer |
| `matching` | `pairs[]` of `{left, right}` | ≥2 pairs, **every** pair needs both sides non-empty, no duplicate `left` |
| `reorder` | `words[]`, `correct_order[]` | `correct_order` a true permutation of `words` (multiset, so duplicate words count) |
| `listening` | `audio_url`, `question`, `options[]`, `correct_index` | `audio_url` absolute (an `{"asset": …}` ref in the IR), ≥2 options, index in range |
| `pronunciation` | `target_text`, `reference_audio_url?` | `target_text` non-empty; the URL, if present, absolute |
| `dictation` | `answer`, `audio_url?`, `hint?`, `show_hint_after_attempts?` | `answer` non-empty; see note below |

#### On `dictation`

The codebase has **no dictation example**: the seed skips it and
`apps/common/tests.py` explicitly asserts it is the one template without sample
data. The shape above was settled here, derived from its seeded `content_schema`
row (which requires only `answer`). `audio_url` is optional by design — when
absent, the backend serializer sets `audio_text` to the answer so the client
speaks it with TTS while the learner never sees the text.

---

## Building a payload

```python
from focus_content_schema import (
    validate_ir_dict, build_import_payload, validate_payload,
)

errors = validate_ir_dict(llm_output)          # 1. check the LLM's work
if errors:
    raise ValueError(errors)

payload = build_import_payload(                # 2. resolve media, add order
    llm_output,
    media_manifest,                            # asset id -> upload response
    level="A1",
    unit={"title": "Travel", "order": 1},
    lesson={"title": "At the airport", "order": 1},
    idempotency_key="batch-2026-07/A1/lesson-01",
    publish_mode="draft",
    on_duplicate="replace",
)

errors = validate_payload(payload)             # 3. last gate
if errors:
    raise ValueError(errors)

requests.post(f"{API}/content/lessons/import", json=payload,
              headers={"Authorization": f"Bearer {key}"})
```

### `storage_key` vs `url` — the most likely bug

The media manifest maps a logical id to the upload API's response. Both fields
are strings that look like paths, and they are **not interchangeable**:

```python
media_manifest = {
    "lesson_intro_video": {
        "storage_key": "videos/9f2a1c04e7b3.mp4",                    # RELATIVE
        "url": "http://84.8.223.62/media/videos/9f2a1c04e7b3.mp4",   # ABSOLUTE
        "kind": "video",
    },
}
```

| Destination | Takes | Why |
|---|---|---|
| video component `storage_key` | **`storage_key`** | Resolved through `VideoService` at request time, so hosting can move to a CDN without rewriting rows |
| vocabulary `image_url` / `audio_url` | **`url`** | Django `URLField`s — a relative path fails validation |
| exercise `audio_url` / `reference_audio_url` | **`url`** | Rendered directly by the client |

The builder asserts the shape of what it pulls out of the manifest, so a swap
raises `BuildError` here rather than producing a lesson with broken media:

```
BuildError: components[1].asset: 'storage_key' for 'lesson_intro_video' is an
absolute URL ('http://…/x.mp4'). Video.storage_key must be relative — it is
resolved through VideoService. Did you put the manifest 'url' here?
```

Both directions are tested.

---

## Layer 5: one source of truth for the prompt

```python
from focus_content_schema import export_ir_json_schema, render_prompt_fragment

schema = export_ir_json_schema()          # JSON Schema of LessonIR
fragment = render_prompt_fragment()       # schema + rules + few-shot examples
```

The prompt is *generated from the models*, so the schema the LLM is shown and
the schema the validator enforces cannot drift. Change `ir.py` and the prompt
changes on the next render. A test asserts the bundled few-shot example passes
the package's own validator — a bad example would teach the model to produce
bad output.

```bash
python -m focus_content_schema prompt  -o prompt.md
python -m focus_content_schema schema  -o ir.schema.json
```

---

## CLI

```bash
python -m focus_content_schema validate     payload.json   # built payload
python -m focus_content_schema validate-ir  ir.json        # raw LLM output
python -m focus_content_schema schema  [-o out.json]
python -m focus_content_schema prompt  [-o out.md]
```

Exit codes: `0` valid, `1` invalid (errors on stderr), `2` unusable file.

```
$ python -m focus_content_schema validate bad.json
✗ bad.json: 1 error(s)
  - components[3].exercises[3]: matching: pairs[1] is missing 'right' — the
    grader uses bracket access and would raise KeyError
$ echo $?
1
```

---

## Tests

```bash
pip install -e ".[dev]" && pytest      # 145 tests
```

Golden fixtures for all eight templates plus a deliberately malformed case
each, the matching-missing-key case, and the storage_key/url swap in both
directions.

### Two documented divergences from the seed data

The golden fixtures come from
`backend/apps/common/management/commands/seed.py`, with two exceptions:

1. **`listening.audio_url` and `pronunciation.reference_audio_url` are relative
   in the seed** (`"samples/airport-announcement.mp3"`). They predate the media
   upload API. This package requires absolute URLs, so the fixtures use
   absolute ones — and `SEEDED_RELATIVE_MEDIA` keeps the originals so a test
   asserts the old form is now rejected. **If you re-import seed-era content
   through this pipeline, those two will fail validation.** That is intended:
   relative paths in a `URLField` are rejected by the server anyway.

2. **`dictation` has no seed example**, as described above.

### Compatibility

The builder's output is checked against the backend's own
`validate_lesson_json()` — the payload this package produces is accepted by the
real import API, not merely by its own rules.
