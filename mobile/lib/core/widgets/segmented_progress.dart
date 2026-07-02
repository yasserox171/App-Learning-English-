import 'package:flutter/material.dart';

import '../theme/app_theme.dart';

/// A segmented progress bar (one rounded segment per item, completed ones
/// filled green) — the ABA-style "Unités terminées 24/24" bar.
class SegmentedProgress extends StatelessWidget {
  const SegmentedProgress({
    super.key,
    required this.completed,
    required this.total,
    this.height = 10,
    this.color,
  });

  final int completed;
  final int total;
  final double height;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final fill = color ?? AppTheme.success;
    if (total <= 0) {
      return Container(
        height: height,
        decoration: BoxDecoration(
          color: scheme.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(height / 2),
        ),
      );
    }
    return Row(
      children: [
        for (var i = 0; i < total; i++)
          Expanded(
            child: Container(
              height: height,
              margin: EdgeInsetsDirectional.only(
                  end: i == total - 1 ? 0 : 3),
              decoration: BoxDecoration(
                color: i < completed ? fill : scheme.surfaceContainerHighest,
                borderRadius: BorderRadius.circular(3),
              ),
            ),
          ),
      ],
    );
  }
}
