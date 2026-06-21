# البرومبت الرئيسي — منصة تعلّم الإنجليزية (LMS)
### يُعطى لـClaude Code كنقطة انطلاق واحدة لبناء المشروع

> **تعليمات للـAI:** اقرأ هذا الملف كاملاً قبل كتابة أي كود. ثم أعد صياغة خطتك لي
> باختصار وانتظر تأكيدي قبل البدء. ابنِ المشروع **مرحلةً مرحلة** بالترتيب المذكور في
> القسم 12. لا تغيّر نموذج البيانات أو القرارات المحسومة دون أن تسألني.

---

## 1) السياق والدور

أنت مهندس برمجيات كامل (full-stack) تبني نظام إدارة تعلّم (LMS) متخصصاً في تعليم
اللغة الإنجليزية للناطقين بالعربية. المالك يدير مركزاً تعليمياً في المغرب ويعمل
بالعربية والفرنسية. الكود وأسماء المتغيّرات والمسارات بالإنجليزية؛ التعليقات يمكن أن
تكون مختصرة بالإنجليزية.

بيئة التطوير: **Windows + WSL (Ubuntu)**، يُشغَّل عبر VS Code. تأكّد أن كل الأوامر
والإعداد متوافقة مع Linux/WSL.

---

## 2) نظرة عامة على المشروع

منصة رقمية متكاملة لتعلّم الإنجليزية، تعمل عبر:
- **تطبيق هاتف** (Android / iOS) + **تطبيق ويب**، من قاعدة كود واحدة بـ**Flutter**.
- **Backend** بـ**Django + Django REST Framework**.

تقدّم مساراً تعليمياً منظّماً حسب الإطار الأوروبي **CEFR**: `A1 → A2 → B1 → B2 → C1`.
كل مستوى يحتوي وحدات، كل وحدة دروساً، كل درس **مكوّنات مرنة** (فيديو، مفردات، شرح،
تمارين). الميزة الأساسية ليست التقنية بل **نظام المحتوى المرن وقوالب التمارين الجاهزة**
التي تتيح للأستاذ بناء الدروس بسهولة.

---

## 3) القرارات المحسومة (لا تغيّرها دون سؤال)

| القرار | الاختيار |
|---|---|
| Frontend | **Flutter** (Android + iOS + Web من كود واحد) |
| Backend | **Django 5.x + Django REST Framework** |
| Database | **PostgreSQL** |
| المفاتيح الأساسية (`id`) | **UUID** |
| المصادقة | **JWT** (`djangorestframework-simplejwt`) + Google + Apple |
| لوحة الإدارة (MVP) | **Django Admin مخصّصة** (لا لوحة Flutter في الـMVP) |
| استضافة الفيديو | **مؤجّلة** — تُعزَل خلف طبقة خدمة (انظر القسم 7) |
| الذكاء الاصطناعي | **خارج الـMVP** — مرحلة لاحقة |
| إصدار الـAPI | كل المسارات تحت `/api/v1/` |
| لغة الواجهة | **عربي + إنجليزي**، مع دعم **RTL** كامل |

---

## 4) المستخدمون والأدوار (Roles)

ثلاثة أدوار على حقل `role` في `User`:

**1. الطالب (`student`)** — المستخدم العادي:
إنشاء حساب، اختبار تحديد المستوى، متابعة المسار، مشاهدة الدروس، حل التمارين، تتبّع
التقدّم، الحصول على شهادات.

**2. الأستاذ / منشئ المحتوى (`teacher`)** — **غير ظاهر للعامة**:
لا يوجد زر «تسجيل دخول كأستاذ». يُنشئ حسابه **المدير فقط**. صلاحياته: إنشاء وحدات
ودروس، رفع فيديوهات، إضافة مفردات، إنشاء تمارين عبر القوالب الجاهزة.

**3. المدير (`admin`)** — صلاحيات كاملة:
إدارة المستخدمين والأساتذة والمحتوى والمستويات، الإحصائيات، إعدادات المنصة.

نفّذ صلاحيات على مستوى الـAPI: `IsStudent`, `IsTeacher`, `IsAdmin` (DRF permissions).

---

## 5) رحلات المستخدم

**الطالب:**
1. فتح التطبيق → شعار + اختيار لغة الواجهة (عربي/إنجليزي).
2. تسجيل (بريد / Google / Apple) → إدخال: الاسم، اللغة الأم، الهدف من التعلّم
   (`study` / `work` / `travel` / `communication`).
3. **اختبار تحديد المستوى** → النتيجة تحدّد المستوى (مثل `A2 - Survival`).
4. متابعة المسار: مستوى → وحدات → دروس → مكوّنات.
5. حل التمارين، تتبّع التقدّم (نسبة، دروس منتهية، نقاط، وقت).
6. عند إكمال مستوى → **شهادة PDF**.

**الأستاذ (عبر Django Admin):** إنشاء مستوى/وحدة/درس، إضافة مكوّنات للدرس بالترتيب،
رفع فيديو، إدخال مفردات، إنشاء تمارين باختيار القالب وملء محتواه.

**المدير (عبر Django Admin):** كل ما سبق + إدارة المستخدمين والأساتذة + لوحة إحصائيات
(عدد المستخدمين، الدروس، الوحدات، النشاط اليومي).

---

## 6) هيكل المحتوى والمكوّنات المرنة

```
Level (A1..C1)
  └─ Unit            مثال: "At the Airport"
       └─ Lesson     مثال: "Checking in"
            └─ LessonComponent[]   (مرتّبة، مرنة)
                 ├─ video
                 ├─ vocabulary
                 ├─ text          (شرح)
                 └─ exercise
```

**القاعدة الذهبية:** الدرس **لا قالب ثابت له**. هو قائمة `LessonComponent` مرتّبة،
يختار الأستاذ أنواعها وترتيبها حسب طبيعة الدرس.

---

## 7) عزل استضافة الفيديو (مهم)

قرار الاستضافة مؤجّل، لكن **يجب ألّا يؤثّر على الكود أو قاعدة البيانات**.

- جدول `Video` يخزّن `storage_key` فقط (مرجع مجرّد) — لا روابط نهائية.
- أنشئ طبقة خدمة `VideoService.get_playback_url(video)` تُرجع رابط البثّ.
- في الـMVP، نفّذها كـ**واجهة (interface) قابلة للاستبدال**، بتطبيق افتراضي بسيط
  (مثلاً يُرجع رابطاً محلياً/تخزينياً). لاحقاً نستبدلها بـHLS موقّع (سيرفر خاص أو
  Bunny/Cloudflare Stream) دون لمس بقية الكود.
- الفيديو نهائياً يُقدَّم كـHLS (`.m3u8` + `.ts`)، لا MP4 مباشر، مع حماية الروابط.

---

## 8) نموذج البيانات الكامل (المرجع الرسمي)

> هذا النموذج **مُلزِم**. أي تعديل عليه يحتاج موافقتي. `id` = UUID في كل الجداول.

### المستخدمون
- **User**: `id`, `email`(unique), `password`(hashed/nullable), `full_name`,
  `role`(`student`|`teacher`|`admin`), `native_language`, `learning_goal`
  (`study`|`work`|`travel`|`communication`), `app_language`(`ar`|`en`),
  `is_active`, `created_at`.
- **SocialAuth**: `id`, `user_id`(FK), `provider`(`google`|`apple`), `provider_uid`, `created_at`.

### المحتوى
- **Level**: `id`, `code`(`A1`..`C1`), `name`, `name_fr`, `order`, `is_free`.
- **Unit**: `id`, `level_id`(FK), `title`, `order`, `description`.
- **Lesson**: `id`, `unit_id`(FK), `title`, `order`, `description`.
- **LessonComponent**: `id`, `lesson_id`(FK), `type`(`video`|`vocabulary`|`text`|`exercise`),
  `order`, `config`(JSON).
- **Video**: `id`, `component_id`(FK), `title`, `duration`, `storage_key`,
  `status`(`processing`|`ready`).
- **VocabularyItem**: `id`, `component_id`(FK), `word`, `translation`, `audio_url`,
  `example_sentence`, `order`.
- **TextBlock**: `id`, `component_id`(FK), `content`(markdown/rich).

### محرّك التمارين
- **ExerciseTemplate**: `id`, `code`(انظر القسم 9), `name`, `content_schema`(JSON),
  `is_active`.
- **Exercise**: `id`, `component_id`(FK), `template_id`(FK), `content`(JSON مطابق للقالب),
  `points`, `order`.
- **ExerciseAttempt**: `id`, `user_id`(FK), `exercise_id`(FK), `answer`(JSON),
  `is_correct`, `score`, `attempted_at`.

### التقدّم والتقييم
- **PlacementResult**: `id`, `user_id`(FK), `assigned_level_id`(FK), `score`, `taken_at`.
- **Progress**: `id`, `user_id`(FK), `lesson_id`(FK),
  `status`(`not_started`|`in_progress`|`completed`), `score`, `time_spent`(seconds),
  `completed_at`.
- **Certificate**: `id`, `user_id`(FK), `level_id`(FK), `certificate_number`(unique),
  `pdf_url`, `issued_at`.

> **تقدّم المستوى يُحسب تجميعاً من `Progress` ولا يُخزَّن.**

---

## 9) قوالب التمارين الثمانية + مخطّطات الـJSON

كل قالب صفّ في `ExerciseTemplate`. حقل `Exercise.content` يطابق المخطّط:

```jsonc
// 1) multiple_choice
{ "question": "...", "options": ["...","..."], "correct_index": 1 }

// 2) true_false
{ "statement": "...", "answer": false }

// 3) fill_blank
{ "sentence": "I ___ a teacher.", "answer": "am" }

// 4) matching
{ "pairs": [{"left":"Apple","right":"تفاحة"}, {"left":"Book","right":"كتاب"}] }

// 5) reorder
{ "words": ["am","I","a","student"], "correct_order": ["I","am","a","student"] }

// 6) listening
{ "audio_url":"...", "question":"...", "options":["...","..."], "correct_index":0 }

// 7) pronunciation
{ "target_text":"Boarding pass", "reference_audio_url":"..." }
// (في الـMVP: التسجيل والمقارنة الصوتية مبسّطة؛ التحليل المتقدّم مرحلة لاحقة)

// 8) final_test
{ "exercise_ids": ["uuid", "uuid", ...] }  // تجميعة تمارين لنهاية الوحدة
```

**التصحيح (correction):** أنشئ `ExerciseCorrector` لكل `code`، يأخذ `content` + `answer`
ويُرجع `(is_correct, score)`. إضافة قالب جديد لاحقاً = مُصحّح جديد + مكوّن عرض في Flutter،
**دون تعديل قاعدة البيانات**.

---

## 10) تصميم الـAPI (REST تحت `/api/v1/`)

أمثلة مسارات متوقّعة (وسّعها حسب الحاجة):

```
# Auth
POST   /api/v1/auth/register
POST   /api/v1/auth/login            -> JWT (access + refresh)
POST   /api/v1/auth/refresh
POST   /api/v1/auth/social/google
POST   /api/v1/auth/social/apple
GET    /api/v1/auth/me

# Placement
GET    /api/v1/placement/test
POST   /api/v1/placement/submit      -> assigned_level

# Content (قراءة للطالب، كتابة عبر Admin)
GET    /api/v1/levels
GET    /api/v1/levels/{id}/units
GET    /api/v1/units/{id}/lessons
GET    /api/v1/lessons/{id}          -> الدرس + مكوّناته بالترتيب

# Exercises
POST   /api/v1/exercises/{id}/attempt -> {is_correct, score}

# Progress
GET    /api/v1/progress/overview     -> نسب لكل مستوى (محسوبة)
POST   /api/v1/progress/lesson/{id}  -> تحديث حالة الدرس

# Certificates
GET    /api/v1/certificates
GET    /api/v1/certificates/{id}/pdf

# Video
GET    /api/v1/videos/{id}/playback  -> رابط بثّ عبر VideoService
```

استخدم DRF Serializers، Pagination، Filtering، ومعالجة أخطاء موحّدة.

---

## 11) بنية المشروع

```
project-root/
├── backend/                      # Django
│   ├── config/                   # settings, urls, wsgi/asgi
│   ├── apps/
│   │   ├── users/                # User, SocialAuth, auth, permissions
│   │   ├── content/              # Level, Unit, Lesson, Component, Video, Vocab, Text
│   │   ├── exercises/            # Template, Exercise, Attempt, Correctors
│   │   ├── progress/             # Progress, PlacementResult, Certificate
│   │   └── common/               # services (VideoService), utils, base models
│   ├── requirements.txt
│   ├── .env.example
│   └── manage.py
├── mobile/                       # Flutter (student app + web)
│   ├── lib/
│   │   ├── core/                 # api client (Dio), theme, i18n, router
│   │   ├── features/             # auth, placement, content, exercises, progress, profile
│   │   └── main.dart
│   └── pubspec.yaml
├── docs/
│   └── data_model.md
└── README.md
```

**Flutter:** استخدم `dio` للـHTTP، `go_router` للتنقّل، إدارة حالة بـ`riverpod`،
دعم **i18n (ar/en) + RTL**، ومكوّن عرض منفصل لكل قالب تمرين.

---

## 12) خطة البناء بالمراحل (نفّذها بهذا الترتيب)

**المرحلة 0 — التهيئة**
إعداد repo، Django project، PostgreSQL، `.env.example`، Docker اختياري، README،
`requirements.txt`.

**المرحلة 1 — نموذج البيانات + الترحيلات**
كل الموديلات في القسم 8، `migrations`، تسجيلها في Django Admin، **fixtures/seed**
للمستويات الستة وعيّنة وحدة/درس/تمارين لكل قالب.

**المرحلة 2 — المصادقة والصلاحيات**
تسجيل/دخول بـJWT، `auth/me`، صلاحيات `IsStudent/IsTeacher/IsAdmin`. (Google/Apple
يمكن أن تأتي كـstubs ثم تُكمَّل.)

**المرحلة 3 — الـAPI للمحتوى**
مسارات المستويات/الوحدات/الدروس + جلب الدرس مع مكوّناته المرتّبة.

**المرحلة 4 — محرّك التمارين**
`ExerciseCorrector` لكل قالب + مسار `attempt` + تسجيل `ExerciseAttempt`.

**المرحلة 5 — التقدّم + تحديد المستوى + الشهادات**
حساب التقدّم، اختبار تحديد المستوى، توليد شهادة PDF.

**المرحلة 6 — لوحة الإدارة (Django Admin مخصّصة)**
تحرير سلس للمحتوى (inlines للمكوّنات داخل الدرس)، صفحة إحصائيات، إدارة الأساتذة.

**المرحلة 7 — تطبيق Flutter (الطالب)**
الواجهات، التنقّل، مكوّنات عرض القوالب، تتبّع التقدّم، RTL/i18n.

**خارج الـMVP (لاحقاً):** الدفع والاشتراكات، HLS موقّع على سيرفر خاص، الذكاء
الاصطناعي (محادثة/تحليل نطق/مدرّس شخصي).

---

## 13) معايير القبول للـMVP (Definition of Done)

- [ ] طالب يسجّل، يجري اختبار تحديد المستوى، ويُسنَد له مستوى.
- [ ] يتصفّح مستوى → وحدة → درس ويرى مكوّناته بالترتيب.
- [ ] يحل تمارين من **القوالب الثمانية** ويُصحَّح فوراً.
- [ ] تقدّمه يُحسب ويُعرض (نسبة، دروس منتهية، نقاط، وقت).
- [ ] عند إكمال مستوى يحصل على شهادة PDF.
- [ ] أستاذ ينشئ محتوى كاملاً عبر Django Admin دون لمس الكود.
- [ ] مدير يدير المستخدمين ويرى إحصائيات.
- [ ] الفيديو يُقدَّم عبر `VideoService` (قابل لتبديل الاستضافة لاحقاً).

---

## 14) كيف يجب أن تعمل (تعليمات تشغيل للـAI)

1. اقرأ هذا الملف كاملاً، ثم **أعد صياغة الخطة وانتظر تأكيدي**.
2. ابنِ مرحلةً مرحلة؛ لا تقفز للأمام.
3. استخدم **migrations** دائماً، لا SQL يدوي.
4. اكتب **اختبارات** للمسارات الحرجة (auth, attempt, progress).
5. اكتب **seed data** لتجربة فورية.
6. **لا تضع أسراراً في الكود** — استخدم `.env` و`.env.example`.
7. اعمل **commits منطقية** برسائل واضحة.
8. إن واجهت قراراً غير محسوم هنا → **اسألني، لا تفترض**.
9. بعد كل مرحلة، أعطني ملخصاً قصيراً لما أُنجز وكيف أختبره.

---

### ملاحظات قابلة للتغيير من المالك
- `id`: حالياً **UUID** — لتحويله إلى BigInt تسلسلي، أخبرني.
- لوحة الإدارة: حالياً **Django Admin** — لبناء لوحة Flutter-Web مخصّصة في الـMVP، أخبرني.
- الملف المرجعي لنموذج البيانات: `docs/data_model.md`.
