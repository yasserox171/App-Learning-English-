# نموذج البيانات — منصة تعلّم الإنجليزية (LMS)

> الأساس الذي يُبنى عليه كل شيء. الأسماء بالإنجليزية (للكود)، الشرح بالعربية.
> القاعدة: **PostgreSQL** — الإطار: **Django + DRF**.

---

## 1) المستخدمون والصلاحيات

### `User`
| الحقل | النوع | ملاحظات |
|---|---|---|
| `id` | UUID / BigInt | المفتاح الأساسي |
| `email` | string (unique) | |
| `password` | hashed | فارغ إذا الدخول عبر Google/Apple |
| `full_name` | string | |
| `role` | enum | `student` \| `teacher` \| `admin` |
| `native_language` | string | اللغة الأم |
| `learning_goal` | enum | `study` \| `work` \| `travel` \| `communication` |
| `app_language` | enum | `ar` \| `en` (لغة الواجهة لا المحتوى) |
| `is_active` | bool | |
| `created_at` | datetime | |

### `SocialAuth`
| `id` · `user_id` (FK) · `provider` (`google`\|`apple`) · `provider_uid` · `created_at` |

> الأستاذ لا يُسجّل ذاتياً — يُنشئه `admin` فقط (لا زر «دخول كأستاذ»).

---

## 2) هيكل المحتوى

### `Level`
| الحقل | النوع | ملاحظات |
|---|---|---|
| `id` | PK | |
| `code` | string | `A1`, `A2`, `B1`, `B2`, `C1` |
| `name` | string | مثل `A2 - Survival` |
| `name_fr` | string | مثل `Survie` |
| `order` | int | ترتيب العرض |
| `is_free` | bool | للنموذج التجاري (A1 مجاني جزئياً) |

### `Unit`
| `id` · `level_id` (FK) · `title` · `order` · `description` |

### `Lesson`
| `id` · `unit_id` (FK) · `title` · `order` · `description` |

### `LessonComponent` ← العمود الفقري المرن
كل درس = قائمة مكوّنات مرتّبة، كل مكوّن من نوع.
| الحقل | النوع | ملاحظات |
|---|---|---|
| `id` | PK | |
| `lesson_id` | FK | |
| `type` | enum | `video` \| `vocabulary` \| `text` \| `exercise` |
| `order` | int | ترتيب المكوّن داخل الدرس |
| `config` | JSON | إعدادات إضافية حسب النوع |

> الأستاذ يبني الدرس بإضافة مكوّنات بالترتيب الذي يريد — لا قالب ثابت.

---

## 3) محتوى المكوّنات

### `Video`
| `id` · `component_id` (FK) · `title` · `duration` · `storage_key` · `status` (`processing`\|`ready`) |

> **عزل الاستضافة:** نخزّن `storage_key` فقط (مرجع مجرّد). رابط البثّ الفعلي (HLS / `.m3u8`) يُولَّد وقت الطلب عبر طبقة خدمة. هكذا قرار الاستضافة لاحقاً (سيرفرك أو Bunny/Cloudflare) لا يغيّر قاعدة البيانات إطلاقاً.

### `VocabularyItem`
| `id` · `component_id` (FK) · `word` · `translation` · `audio_url` · `example_sentence` · `order` |

### `TextBlock`
| `id` · `component_id` (FK) · `content` (rich text / markdown) | — لشرح الدرس |

---

## 4) محرّك التمارين (الجوهر)

### `ExerciseTemplate`
| الحقل | النوع | ملاحظات |
|---|---|---|
| `id` | PK | |
| `code` | enum | `multiple_choice` · `true_false` · `fill_blank` · `matching` · `reorder` · `listening` · `pronunciation` · `final_test` |
| `name` | string | |
| `content_schema` | JSON | يحدّد شكل المحتوى المقبول لهذا القالب |
| `is_active` | bool | تفعيل/تعطيل قالب |

### `Exercise`
| الحقل | النوع | ملاحظات |
|---|---|---|
| `id` | PK | |
| `component_id` | FK | |
| `template_id` | FK → ExerciseTemplate | |
| `content` | JSON | المحتوى الفعلي، مطابق لـ`content_schema` |
| `points` | int | |
| `order` | int | |

**أمثلة على شكل `content` حسب القالب:**
```jsonc
// multiple_choice
{ "question": "Meaning of 'Airport'?",
  "options": ["مدرسة", "مطار", "مستشفى"],
  "correct_index": 1 }

// true_false
{ "statement": "London is in France.", "answer": false }

// fill_blank
{ "sentence": "I ___ a teacher.", "answer": "am" }

// matching
{ "pairs": [{"left":"Apple","right":"تفاحة"},
            {"left":"Book","right":"كتاب"}] }

// reorder
{ "words": ["am","I","a","student"],
  "correct_order": ["I","am","a","student"] }

// listening
{ "audio_url": "...", "question": "...", "options": [...], "correct_index": 0 }

// pronunciation
{ "target_text": "Boarding pass", "reference_audio_url": "..." }
```
> إضافة قالب جديد مستقبلاً = صفّ جديد في `ExerciseTemplate` + مكوّن عرض في Flutter. **لا تعديل على الجداول.**

### `ExerciseAttempt`
| `id` · `user_id` (FK) · `exercise_id` (FK) · `answer` (JSON) · `is_correct` · `score` · `attempted_at` |

---

## 5) التقدّم والتقييم

### `PlacementResult` (اختبار تحديد المستوى)
| `id` · `user_id` (FK) · `assigned_level_id` (FK) · `score` · `taken_at` |

### `Progress`
| الحقل | النوع | ملاحظات |
|---|---|---|
| `id` | PK | |
| `user_id` | FK | |
| `lesson_id` | FK | |
| `status` | enum | `not_started` \| `in_progress` \| `completed` |
| `score` | int | |
| `time_spent` | int (ثوانٍ) | |
| `completed_at` | datetime | |

> تقدّم المستوى (مثل `68% — 35/50`) يُحسب تجميعاً من `Progress`، لا يُخزّن.

### `Certificate`
| `id` · `user_id` (FK) · `level_id` (FK) · `certificate_number` (unique) · `pdf_url` · `issued_at` |

---

## خريطة العلاقات (ملخّص)
```
User ─< SocialAuth
User ─< Progress >─ Lesson
User ─< ExerciseAttempt >─ Exercise
User ─< PlacementResult >─ Level
User ─< Certificate >─ Level

Level ─< Unit ─< Lesson ─< LessonComponent
LessonComponent ─< Video
LessonComponent ─< VocabularyItem
LessonComponent ─< TextBlock
LessonComponent ─< Exercise >─ ExerciseTemplate
```

---

## قرارات مقصودة في هذا التصميم
1. **التمارين بـJSON موجّه بقالب** → مرونة بلا تعديل قاعدة البيانات.
2. **مكوّنات الدرس مرنة ومرتّبة** → الأستاذ يبني الدرس كما يشاء.
3. **عزل استضافة الفيديو** عبر `storage_key` → القرار يؤجَّل بأمان.
4. **التقدّم محسوب لا مخزّن** → لا تضارب في الأرقام.
5. **الأستاذ يُنشأ إدارياً** → لا واجهة تسجيل عامة له.
