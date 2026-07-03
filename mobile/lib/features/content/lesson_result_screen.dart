import 'dart:math';

import 'package:confetti/confetti.dart';
import 'package:flutter/material.dart';

import '../../core/i18n/app_localizations.dart';
import '../../core/theme/app_theme.dart';

/// Celebration screen shown after finishing a lesson (UX prompt feature 8):
/// confetti + trophy + stars + a summary of words learned, exercise score,
/// time spent and the daily streak.
class LessonResultView extends StatefulWidget {
  const LessonResultView({
    super.key,
    required this.percent,
    required this.onRetry,
    required this.onContinue,
    this.wordsLearned,
    this.exercisesCorrect,
    this.exercisesTotal,
    this.minutes,
    this.streak,
  });

  final int percent;
  final VoidCallback onRetry;
  final VoidCallback onContinue;
  final int? wordsLearned;
  final int? exercisesCorrect;
  final int? exercisesTotal;
  final int? minutes;
  final int? streak;

  @override
  State<LessonResultView> createState() => _LessonResultViewState();
}

class _LessonResultViewState extends State<LessonResultView> {
  late final ConfettiController _confetti =
      ConfettiController(duration: const Duration(seconds: 2));

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _confetti.play());
  }

  @override
  void dispose() {
    _confetti.dispose();
    super.dispose();
  }

  int get _stars => widget.percent >= 90
      ? 3
      : widget.percent >= 70
          ? 2
          : widget.percent >= 50
              ? 1
              : 0;

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    return Stack(
      alignment: Alignment.topCenter,
      children: [
        Center(
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
                    padding: const EdgeInsets.all(24),
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: AppTheme.accent.withOpacity(0.15),
                    ),
                    child: const Icon(Icons.emoji_events_rounded,
                        size: 88, color: AppTheme.accent),
                  ),
                ),
                const SizedBox(height: 16),
                Text(t.t('well_done'),
                    style: Theme.of(context)
                        .textTheme
                        .headlineSmall
                        ?.copyWith(fontWeight: FontWeight.bold)),
                const SizedBox(height: 12),
                Text('${widget.percent}%',
                    style: Theme.of(context).textTheme.displaySmall?.copyWith(
                        fontWeight: FontWeight.bold, color: AppTheme.primary)),
                Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    for (int i = 0; i < 3; i++)
                      Icon(
                        i < _stars
                            ? Icons.star_rounded
                            : Icons.star_border_rounded,
                        color: AppTheme.accent,
                        size: 40,
                      ),
                  ],
                ),
                const SizedBox(height: 16),
                _SummaryCard(
                  wordsLearned: widget.wordsLearned,
                  exercisesCorrect: widget.exercisesCorrect,
                  exercisesTotal: widget.exercisesTotal,
                  minutes: widget.minutes,
                  streak: widget.streak,
                ),
                const SizedBox(height: 20),
                Row(
                  children: [
                    Expanded(
                      child: OutlinedButton(
                        onPressed: widget.onRetry,
                        child: Text(t.t('retry_lesson')),
                      ),
                    ),
                    const SizedBox(width: 12),
                    Expanded(
                      child: FilledButton(
                        onPressed: widget.onContinue,
                        child: Text(t.t('continue_')),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
        ),
        ConfettiWidget(
          confettiController: _confetti,
          blastDirection: pi / 2,
          blastDirectionality: BlastDirectionality.explosive,
          numberOfParticles: 24,
          emissionFrequency: 0.06,
          gravity: 0.25,
          colors: const [
            AppTheme.primary,
            AppTheme.success,
            AppTheme.accent,
            Colors.pinkAccent,
          ],
        ),
      ],
    );
  }
}

class _SummaryCard extends StatelessWidget {
  const _SummaryCard({
    this.wordsLearned,
    this.exercisesCorrect,
    this.exercisesTotal,
    this.minutes,
    this.streak,
  });

  final int? wordsLearned;
  final int? exercisesCorrect;
  final int? exercisesTotal;
  final int? minutes;
  final int? streak;

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    final rows = <Widget>[
      if (wordsLearned != null && wordsLearned! > 0)
        _row('🔤', '${t.t('summary_words')}: $wordsLearned'),
      if (exercisesTotal != null && exercisesTotal! > 0)
        _row('✅', '${t.t('summary_exercises')}: $exercisesCorrect/$exercisesTotal'),
      if (minutes != null)
        _row('⏱️', '${t.t('summary_time')}: $minutes ${t.t('min_short')}'),
      if (streak != null && streak! > 0)
        _row('🔥', '${t.t('daily_streak')}: $streak ${t.t('days')}'),
    ];
    if (rows.isEmpty) return const SizedBox.shrink();
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(18),
        boxShadow: AppTheme.cardShadow(context),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(t.t('summary'),
              style: Theme.of(context).textTheme.labelLarge),
          const SizedBox(height: 8),
          ...rows,
        ],
      ),
    );
  }

  Widget _row(String emoji, String text) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 3),
        child: Row(
          children: [
            Text(emoji, style: const TextStyle(fontSize: 16)),
            const SizedBox(width: 8),
            Expanded(child: Text(text)),
          ],
        ),
      );
}
