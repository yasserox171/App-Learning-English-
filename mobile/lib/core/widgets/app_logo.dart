import 'package:flutter/material.dart';

import '../theme/app_theme.dart';

/// The «English Master» brand mark: a graduation cap over an open book inside
/// a rounded gradient tile. Used on splash / login.
class AppLogo extends StatelessWidget {
  const AppLogo({super.key, this.size = 96});

  final double size;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(size * 0.28),
        gradient: const LinearGradient(
          colors: [AppTheme.primary, Color(0xFF3DDCFF)],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        boxShadow: [
          BoxShadow(
            color: AppTheme.primary.withOpacity(0.4),
            blurRadius: 24,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: Stack(
        alignment: Alignment.center,
        children: [
          Icon(Icons.menu_book_rounded,
              size: size * 0.42, color: AppTheme.accent),
          Padding(
            padding: EdgeInsets.only(bottom: size * 0.22),
            child: Icon(Icons.school_rounded,
                size: size * 0.5, color: Colors.white),
          ),
        ],
      ),
    );
  }
}
