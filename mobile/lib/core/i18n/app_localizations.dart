import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../settings/settings_storage.dart';

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
      'home': 'Home',
      'back': 'Back',
      'start_lesson': 'Start lesson',
      'finish_lesson': 'Finish lesson',
      'welcome': 'Welcome back',
      'keep_learning': 'Keep learning!',
      'start_practice': 'Start practice',
      'session_expired': 'Session expired. Please sign in again.',
      'connection_error': 'Cannot reach the server. Check your connection.',
      'no_practice': 'No practice available for this lesson.',
      'play': 'Play',
      'tf_true': 'True',
      'tf_false': 'False',
      'tap_word': 'Tap a word',
      'retry': 'Retry',
      'welcome_user': 'Welcome',
      'notifications': 'Notifications',
      'current_level': 'Current level',
      'continue_learning': 'Continue learning',
      'continue_lesson': 'Continue lesson',
      'daily_streak': 'Daily streak',
      'days': 'days',
      'xp': 'XP',
      'learn': 'Learn',
      'settings': 'Settings',
      'dark_mode': 'Dark mode',
      'sound': 'Sound',
      'about': 'About the app',
      'share': 'Share',
      'download_pdf': 'Download (PDF)',
      'overall_progress': 'Overall progress',
      'completed_lessons': 'Completed lessons',
      'remaining_lessons': 'Remaining lessons',
      'well_done': 'Well done!',
      'your_result': 'You completed the lesson successfully',
      'retry_lesson': 'Retry',
      'what_is_this': 'What is this image?',
      'remember_me': 'Remember me',
      'forgot_password': 'Forgot password?',
      'no_account': "Don't have an account?",
      'create_account': 'Create account',
      'have_account': 'Already have an account?',
      'or_text': 'or',
      'sign_in_google': 'Continue with Google',
      'sign_in_apple': 'Continue with Apple',
      'skip': 'Skip for now',
      'start_now': 'Start now',
      'locked_msg': 'Complete the previous one first.',
      'definition': 'Definition',
      'example': 'Example',
      'choose_level': 'Choose your level',
      'placement_intro': 'A quick test to help us find the level that suits you.',
      'no_certificates': 'No certificates yet. Complete a level to earn one.',
      'language': 'Language',
      'save': 'Save',
      'loading': 'Loading…',
      'new_word': 'New word',
      'points': 'Points',
      'total_points': 'Total points',
      'study_plan': 'Study plan',
      'unit_n': 'Unit',
      'level_certificate': 'Level certificate',
      'add_to_linkedin': 'Add to LinkedIn',
      'earn_certificate_hint':
          'Complete all lessons to earn your certificate.',
      'downloading': 'Downloading…',
      'saved_to_downloads': 'Saved to the Downloads folder',
      'saved_to_app_files': 'Saved inside the app files',
      'share_certificate_text':
          'I earned my {level} English certificate at Focus Languages!',
      'video_lesson': 'Video lesson',
      'vocabulary_step': 'Vocabulary',
      'exercises_step': 'Exercises',
      'evaluation': 'Evaluation',
      'reading_step': 'Reading',
      'min_short': 'min',
      'listening': 'Listening',
      'watch_video':
          'Watch a short real-life scene to train your ear.',
      'hint': 'Hint',
      'half_points': 'half points',
      'correct_is': 'Correct answer',
      'summary': 'Summary',
      'summary_words': 'Words learned',
      'summary_exercises': 'Exercises',
      'summary_time': 'Time',
      'unit_test': 'Unit test',
      'expected_time': 'Expected time',
      'pass_condition': 'Pass condition',
      'retake_on_fail': 'You can retake the test if you fail.',
      'review_lessons': 'Review the lessons',
      'of': 'of',
      'unit_passed': 'Well done! You passed the unit!',
      'needs_practice': 'You need more practice',
      'proud_of_you': "We're proud of your progress — keep going! 💪",
      'rate_unit': 'How was this unit?',
      'next_unit': 'Next unit',
      'retake_test': 'Retake the test',
      'finish_lessons_first': 'Finish all unit lessons to unlock the test.',
      'you_will_learn': 'In this lesson you will learn:',
      'write_what_you_hear': 'Write what you hear:',
      'pronounce_word': 'Pronounce this:',
      'listen_model': 'Listen to the model',
      'recording': 'Listening… speak now',
      'attempt': 'Attempt',
      'excellent': 'Excellent!',
      'very_good': 'Very good!',
      'almost': 'Almost there!',
      'mic_unavailable':
          'Speech recognition is unavailable on this device.',
      'pron_tip_generic':
          'Listen to the model again and repeat slowly, syllable by syllable.',
      'skip_step': 'Skip',
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
      'home': 'الرئيسية',
      'back': 'السابق',
      'start_lesson': 'ابدأ الدرس',
      'finish_lesson': 'إنهاء الدرس',
      'welcome': 'مرحباً بعودتك',
      'keep_learning': 'واصل التعلّم!',
      'start_practice': 'ابدأ التدريب',
      'session_expired': 'انتهت الجلسة. الرجاء تسجيل الدخول من جديد.',
      'connection_error': 'تعذّر الاتصال بالخادم. تحقّق من الاتصال.',
      'no_practice': 'لا يوجد تدريب متاح لهذا الدرس.',
      'play': 'تشغيل',
      'tf_true': 'صحيح',
      'tf_false': 'خطأ',
      'tap_word': 'اختر كلمة',
      'retry': 'إعادة المحاولة',
      'welcome_user': 'مرحباً',
      'notifications': 'الإشعارات',
      'current_level': 'مستواك الحالي',
      'continue_learning': 'تابع تعلّمك',
      'continue_lesson': 'متابعة الدرس',
      'daily_streak': 'السلسلة اليومية',
      'days': 'أيام',
      'xp': 'نقطة',
      'learn': 'التعلّم',
      'settings': 'الإعدادات',
      'dark_mode': 'الوضع الليلي',
      'sound': 'الصوت',
      'about': 'حول التطبيق',
      'share': 'مشاركة',
      'download_pdf': 'تحميل الشهادة (PDF)',
      'overall_progress': 'التقدّم العام',
      'completed_lessons': 'الدروس المكتملة',
      'remaining_lessons': 'الدروس المتبقية',
      'well_done': 'أحسنت!',
      'your_result': 'لقد أكملت الدرس بنجاح',
      'retry_lesson': 'إعادة المحاولة',
      'what_is_this': 'ما هذه الصورة؟',
      'remember_me': 'تذكّرني',
      'forgot_password': 'نسيت كلمة المرور؟',
      'no_account': 'ليس لديك حساب؟',
      'create_account': 'إنشاء حساب',
      'have_account': 'لديك حساب بالفعل؟',
      'or_text': 'أو',
      'sign_in_google': 'المتابعة عبر Google',
      'sign_in_apple': 'المتابعة عبر Apple',
      'skip': 'سأجرّب لاحقاً',
      'start_now': 'ابدأ الآن',
      'locked_msg': 'أكمل السابق أولاً.',
      'definition': 'تعريف',
      'example': 'مثال',
      'choose_level': 'اختيار تحديد المستوى',
      'placement_intro': 'اختبار قصير يساعدنا على تحديد مستواك المناسب.',
      'no_certificates': 'لا توجد شهادات بعد. أكمل مستوى للحصول على شهادة.',
      'language': 'اللغة',
      'save': 'حفظ',
      'loading': 'جارٍ التحميل…',
      'new_word': 'مفردة جديدة',
      'points': 'النقاط',
      'total_points': 'إجمالي النقاط',
      'study_plan': 'خطة الدراسة',
      'unit_n': 'الوحدة',
      'level_certificate': 'شهادة المستوى',
      'add_to_linkedin': 'إضافة إلى LinkedIn',
      'earn_certificate_hint': 'أكمل كل الدروس للحصول على شهادتك.',
      'downloading': 'جارٍ التحميل…',
      'saved_to_downloads': 'تم الحفظ في مجلد التنزيلات',
      'saved_to_app_files': 'تم الحفظ داخل ملفات التطبيق',
      'share_certificate_text':
          'حصلت على شهادة مستوى {level} في اللغة الإنجليزية من Focus Languages!',
      'video_lesson': 'درس فيديو',
      'vocabulary_step': 'المفردات',
      'exercises_step': 'التمارين',
      'evaluation': 'التقييم',
      'reading_step': 'القراءة',
      'min_short': 'د',
      'listening': 'استماع',
      'watch_video': 'شاهد مشهداً قصيراً من الحياة الواقعية لتدريب أذنك.',
      'hint': 'مساعدة',
      'half_points': 'نصف النقاط',
      'correct_is': 'الإجابة الصحيحة',
      'summary': 'ملخص',
      'summary_words': 'تعلمت من الكلمات',
      'summary_exercises': 'التمارين',
      'summary_time': 'الوقت',
      'unit_test': 'اختبار الوحدة',
      'expected_time': 'الوقت المتوقع',
      'pass_condition': 'شرط النجاح',
      'retake_on_fail': 'يمكنك إعادة الاختبار في حال عدم النجاح.',
      'review_lessons': 'مراجعة الدروس',
      'of': 'من',
      'unit_passed': 'أحسنت! اجتزت الوحدة!',
      'needs_practice': 'تحتاج للمزيد من التدريب',
      'proud_of_you': 'نحن فخورون بتقدمك — واصل هكذا! 💪',
      'rate_unit': 'كيف وجدت الوحدة؟',
      'next_unit': 'انتقل للوحدة التالية',
      'retake_test': 'أعد الاختبار',
      'finish_lessons_first': 'أكمل كل دروس الوحدة لفتح الاختبار.',
      'you_will_learn': 'ستتعلم في هذا الدرس:',
      'write_what_you_hear': 'اكتب ما تسمعه:',
      'pronounce_word': 'انطق هذه:',
      'listen_model': 'استمع للنموذج',
      'recording': 'جارٍ الاستماع… تحدّث الآن',
      'attempt': 'المحاولة',
      'excellent': 'ممتاز!',
      'very_good': 'جيد جداً!',
      'almost': 'تقريباً!',
      'mic_unavailable': 'التعرف على الصوت غير متاح على هذا الجهاز.',
      'pron_tip_generic': 'استمع للنموذج مجدداً وكرر ببطء، مقطعاً مقطعاً.',
      'skip_step': 'تخطَّ',
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

/// Holds the chosen UI locale; defaults to Arabic (RTL) and persists the choice.
class LocaleNotifier extends StateNotifier<Locale> {
  LocaleNotifier(this._storage) : super(const Locale('ar')) {
    _load();
  }

  final SettingsStorage _storage;

  Future<void> _load() async {
    final code = await _storage.locale;
    if (code == 'en' || code == 'ar') state = Locale(code!);
  }

  void setLocale(Locale locale) {
    state = locale;
    _storage.setLocale(locale.languageCode);
  }

  void toggle() => setLocale(
      state.languageCode == 'ar' ? const Locale('en') : const Locale('ar'));
}

final localeProvider = StateNotifierProvider<LocaleNotifier, Locale>(
  (ref) => LocaleNotifier(ref.read(settingsStorageProvider)),
);
