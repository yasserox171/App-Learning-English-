import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../settings/settings_storage.dart';

/// Holds the active [ThemeMode]; defaults to light (ABA-style identity) and
/// persists the user's choice.
class ThemeModeNotifier extends StateNotifier<ThemeMode> {
  ThemeModeNotifier(this._storage) : super(ThemeMode.light) {
    _load();
  }

  final SettingsStorage _storage;

  Future<void> _load() async {
    switch (await _storage.themeMode) {
      case 'dark':
        state = ThemeMode.dark;
        break;
      case 'system':
        state = ThemeMode.system;
        break;
      default:
        state = ThemeMode.light;
    }
  }

  void set(ThemeMode mode) {
    state = mode;
    _storage.setThemeMode(mode.name);
  }

  void toggle() =>
      set(state == ThemeMode.dark ? ThemeMode.light : ThemeMode.dark);
}

final themeModeProvider =
    StateNotifierProvider<ThemeModeNotifier, ThemeMode>(
  (ref) => ThemeModeNotifier(ref.read(settingsStorageProvider)),
);
