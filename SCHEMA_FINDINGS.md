# SCHEMA_FINDINGS.md

Findings from reading the code at commit `559876d`. Every claim below is cited
to a file and line. Where the declared schema and the runtime behaviour differ,
both are reported — the runtime behaviour is what actually governs.

---

## 1. Exercise templates

### Where they are defined

Two places, and they are **not the same kind of authority**:

| Source | File | What it is |
|---|---|---|
| `ExerciseTemplate.Code` | `backend/apps/exercises/models.py:14-24` | Django `TextChoices` enum — the closed set of valid codes |
| `ExerciseTemplate.content_schema` | DB column, seeded from `backend/apps/common/management/commands/seed.py:43-116` | JSON Schema fragment stored per row, **descriptive only** |
| Correctors | `backend/apps/exercises/correctors.py` | The code that actually reads `content` at grading time |

Critically: **`content_schema` is never enforced.** It is a `JSONField` with the
help text *"Describes the accepted shape of Exercise.content"*
(`models.py:26-29`), it is serialized out to clients
(`apps/exercises/serializers.py:31-34`), but no validator reads it. The import
API checks only that `content` is a dict (`apps/content/importer.py:72-76`).
The real contract is therefore the corrector for each template.

### The 9 valid template names

`multiple_choice`, `true_false`, `fill_blank`, `matching`, `reorder`,
`listening`, `pronunciation`, `dictation`, `final_test`.

(The `models.py` docstring says "eight built-in exercise templates" — there are
nine `Code` members. The docstring is stale.)

### Per-template `content` shape

"Declared" = the seeded `content_schema`. "Read at runtime" = keys the corrector
in `correctors.py` actually accesses. "Stripped" = removed from student-facing
responses by `ANSWER_KEYS` in `apps/exercises/serializers.py:11`.

---

#### `multiple_choice`
- **Declared required:** `question` (string), `options` (string[]), `correct_index` (integer)
- **Runtime:** `content.get("correct_index")` — `correctors.py:56`; `options` read by `answer_text()` `correctors.py:197-202`
- **Stripped from client:** `correct_index`
- **Answer shape client sends:** `{"selected_index": int}`
- **Real example** (`seed.py:320-322`):
```json
{ "question": "What does 'Airport' mean?",
  "options": ["مدرسة", "مطار", "مستشفى"],
  "correct_index": 1 }
```

#### `true_false`
- **Declared required:** `statement` (string), `answer` (boolean)
- **Runtime:** `bool(content.get("answer"))` — `correctors.py:63`. `statement` is never read by the backend; it is display-only.
- **Stripped from client:** `answer`
- **Answer shape:** `{"answer": bool}`
- **Real example** (`seed.py:323-324`):
```json
{ "statement": "A boarding pass is needed to fly.", "answer": true }
```

#### `fill_blank`
- **Declared required:** `sentence` (string), `answer` (string)
- **Runtime:** `content.get("answer", "")`, compared case-insensitively after `.strip().casefold()` — `correctors.py:70`, `_norm()` at `:43-44`
- **Optional:** `options` (string[]). If absent, the serializer **generates a word bank at read time** from the lesson's vocabulary plus filler words, shuffled — `serializers.py:66-84`. Supplying your own `options` disables that.
- **Stripped from client:** `answer`
- **Answer shape:** `{"answer": str}`
- **Real example** (`seed.py:325-326`):
```json
{ "sentence": "I ___ a passenger.", "answer": "am" }
```

#### `matching`
- **Declared required:** `pairs` (array of `{left, right}`)
- **Runtime:** `p["left"]` and `p["right"]` — `correctors.py:78`. **These use bracket access, not `.get()`** — a pair missing either key raises `KeyError` during grading, not a validation error at import. This is the only template that can hard-fail on malformed content.
- **Not stripped:** `pairs` is not in `ANSWER_KEYS`, so the full answer key reaches the client (inherent to the matching UI).
- **Answer shape:** `{"pairs": [{"left": str, "right": str}, ...]}`
- **Scoring:** set intersection, partial credit = matched / expected — `correctors.py:86-88`
- **Real example** (`seed.py:327-329`):
```json
{ "pairs": [ {"left": "Airport",  "right": "مطار"},
             {"left": "Passport", "right": "جواز السفر"} ] }
```

#### `reorder`
- **Declared required:** `words` (string[]), `correct_order` (string[])
- **Runtime:** only `correct_order` is read — `correctors.py:94`. `words` is display-only (the shuffled bank shown to the learner).
- **Stripped from client:** `correct_order`
- **Answer shape:** `{"order": [str, ...]}`
- **Scoring:** exact sequence for pass; partial credit = positionally-correct count — `correctors.py:98-102`
- **Real example** (`seed.py:330-332`):
```json
{ "words": ["am", "I", "a", "passenger"],
  "correct_order": ["I", "am", "a", "passenger"] }
```

#### `listening`
- **Declared required:** `audio_url` (string), `question` (string), `options` (string[]), `correct_index` (integer)
- **Runtime:** `content.get("correct_index")` — `correctors.py:109`
- **Serializer adds:** `audio_text` = `options[correct_index]`, so the client can TTS the word without seeing the index — `serializers.py:55-59`
- **Stripped from client:** `correct_index`
- **Answer shape:** `{"selected_index": int}`
- **Real example** (`seed.py:333-336`):
```json
{ "audio_url": "samples/airport-announcement.mp3",
  "question": "Which gate is mentioned?",
  "options": ["A1", "B2", "C3"], "correct_index": 1 }
```

#### `pronunciation`
- **Declared required:** `target_text` (string). Optional: `reference_audio_url` (string)
- **Runtime:** `content.get("target_text", "")` — `correctors.py:172`
- **Not stripped:** `target_text` must reach the client (it's what the learner reads aloud)
- **Answer shape:** `{"spoken_text": str}`, legacy `{"transcript": str}` also accepted; `{"recorded": true}` with no text scores a lenient full mark — `correctors.py:170-177`
- **Scoring:** Levenshtein with reduced cost for Arabic-speaker confusions (θ/s/z/t, p/b, v/f, g/j, e/i, o/u), pass mark 0.7 — `correctors.py:119-128, 167`
- **Real example** (`seed.py:337-339`):
```json
{ "target_text": "Boarding pass",
  "reference_audio_url": "samples/boarding-pass.mp3" }
```

#### `dictation`
- **Declared required:** `answer` (string). Optional: `audio_url`, `hint` (string), `show_hint_after_attempts` (integer)
- **Runtime:** `content.get("answer", "")`, compared after stripping punctuation and collapsing whitespace — `correctors.py:186-192`
- **Serializer adds:** if `audio_url` is absent, sets `audio_text` = the answer so the client can TTS it — `serializers.py:63-64`
- **Stripped from client:** `answer`
- **Answer shape:** `{"answer": str}`
- **⚠️ No example exists anywhere.** Confirmed three ways: the live DB has **0 dictation exercises** (all other 8 templates have 1 each); `seed.py:320-339` skips it; and `apps/common/tests.py:31-33` explicitly asserts `codes - used <= {"dictation"}`, i.e. the test suite *codifies* that dictation is the one template with no sample data. A valid payload per the schema would be `{"answer": "I am a passenger.", "hint": "4 words"}`.

#### `final_test`
- **Declared required:** `exercise_ids` (string[] of Exercise UUIDs)
- **Runtime:** `correctors.py:227-249` — looks each ID up, dispatches to that exercise's own corrector, averages the fractions. Missing IDs are skipped but still count against the total (`:241-243`), so a stale ID silently lowers the score.
- **Answer shape:** `{"answers": {exercise_id: answer_obj, ...}}`
- **Real example** (`seed.py:344-347`) — IDs are generated at seed time, so this is only constructible after the referenced exercises exist:
```json
{ "exercise_ids": ["<uuid>", "<uuid>", "..."] }
```

### Answer-key stripping (applies to all templates)

`ANSWER_KEYS = ("correct_index", "answer", "correct_order")` —
`apps/exercises/serializers.py:11`, popped at `:86-87`. Note this strips by key
name across every template, which is why `matching.pairs` and
`pronunciation.target_text` still reach clients.

---

## 2. Video component `script` field

### Model

`backend/apps/content/models.py:103-127`. The field:

```python
script = models.JSONField(default=dict, blank=True)   # models.py:121
```

Declared structure, from the comment at `models.py:119-120`:

```json
{ "segments": [ {"start": 0.0, "end": 3.5,
                 "narration_en": "...", "subtitle_ar": "..."} ] }
```

- Type: JSON **object** (dict), defaulting to `{}`, `blank=True`
- Only the top-level key `segments` is ever read

### Validation: none

There is **no serializer validation on `script` whatsoever.** `VideoSerializer`
(`apps/content/serializers.py:42-57`) does not include `script` in its
`fields` tuple — it is write-never, read-never on the API surface. The only
write path is the importer:

```python
script=comp.get("script") or {}     # apps/content/importer.py:143
                                    # and management/commands/import_content.py:187
```

Any JSON shape is accepted and stored unvalidated. A malformed `script`
produces no error — it degrades to no subtitles.

### Who reads it

One backend reader, one client chain:

1. **`VideoSerializer.get_segments()`** — `apps/content/serializers.py:50-53`:
   ```python
   script = obj.script or {}
   return script.get("segments", [])
   ```
   The API exposes a derived `segments` array, **not** `script`. Serializer
   fields are `("id", "title", "duration", "status", "playback_url", "segments")`.

2. **Flutter** — `mobile/lib/features/content/lesson_flow.dart:107` pulls
   `p['segments']` into `videoSegments`, passed to
   `video_player_widget.dart:17`. `_onTick()` (`:71-86`) selects the active
   segment by `seg['start'] <= t < seg['end']`, both coerced with
   `(seg['start'] ?? 0).toDouble()` — so seconds, numeric, missing → 0.

3. **Subtitle keys are read with fallbacks** —
   `video_player_widget.dart:127-135`:
   - English: `narration_en` → `text_en` → `en` → `""`
   - Arabic: `subtitle_ar` → `text_ar` → `ar` → `""`

   So three key spellings work per language, though only `narration_en` /
   `subtitle_ar` are documented in the model.

**No production video currently uses this** — the seeded sample lesson creates
its Video without a `script`, so `segments` is `[]` in practice.

---

## 3. Content Import API status

### Yes — it exists and works today. Verified live.

- **Route:** `config/urls.py:19-20` → `path("content/lessons/import", LessonImportView.as_view(), name="content-lessons-import")`, mounted under `api/v1/` (`config/urls.py:27`)
- **View:** `backend/apps/adminpanel/views.py:622-676`
- **Live probe against the running server:**
  - no `Authorization` header → `403`
  - `Authorization: Bearer flk_invalidkey123456` → `403 {"error":{"status":403,"detail":"Invalid API key"}}`

```
POST http://84.8.223.62/api/v1/content/lessons/import
```

### Auth mechanism

`APIKeyAuthentication` — `backend/apps/adminpanel/auth.py:90-107`:

- Header `Authorization: Bearer <key>`; the key **must** start with `flk_` or the authenticator returns `None` (falls through to 403)
- Lookup is by `prefix` (first 12 chars, indexed) **plus** SHA-256 hash, `is_active=True` — `auth.py:100-102`
- Raw keys are never stored. `APIKey.generate()` (`models.py:84-88`) returns `"flk_" + secrets.token_urlsafe(32)` and persists only prefix + hash
- `last_used_at` is stamped on every successful auth (`auth.py:105-106`)
- Permission `HasValidAPIKey` (`auth.py:110-112`) requires `request.auth` to be an `APIKey`
- **Two trust tiers** — `APIKey.Trust`, `models.py:63-65`: `draft_only` (default) and `direct_publish`

> **There are currently 0 API keys in the database.** Mint one at
> `/admin-panel/` → *Team & API Keys* (Super Admin only). Shown once.

### Request schema

```jsonc
{
  "publish_mode": "draft",   // optional; "draft" (default) | "direct"
  "level": "A1",             // REQUIRED, must already exist
  "unit":   { "title": "...", "order": 0, "description": "" },   // title REQUIRED
  "lesson": { "title": "...", "order": 0, "description": "" },   // title REQUIRED
  "components": [ /* see below */ ]
}
```

Component variants — `importer.py:111-153`:

| `type` | Fields consumed |
|---|---|
| `text` | `content` (string, markdown) |
| `vocabulary` | `items[]`: `word` **(required)**, `translation`, `example_sentence`, `image_url`, `audio_url`, `syllables`, `pronunciation_tip_ar`, `difficulty`, `order` |
| `video` | `title`, `duration` (int, seconds), `storage_key`, `status` (`processing`\|`ready`, default `ready`), `script` (object) |
| `exercise` | `exercises[]`: `template` **(required)**, `content` **(required object)**, `points` (default 1), `order` |

All components also accept `order` (default 0) and `config` (object, default
`{}`) — `importer.py:112-117`.

Valid component types come from `LessonComponent.Type`:
`video`, `vocabulary`, `text`, `exercise` (`importer.py:19`).
Valid levels: `A1 A2 B1 B2 C1 C2`.

### Validation rules

`validate_lesson_json()` — `importer.py:28-83`. It returns a list of error
strings; **all** errors are collected, not just the first:

1. Payload must be a JSON object — `:32-33`
2. `level` required **and must already exist** in the DB — `:35-39`. The importer never creates levels.
3. `unit` must be an object with a truthy `title` — `:41-43`
4. `lesson` must be an object with a truthy `title` — `:45-47`
5. `components` must be a list if present (absent = empty) — `:52-55`
6. Each `components[i].type` must be one of the four — `:57-63`
7. For `exercise`: each `template` must match an existing `ExerciseTemplate.code`, and `content` must be a dict — `:64-76`
8. For `vocabulary`: each item needs a truthy `word` — `:77-82`

**What is NOT validated:**
- `content` is checked only for *being a dict* — its internal shape is never checked against `content_schema`. A `multiple_choice` with no `correct_index` imports cleanly and silently grades every answer wrong.
- `script` — anything accepted.
- `order`, `points`, `duration` — no type or range checks.
- Unknown/extra keys are ignored silently.

### Write behaviour

`import_lesson()` — `importer.py:86-154`, wrapped in `@transaction.atomic`:

- Unit is `get_or_create(level, title)` — reused if the title matches
- Lesson is **always `create`** (`:102`) — re-POSTing the same payload produces duplicate lessons. There is no upsert and no idempotency key.
- `status` = `published` for `direct`, `draft` for `draft` — `views.py:645-647`

### Publish modes and responses

- `publish_mode` defaults to `"draft"` — `views.py:632`
- Anything other than `draft`/`direct` → `400` — `views.py:633-637`
- `direct` with a `draft_only` key → `403 {"detail": "This API key may only submit drafts."}` — `views.py:639-643`
- **Success `201`** — `views.py:668-676`:
  ```json
  { "lesson_id": "<uuid>", "status": "draft",
    "publish_mode": "draft", "review_required": true }
  ```
- **Validation failure `400`** — `views.py:655-658`:
  ```json
  { "detail": "Validation failed.", "errors": ["components[0]: unknown type 'quiz'"] }
  ```

Every attempt — success **and** failure — writes an `ImportLog` row with the
API key, mode, content id and title (`views.py:651-654`, `:661-667`), visible
in the admin panel.

### CLI alternative

`python manage.py import_content lesson.json` —
`apps/content/management/commands/import_content.py`. Same JSON shape, plus
`--media-dir` and `--replace`, and it rewrites relative media paths to
`{media_base_url}/{media_dest}/{path}` and copies files into `MEDIA_ROOT`
(docstring `:1-19`). The HTTP API does **not** do this rewriting.

---

## 4. Media upload endpoints

### There is no media upload endpoint.

Exhaustive search across `backend/apps/` for `FileField`, `ImageField`,
`FileUploadParser`, `MultiPartParser`, `request.FILES` returns exactly one hit,
and it is not a media endpoint:

- `apps/tutor/views.py:82,100` — `SessionTurnView` accepts a multipart `audio`
  file, reads it into memory, forwards it to Whisper for transcription
  (`views.py:100-110`) and **discards it**. Nothing is persisted.

No route anywhere contains "upload" (`grep` over all `urls.py`). The admin panel
API has no media handling — `image_url`, `audio_url` and `storage_key` do not
appear in `apps/adminpanel/views.py`.

### How media gets in today

Three paths, all of which assume the file already exists somewhere:

1. **Absolute URLs in the JSON.** `image_url`/`audio_url` are `URLField`s
   (`content/models.py:136-137`); `storage_key` starting with `http://`/`https://`
   is returned verbatim as the playback URL
   (`apps/common/services.py:32-34`).
2. **`import_content` CLI with `--media-dir`** — copies local files into
   `MEDIA_ROOT/{media_dest}/` and rewrites the paths. This is the only
   file-moving code in the project, and it is CLI-only.
3. **Manual placement** under `MEDIA_ROOT` (`config/settings.py:154`,
   `BASE_DIR/media`), served at `/media/` — wired via
   `static(settings.MEDIA_URL, ...)` in `config/urls.py:44`, which is inside a
   `DEBUG`-guarded block, plus an nginx `alias /app/media/` in
   `backend/nginx.conf`.

**Gap:** to publish media purely over HTTP you must host the file yourself and
pass an absolute URL. Video delivery is abstracted behind `VideoService`
(`apps/common/services.py:14-40`) whose docstring states hosting is deferred and
the MVP `LocalVideoService` just prefixes `VIDEO_PLAYBACK_BASE_URL` — so adding
an upload endpoint later requires no changes to callers.

---

## Summary of gaps found

| # | Gap | Impact |
|---|---|---|
| 1 | `content_schema` is stored and served but never enforced | Malformed exercise `content` imports cleanly and fails silently at grading time |
| 2 | `matching` corrector uses `p["left"]` / `p["right"]` bracket access | Malformed pairs raise `KeyError` during grading rather than failing at import |
| 3 | No `dictation` example anywhere; the test suite codifies the omission | Only template with no reference payload |
| 4 | Lesson import is always `create`, never upsert | Re-running an import duplicates lessons |
| 5 | `script` has zero validation | Bad subtitle data degrades silently to no subtitles |
| 6 | No media upload endpoint | Media must be self-hosted and referenced by absolute URL, or loaded via the CLI |
| 7 | `models.py:12` docstring says "eight built-in exercise templates" | There are nine |
