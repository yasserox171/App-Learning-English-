# English Learning LMS — منصة تعلّم الإنجليزية

نظام إدارة تعلّم (LMS) متخصّص في تعليم اللغة الإنجليزية للناطقين بالعربية،
مبني على مسار **CEFR** (`A1 → A2 → B1 → B2 → C1`) بمحتوى مرن وقوالب تمارين جاهزة.

- **Backend:** Django 5 + Django REST Framework + PostgreSQL (مفاتيح UUID، JWT).
- **Frontend:** Flutter (Android + iOS + Web) — يأتي في مرحلة لاحقة.
- **API:** كل المسارات تحت `/api/v1/`.

> المرجع الكامل للقرارات وخطة المراحل: [`docs/master_prompt.md`](docs/master_prompt.md)
> ونموذج البيانات: [`docs/data_model.md`](docs/data_model.md).

---

## بنية المشروع

```
project-root/
├── backend/            # Django + DRF
│   ├── config/         # settings, urls, wsgi/asgi
│   ├── apps/
│   │   ├── common/     # base models (UUID), VideoService, permissions, error handler
│   │   ├── users/      # User, SocialAuth, auth (Phase 2)
│   │   ├── content/    # Level, Unit, Lesson, Component, Video, Vocab, Text
│   │   ├── exercises/  # Template, Exercise, Attempt, Correctors
│   │   └── progress/   # Progress, PlacementResult, Certificate
│   ├── requirements.txt
│   ├── .env.example
│   └── manage.py
├── mobile/             # Flutter (Phase 7)
├── docs/               # data_model.md, master_prompt.md
└── README.md
```

---

## التشغيل المحلي (Backend) — Windows + WSL (Ubuntu)

### 1) المتطلّبات
- Python 3.11+
- PostgreSQL 14+

### 2) إنشاء قاعدة البيانات
```bash
sudo -u postgres psql -c "CREATE USER lms WITH PASSWORD 'lms';"
sudo -u postgres psql -c "CREATE DATABASE lms OWNER lms;"
```

### 3) إعداد البيئة الافتراضية والاعتماديات
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 4) متغيّرات البيئة
```bash
cp .env.example .env
# عدّل DJANGO_SECRET_KEY و DATABASE_URL حسب جهازك
```

### 5) الترحيلات والتشغيل
```bash
python manage.py migrate          # يصبح فعّالاً بعد المرحلة 1
python manage.py runserver
```

- توثيق الـAPI (Swagger): `http://localhost:8000/api/v1/docs/`
- لوحة الإدارة: `http://localhost:8000/admin/`

---

## التشغيل على الهاتف عبر Termux (بدون حاسوب)

لتجربة التطبيق بهاتف واحد فقط: شغّل الـbackend داخل **Termux** على نفس الهاتف،
ويتصل به التطبيق عبر `http://127.0.0.1:8000`. يستخدم **SQLite** (لا حاجة لـPostgreSQL).

1. ثبّت **Termux** من **F-Droid** (نسخة Google Play قديمة ومعطّلة).
2. داخل Termux:
   ```bash
   pkg update -y && pkg install -y python git
   git clone https://github.com/yasserox171/App-Learning-English-.git
   cd App-Learning-English-/backend
   bash termux_setup.sh
   ```
3. بعد انتهاء الإعداد، شغّل الخادم:
   ```bash
   . .venv/bin/activate
   python manage.py runserver 127.0.0.1:8000
   ```
4. اترك Termux يعمل، وافتح تطبيق **lms-student-app.apk** (المبني برابط `127.0.0.1`).
   - تسجيل دخول تجريبي: `student@lms.test` / `student12345`
   - أو أنشئ حساباً جديداً (سيعمل الآن لأن الخادم متاح محلياً).

> ملاحظة: الـAPK المنشور في صفحة Releases مبنيّ على هذا الرابط (`127.0.0.1:8000`)،
> فهو متوافق مباشرة مع تشغيل Termux. لاستضافة عامة لاحقاً، أعد البناء برابطك العام.

---

## التشغيل عبر Docker (اختياري)

```bash
cd backend
docker compose up --build
```
يشغّل PostgreSQL + خادم Django على المنفذ `8000`.

---

## خطة المراحل

| المرحلة | الوصف | الحالة |
|---|---|---|
| 0 | التهيئة (هيكل المشروع، Django، PostgreSQL، env، Docker، README) | ✅ منجزة |
| 1 | نموذج البيانات + الترحيلات + Admin + seed | ✅ منجزة |
| 2 | المصادقة والصلاحيات (JWT، الأدوار) | ✅ منجزة |
| 3 | API المحتوى (مستويات/وحدات/دروس/مكوّنات) | ✅ منجزة |
| 4 | محرّك التمارين (المصحّحات + attempt) | ✅ منجزة |
| 5 | التقدّم + تحديد المستوى + الشهادات | ✅ منجزة |
| 6 | لوحة Django Admin المخصّصة + الإحصائيات | ✅ منجزة |
| 7 | تطبيق Flutter للطالب | ✅ منجزة |

> **المستويات:** 6 (A1–C2) بقرار المالك (خطة المراحل §12).
> راجع [`mobile/README.md`](mobile/README.md) لتشغيل تطبيق Flutter.

---

## ملاحظات معمارية أساسية
1. **التمارين بـJSON موجّه بقالب** → مرونة بلا تعديل قاعدة البيانات.
2. **مكوّنات الدرس مرنة ومرتّبة** → الأستاذ يبني الدرس كما يشاء.
3. **عزل استضافة الفيديو** عبر `storage_key` + `VideoService` → القرار مؤجّل بأمان.
4. **التقدّم محسوب لا مخزّن** → لا تضارب في الأرقام.
5. **الأستاذ يُنشأ إدارياً فقط** → لا واجهة تسجيل عامة له.
