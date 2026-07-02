import 'package:flutter/material.dart';

import '../theme/app_theme.dart';

/// A row of small step indicators (one per lesson step): filled turquoise
/// check circles when done, faint outlines otherwise (ABA unit-card dots).
class StepDots extends StatelessWidget {
  const StepDots({
    super.key,
    required this.count,
    required this.completedCount,
    this.size = 20,
  });

  final int count;
  final int completedCount;
  final double size;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Wrap(
      spacing: 6,
      runSpacing: 6,
      children: [
        for (var i = 0; i < count; i++)
          Container(
            width: size,
            height: size,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: i < completedCount
                  ? AppTheme.primary
                  : scheme.surfaceContainerHighest,
            ),
            child: i < completedCount
                ? Icon(Icons.check_rounded,
                    size: size * 0.65, color: Colors.white)
                : null,
          ),
      ],
    );
  }
}
