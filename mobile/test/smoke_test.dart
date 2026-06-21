import 'package:flutter_test/flutter_test.dart';
import 'package:lms_mobile/core/i18n/app_localizations.dart';
import 'package:flutter/widgets.dart';

void main() {
  test('localization returns translated strings', () {
    final ar = AppLocalizations(const Locale('ar'));
    final en = AppLocalizations(const Locale('en'));
    expect(ar.t('login'), 'تسجيل الدخول');
    expect(en.t('login'), 'Login');
    // Unknown key falls back to the key itself.
    expect(en.t('missing_key'), 'missing_key');
  });
}
