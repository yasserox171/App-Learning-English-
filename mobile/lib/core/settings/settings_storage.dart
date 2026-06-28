import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

/// Persists lightweight UI preferences (theme, locale, onboarding flag).
class SettingsStorage {
  SettingsStorage(this._storage);

  final FlutterSecureStorage _storage;

  static const _themeKey = 'theme_mode';
  static const _localeKey = 'locale';
  static const _onboardedKey = 'onboarded';
  static const _soundKey = 'sound';

  Future<String?> get themeMode => _storage.read(key: _themeKey);
  Future<void> setThemeMode(String value) =>
      _storage.write(key: _themeKey, value: value);

  Future<bool> get soundEnabled async =>
      (await _storage.read(key: _soundKey)) != '0';
  Future<void> setSoundEnabled(bool value) =>
      _storage.write(key: _soundKey, value: value ? '1' : '0');

  Future<String?> get locale => _storage.read(key: _localeKey);
  Future<void> setLocale(String value) =>
      _storage.write(key: _localeKey, value: value);

  Future<bool> get onboarded async =>
      (await _storage.read(key: _onboardedKey)) == '1';
  Future<void> setOnboarded() => _storage.write(key: _onboardedKey, value: '1');
}

final settingsStorageProvider = Provider<SettingsStorage>(
  (ref) => SettingsStorage(const FlutterSecureStorage()),
);
