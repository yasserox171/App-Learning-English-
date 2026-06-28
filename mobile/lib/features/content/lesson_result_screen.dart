import 'package:flutter/material.dart';

import '../../core/i18n/app_localizations.dart';
import '../../core/theme/app_theme.dart';

/// Celebration screen shown after finishing a lesson (design screen 19):
/// trophy, score percentage, 0–3 stars, and retry / continue actions.
class LessonResultView extends StatelessWidget {
  const LessonResultView({
    super.key,
    required this.percent,
    required this.onRetry,
    required this.onContinue,
  });

  final int percent;
  final VoidCallback onRetry;
  final VoidCallback onContinue;

  int get _stars => percent >= 90
      ? 3
      : percent >= 70
          ? 2
          : percent >= 50
              ? 1
              : 0;

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    return Center(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            TweenAnimationBuilder<double>(
              tween: Tween(begin: 0.6, end: 1),
              duration: const Duration(milliseconds: 500),
              curve: Curves.elasticOut,
              builder: (_, scale, child) =>
                  Transform.scale(scale: scale, child: child),
              child: Container(
                padding: const EdgeInsets.all(28),
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: AppTheme.accent.withOpacity(0.15),
                ),
                child: const Icon(Icons.emoji_events_rounded,
                    size: 96, color: AppTheme.accent),
              ),
            ),
            const SizedBox(height: 20),
            Text(t.t('well_done'),
                style: Theme.of(context)
                    .textTheme
                    .headlineSmall
                    ?.copyWith(fontWeight: FontWeight.bold)),
            const SizedBox(height: 6),
            Text(t.t('your_result'),
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodyMedium),
            const SizedBox(height: 16),
            Text('$percent%',
                style: Theme.of(context).textTheme.displaySmall?.copyWith(
                    fontWeight: FontWeight.bold, color: AppTheme.primary)),
            const SizedBox(height: 8),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                for (int i = 0; i < 3; i++)
                  Icon(
                    i < _stars ? Icons.star_rounded : Icons.star_border_rounded,
                    color: AppTheme.accent,
                    size: 44,
                  ),
              ],
            ),
            const SizedBox(height: 28),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton(
                    onPressed: onRetry,
                    child: Text(t.t('retry_lesson')),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: FilledButton(
                    onPressed: onContinue,
                    child: Text(t.t('continue_')),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
