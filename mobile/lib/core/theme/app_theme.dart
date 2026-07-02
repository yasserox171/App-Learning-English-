import 'package:flutter/material.dart';

/// ABA-inspired identity: bright white surfaces, turquoise primary, green
/// success, bold rounded titles, soft card shadows. Light mode is the default;
/// dark mode keeps the same hues on deep navy surfaces.
class AppTheme {
  static const primary = Color(0xFF00B2E3); // turquoise / cyan
  static const success = Color(0xFF2DCE89); // green (done / correct)
  static const accent = Color(0xFFFF9800); // warm orange (streak / XP)
  static const danger = Color(0xFFEF4444); // red (wrong)
  static const linkedIn = Color(0xFF0A66C2);

  // Dark surfaces (deep navy, cyan-friendly).
  static const _darkBg = Color(0xFF0F172A);
  static const _darkSurface = Color(0xFF1E293B);
  static const _darkSurfaceHi = Color(0xFF334155);

  static ThemeData _build(Brightness brightness) {
    final isDark = brightness == Brightness.dark;
    final scheme =
        ColorScheme.fromSeed(
          seedColor: primary,
          brightness: brightness,
          secondary: success,
        ).copyWith(
          primary: primary,
          secondary: success,
          surface: isDark ? _darkSurface : Colors.white,
          surfaceContainerHighest:
              isDark ? _darkSurfaceHi : const Color(0xFFEFF3F6),
        );

    final base = ThemeData(
      colorScheme: scheme,
      useMaterial3: true,
      scaffoldBackgroundColor: isDark ? _darkBg : const Color(0xFFF7F9FB),
    );

    final titles = base.textTheme.copyWith(
      headlineMedium: base.textTheme.headlineMedium
          ?.copyWith(fontWeight: FontWeight.w800),
      headlineSmall:
          base.textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w800),
      titleLarge:
          base.textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800),
      titleMedium:
          base.textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700),
    );

    return base.copyWith(
      textTheme: titles,
      appBarTheme: AppBarTheme(
        backgroundColor: Colors.transparent,
        foregroundColor: scheme.onSurface,
        elevation: 0,
        scrolledUnderElevation: 0,
        centerTitle: true,
        titleTextStyle: titles.titleLarge?.copyWith(color: scheme.onSurface),
      ),
      cardTheme: CardThemeData(
        elevation: 0,
        color: scheme.surface,
        surfaceTintColor: Colors.transparent,
        margin: const EdgeInsets.symmetric(vertical: 6),
        shadowColor: Colors.transparent,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
          side: isDark
              ? BorderSide(color: Colors.white.withOpacity(0.06))
              : BorderSide.none,
        ),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          minimumSize: const Size.fromHeight(52),
          textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(26),
          ),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          minimumSize: const Size.fromHeight(48),
          textStyle: const TextStyle(fontSize: 15, fontWeight: FontWeight.w600),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(26),
          ),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor:
            scheme.surfaceContainerHighest.withOpacity(isDark ? 0.6 : 0.55),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(14),
          borderSide: BorderSide.none,
        ),
        contentPadding:
            const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
      ),
      navigationBarTheme: NavigationBarThemeData(
        height: 66,
        backgroundColor: scheme.surface,
        indicatorColor: primary.withOpacity(0.15),
        labelBehavior: NavigationDestinationLabelBehavior.alwaysShow,
        iconTheme: WidgetStateProperty.resolveWith(
          (states) => IconThemeData(
            color: states.contains(WidgetState.selected)
                ? primary
                : scheme.onSurfaceVariant,
          ),
        ),
      ),
      chipTheme: base.chipTheme.copyWith(
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(20),
        ),
      ),
      snackBarTheme: SnackBarThemeData(
        behavior: SnackBarBehavior.floating,
        shape:
            RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      ),
      progressIndicatorTheme: const ProgressIndicatorThemeData(
        color: primary,
      ),
    );
  }

  /// Soft drop shadow used on light-mode cards (ABA look). Empty in dark mode.
  static List<BoxShadow> cardShadow(BuildContext context) =>
      Theme.of(context).brightness == Brightness.dark
          ? const []
          : [
              BoxShadow(
                color: Colors.black.withOpacity(0.06),
                blurRadius: 18,
                offset: const Offset(0, 6),
              ),
            ];

  static ThemeData light() => _build(Brightness.light);
  static ThemeData dark() => _build(Brightness.dark);
}
