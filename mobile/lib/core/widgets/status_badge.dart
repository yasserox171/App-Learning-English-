import 'package:flutter/material.dart';

import '../theme/app_theme.dart';

/// Trailing status icon for a level / unit / lesson tile:
/// 🔒 locked · ✓ completed · ▶ available/in-progress.
class StatusBadge extends StatelessWidget {
  const StatusBadge({
    super.key,
    required this.locked,
    required this.completed,
    this.size = 34,
  });

  final bool locked;
  final bool completed;
  final double size;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    late final Color bg;
    late final IconData icon;
    late final Color fg;

    if (locked) {
      bg = scheme.surfaceContainerHighest;
      fg = scheme.onSurfaceVariant;
      icon = Icons.lock_rounded;
    } else if (completed) {
      bg = AppTheme.success.withOpacity(0.18);
      fg = AppTheme.success;
      icon = Icons.check_rounded;
    } else {
      bg = AppTheme.primary.withOpacity(0.18);
      fg = AppTheme.primary;
      icon = Icons.play_arrow_rounded;
    }

    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(color: bg, shape: BoxShape.circle),
      child: Icon(icon, color: fg, size: size * 0.55),
    );
  }
}
