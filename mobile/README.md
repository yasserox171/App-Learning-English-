# LMS Mobile (Flutter) — Student App

تطبيق الطالب لمنصة تعلّم الإنجليزية، من قاعدة كود واحدة لـ**Android + iOS + Web**.

## التقنيات
- **State:** `flutter_riverpod`
- **HTTP:** `dio` (مع interceptor لإرفاق JWT وتجديده عند 401)
- **Routing:** `go_router` (مع حارس مصادقة)
- **i18n:** عربي/إنجليزي مع دعم **RTL** كامل
- **Storage:** `flutter_secure_storage` لحفظ التوكنات

## البنية
```
lib/
├── core/
│   ├── api/        # Dio client + token storage
│   ├── i18n/       # AppLocalizations (ar/en) + locale provider
│   ├── router/     # go_router + auth guard
│   ├── theme/      # Material 3 theme
│   └── config.dart # API base URL (--dart-define)
├── features/
│   ├── auth/       # login, register, controller, repository
│   ├── placement/  # placement test
│   ├── content/    # levels → units → lessons → lesson detail
│   ├── exercises/  # ExerciseView dispatcher + 8 template widgets
│   ├── progress/   # progress overview
│   └── profile/    # profile + language toggle + logout
└── main.dart
```

## التشغيل
```bash
cd mobile
flutter pub get

# الويب (يتصل بالـbackend المحلي)
flutter run -d chrome --dart-define=API_BASE_URL=http://localhost:8000/api/v1

# Android / iOS
flutter run --dart-define=API_BASE_URL=http://10.0.2.2:8000/api/v1
```

> **مكوّنات عرض التمارين الثمانية** موجودة في `features/exercises/exercise_view.dart`.
> إضافة قالب جديد = حالة جديدة هنا + مُصحّح جديد في الـbackend، دون تعديل قاعدة البيانات.

> **الفيديو:** الواجهة تعرض البطاقة وتستقبل `playback_url` من الـbackend (عبر `VideoService`).
> مشغّل HLS الفعلي يُضاف لاحقاً دون تغيير العقد.
