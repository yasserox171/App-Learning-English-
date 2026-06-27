import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Minimal manual i18n (ar/en) with full RTL support, no codegen needed.
class AppLocalizations {
  AppLocalizations(this.locale);

  final Locale locale;

  static AppLocalizations of(BuildContext context) =>
      Localizations.of<AppLocalizations>(context, AppLocalizations)!;

  static const supportedLocales = [Locale('ar'), Locale('en')];

  static const LocalizationsDelegate<AppLocalizations> delegate =
      _AppLocalizationsDelegate();

  static const Map<String, Map<String, String>> _values = {
    'en': {
      'app_title': 'English Learning',
      'login': 'Login',
      'register': 'Register',
      'email': 'Email',
      'password': 'Password',
      'full_name': 'Full name',
      'logout': 'Logout',
      'levels': 'Levels',
      'units': 'Units',
      'lessons': 'Lessons',
      'lesson': 'Lesson',
      'placement_test': 'Placement Test',
      'start_test': 'Start test',
      'submit': 'Submit',
      'next': 'Next',
      'progress': 'Progress',
      'profile': 'Profile',
      'certificates': 'Certificates',
      'correct': 'Correct!',
      'incorrect': 'Incorrect',
      'check': 'Check',
      'completed': 'Completed',
      'continue_': 'Continue',
      'choose_language': 'Choose language',
      'arabic': 'العربية',
      'english': 'English',
      'practice': 'Practice',
      'practice_words': 'Practice the words',
      'listen': 'Listen',
      'your_score': 'Your score',
      'try_again': 'Try again',
      'finish': 'Finish',
      'question': 'Question',
    },
    'ar': {
      'app_title': 'تعلّم الإنجليزية',
      'login': 'تسجيل الدخول',
      'register': 'إنشاء حساب',
      'email': 'البريد الإلكتروني',
      'password': 'كلمة المرور',
      'full_name': 'الاسم الكامل',
      'logout': 'تسجيل الخروج',
      'levels': 'المستويات',
      'units': 'الوحدات',
      'lessons': 'الدروس',
      'lesson': 'الدرس',
      'placement_test': 'اختبار تحديد المستوى',
      'start_test': 'ابدأ الاختبار',
      'submit': 'إرسال',
      'next': 'التالي',
      'progress': 'التقدّم',
      'profile': 'الملف الشخصي',
      'certificates': 'الشهادات',
      'correct': 'إجابة صحيحة!',
      'incorrect': 'إجابة خاطئة',
      'check': 'تحقّق',
      'completed': 'مكتمل',
      'continue_': 'متابعة',
      'choose_language': 'اختر اللغة',
      'arabic': 'العربية',
      'english': 'English',
      'practice': 'تدرّب',
      'practice_words': 'تدرّب على الكلمات',
      'listen': 'استمع',
      'your_score': 'نتيجتك',
      'try_again': 'حاول مجدداً',
      'finish': 'إنهاء',
      'question': 'سؤال',
    },
  };

  String t(String key) =>
      _values[locale.languageCode]?[key] ?? _values['en']![key] ?? key;
}

class _AppLocalizationsDelegate
    extends LocalizationsDelegate<AppLocalizations> {
  const _AppLocalizationsDelegate();

  @override
  bool isSupported(Locale locale) =>
      ['ar', 'en'].contains(locale.languageCode);

  @override
  Future<AppLocalizations> load(Locale locale) async =>
      AppLocalizations(locale);

  @override
  bool shouldReload(_AppLocalizationsDelegate old) => false;
}

/// Holds the chosen UI locale; defaults to Arabic (RTL).
class LocaleNotifier extends StateNotifier<Locale> {
  LocaleNotifier() : super(const Locale('ar'));

  void setLocale(Locale locale) => state = locale;
  void toggle() =>
      state = state.languageCode == 'ar' ? const Locale('en') : const Locale('ar');
}

final localeProvider =
    StateNotifierProvider<LocaleNotifier, Locale>((ref) => LocaleNotifier());
