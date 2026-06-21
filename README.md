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
| 1 | نموذج البيانات + الترحيلات + Admin + seed | ⏳ التالية |
| 2 | المصادقة والصلاحيات (JWT، الأدوار) | — |
| 3 | API المحتوى (مستويات/وحدات/دروس/مكوّنات) | — |
| 4 | محرّك التمارين (المصحّحات + attempt) | — |
| 5 | التقدّم + تحديد المستوى + الشهادات | — |
| 6 | لوحة Django Admin المخصّصة + الإحصائيات | — |
| 7 | تطبيق Flutter للطالب | — |

---

## ملاحظات معمارية أساسية
1. **التمارين بـJSON موجّه بقالب** → مرونة بلا تعديل قاعدة البيانات.
2. **مكوّنات الدرس مرنة ومرتّبة** → الأستاذ يبني الدرس كما يشاء.
3. **عزل استضافة الفيديو** عبر `storage_key` + `VideoService` → القرار مؤجّل بأمان.
4. **التقدّم محسوب لا مخزّن** → لا تضارب في الأرقام.
5. **الأستاذ يُنشأ إدارياً فقط** → لا واجهة تسجيل عامة له.
