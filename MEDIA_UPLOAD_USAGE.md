# Media Upload & Idempotent Import — usage

Two endpoints for an automated content pipeline: upload the media, then import
the lesson that references it. Both take the same API key, and both are safe to
retry.

Base URL below is the deployed server; swap in your own host as needed.

```
http://84.8.223.62/api/v1
```

## Getting an API key

Admin panel → **Team & API Keys** → *Generate* (Super Admin only). The raw key
is shown **once**; only a SHA-256 hash is stored.

| Trust tier | Can upload media | Can import drafts | Can publish directly |
|---|---|---|---|
| `draft_only` (default) | yes | yes | no — 403 |
| `direct_publish` | yes | yes | yes |

Uploading stores bytes but publishes nothing, so any valid key may upload. The
tier still gates whether the *lesson* referencing that media goes live.

---

## 1. Upload media

```
POST /api/v1/content/media/upload
Authorization: Bearer <api_key>
Content-Type: multipart/form-data
```

| Field | Required | Notes |
|---|---|---|
| `file` | yes | The binary. Streamed to disk in chunks, never buffered whole. |
| `kind` | yes | `video` \| `image` \| `audio` — decides the directory and the rules. |
| `filename` | no | Only its **extension** is honoured; the stored name is the content hash. |

```bash
curl -X POST http://84.8.223.62/api/v1/content/media/upload \
  -H "Authorization: Bearer flk_xxxxxxxxxxxx" \
  -F "file=@lesson-01-intro.mp4" \
  -F "kind=video"
```

**201 Created**

```json
{
  "storage_key": "videos/9f2a1c04e7b3....mp4",
  "url": "http://84.8.223.62/media/videos/9f2a1c04e7b3....mp4",
  "kind": "video",
  "size": 18402311,
  "sha256": "9f2a1c04e7b3...",
  "deduplicated": false
}
```

### `storage_key` vs `url` — not interchangeable

This is the one thing to get right:

| Use | Field | Why |
|---|---|---|
| Video component `storage_key` | **`storage_key`** (relative) | Resolved through `VideoService` at request time, so hosting can move to a CDN without rewriting rows. |
| Vocabulary `image_url` / `audio_url` | **`url`** (absolute) | These are Django `URLField`s — a relative path fails validation. |
| Exercise `audio_url` / `reference_audio_url` | **`url`** (absolute) | Rendered directly by the client. |

Both come from the same base (`VIDEO_PLAYBACK_BASE_URL`), so they never
disagree.

### Deduplication

The stored filename **is** the content hash. Re-uploading identical bytes
returns the same `storage_key` with `"deduplicated": true` and does not rewrite
the file — so an orchestrator can retry an upload for free, and the same asset
referenced by ten lessons is stored once.

### Limits and rejections

| Kind | Directory | Allowed extensions | Default cap |
|---|---|---|---|
| `video` | `videos/` | `.mp4 .m3u8 .mov .webm .mkv` | 200 MB |
| `image` | `images/` | `.png .jpg .jpeg .webp .gif .svg` | 10 MB |
| `audio` | `audio/` | `.mp3 .m4a .wav .ogg .aac .opus` | 25 MB |

Caps are env-configurable: `MEDIA_MAX_VIDEO_MB`, `MEDIA_MAX_IMAGE_MB`,
`MEDIA_MAX_AUDIO_MB`. nginx `client_max_body_size` is `210m`, deliberately
above the video cap so an oversized upload gets a JSON 400 from Django rather
than an unparseable HTML 413 from nginx.

**400** — missing `file`, unknown `kind`, extension not allowed for that kind,
empty file, or over the cap:

```json
{ "detail": "Extension '.exe' is not allowed for kind 'image'. Allowed: .gif, .jpeg, .jpg, .png, .svg, .webp" }
```

**403** — missing or invalid key: `{"error": {"status": 403, "detail": "Invalid API key"}}`

Filenames are sanitised to their basename, so `../../../etc/passwd.png` cannot
escape `MEDIA_ROOT`; only the extension survives anyway.

---

## 2. Import the lesson

```
POST /api/v1/content/lessons/import
Authorization: Bearer <api_key>
Content-Type: application/json
```

### Idempotency

| Field | Default | Effect |
|---|---|---|
| `idempotency_key` | *(none)* | Stored on the lesson. Reusing it resolves to the same row instead of duplicating. |
| `on_duplicate` | `"skip"` | `skip` → leave the existing lesson untouched. `replace` → rebuild its components from this payload, keeping the same `lesson_id`. |

| Situation | Status | `action` | `duplicate` |
|---|---|---|---|
| No `idempotency_key` | `201` | `created` | `false` |
| New key | `201` | `created` | `false` |
| Known key, `skip` | `200` | `skipped` | `true` |
| Known key, `replace` | `200` | `replaced` | `true` |

**Omitting `idempotency_key` preserves the original behaviour exactly** — every
POST creates a new lesson. Idempotency is opt-in.

`201` means a row was created; `200` means an existing one was resolved. A
pipeline can branch on the status code alone.

Keys are unique across all lessons, enforced by a partial unique index. Two
concurrent POSTs with the same key are safe: the loser's insert hits the
constraint and resolves to the winner's row rather than erroring. Every
outcome — skips included — is written to the import log with its `action`, so a
retry storm is visible in the admin panel.

---

## Worked example: upload, then reference

**Step 1 — upload the three assets.**

```bash
API=http://84.8.223.62/api/v1
KEY=flk_xxxxxxxxxxxx

VIDEO=$(curl -s -X POST $API/content/media/upload -H "Authorization: Bearer $KEY" \
  -F "file=@airport.mp4" -F "kind=video")
IMAGE=$(curl -s -X POST $API/content/media/upload -H "Authorization: Bearer $KEY" \
  -F "file=@passport.png" -F "kind=image")
AUDIO=$(curl -s -X POST $API/content/media/upload -H "Authorization: Bearer $KEY" \
  -F "file=@passport.mp3" -F "kind=audio")

VIDEO_KEY=$(echo "$VIDEO" | jq -r .storage_key)   # relative  -> video component
IMAGE_URL=$(echo "$IMAGE" | jq -r .url)           # absolute  -> vocabulary
AUDIO_URL=$(echo "$AUDIO" | jq -r .url)           # absolute  -> vocabulary
```

**Step 2 — import, threading each field into the right slot.**

```bash
cat > lesson.json <<JSON
{
  "idempotency_key": "batch-2026-07/A1/lesson-01",
  "on_duplicate": "replace",
  "publish_mode": "draft",

  "level": "A1",
  "unit":   { "title": "Travel", "order": 1 },
  "lesson": { "title": "At the airport", "order": 1,
              "description": "Checking in and boarding." },

  "components": [
    { "type": "text", "order": 1,
      "content": "# At the airport\n\nYou need a passport to fly." },

    { "type": "video", "order": 2,
      "title": "Checking in",
      "duration": 180,
      "storage_key": "$VIDEO_KEY",
      "status": "ready",
      "script": { "segments": [
        { "start": 0, "end": 4,
          "narration_en": "Good morning, may I see your passport?",
          "subtitle_ar": "صباح الخير، هل يمكنني رؤية جواز سفرك؟" }
      ]}
    },

    { "type": "vocabulary", "order": 3, "items": [
      { "word": "passport", "translation": "جواز السفر",
        "example_sentence": "Show your passport at the gate.",
        "image_url": "$IMAGE_URL",
        "audio_url": "$AUDIO_URL",
        "order": 1 }
    ]},

    { "type": "exercise", "order": 4, "exercises": [
      { "template": "multiple_choice", "points": 1,
        "content": { "question": "What do you need to fly?",
                     "options": ["A passport", "A ticket only", "Nothing"],
                     "correct_index": 0 } }
    ]}
  ]
}
JSON

curl -X POST $API/content/lessons/import \
  -H "Authorization: Bearer $KEY" \
  -H "Content-Type: application/json" \
  -d @lesson.json
```

**201 Created**

```json
{
  "lesson_id": "a05947cd-....",
  "status": "draft",
  "publish_mode": "draft",
  "review_required": true,
  "action": "created",
  "duplicate": false
}
```

Re-running the identical command returns **200** with `"action": "replaced"`
and the **same** `lesson_id` — components rebuilt, nothing duplicated. Change
`on_duplicate` to `"skip"` (or omit it) and the second run becomes a no-op
returning `"action": "skipped"`.

Note the asymmetry in the payload: the video takes `"$VIDEO_KEY"`
(`videos/....mp4`) while the vocabulary takes `"$IMAGE_URL"` /`"$AUDIO_URL"`
(full `http://...`). Swapping them fails — the `URLField`s reject a relative
path, and a video `storage_key` holding an absolute URL bypasses the hosting
abstraction.

---

## Batch pipeline sketch

```python
for lesson in lessons:                      # 180 of them
    media = {}
    for asset in lesson.assets:             # dedupe makes re-uploads free
        media[asset.id] = upload(asset.path, kind=asset.kind)

    resp = import_lesson(
        build_payload(lesson, media),
        idempotency_key=f"batch-2026-07/{lesson.level}/{lesson.slug}",
        on_duplicate="replace",             # regenerate freely
    )
    assert resp.status_code in (200, 201)   # both are success
```

Crash halfway and rerun the whole batch: already-uploaded media dedupes,
already-imported lessons resolve by key. Nothing duplicates.

Drafts stay invisible to students until approved in the admin panel's Lesson
Review queue.
