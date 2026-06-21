import 'package:flutter/material.dart';

class AppTheme {
  static ThemeData light() {
    final scheme = ColorScheme.fromSeed(seedColor: const Color(0xFF1565C0));
    return ThemeData(
      colorScheme: scheme,
      useMaterial3: true,
      appBarTheme: AppBarTheme(
        backgroundColor: scheme.primary,
        foregroundColor: scheme.onPrimary,
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          minimumSize: const Size.fromHeight(48),
        ),
      ),
    );
  }
}
