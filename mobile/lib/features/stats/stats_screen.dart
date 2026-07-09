import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/i18n/app_localizations.dart';
import '../../core/theme/app_theme.dart';
import '../progress/data/progress_repository.dart';
import 'data/stats_repository.dart';

Color _statusColor(String status) => switch (status) {
      'strong' => AppTheme.success,
      'growing' => AppTheme.accent,
      _ => AppTheme.danger,
    };

String _statusEmoji(String status) => switch (status) {
      'strong' => '✅',
      'growing' => '⭐',
      _ => '⚠️',
    };

String _fmtDuration(int seconds) {
  final h = seconds ~/ 3600;
  final m = (seconds % 3600) ~/ 60;
  if (h > 0) return '${h}h ${m}m';
  return '${m}m';
}

/// Advanced stats dashboard tab (UX prompt 2.2): overall progress, vocabulary
/// heatmap, skills chain, level progress, time investment, and weak areas —
/// all drawn with lightweight custom widgets (no chart package).
class StatsScreen extends ConsumerWidget {
  const StatsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = AppLocalizations.of(context);
    final bundle = ref.watch(statsBundleProvider);

    return Scaffold(
      appBar: AppBar(title: Text('📊 ${t.t('stats')}')),
      body: bundle.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('$e')),
        data: (data) => RefreshIndicator(
          onRefresh: () async => ref.invalidate(statsBundleProvider),
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              _OverallCard(overview: data.overview),
              const SizedBox(height: 14),
              _TimeCard(time: data.time),
              const SizedBox(height: 14),
              if (data.weakAreas.isNotEmpty) ...[
                _WeakAreasCard(areas: data.weakAreas),
                const SizedBox(height: 14),
              ],
              _LevelProgressCard(),
              const SizedBox(height: 14),
              if (data.skills.isNotEmpty) ...[
                _SkillsCard(skills: data.skills),
                const SizedBox(height: 14),
              ],
              _HeatmapCard(units: data.heatmap),
              const SizedBox(height: 24),
            ],
          ),
        ),
      ),
    );
  }
}

// --- 1. Overall progress ---------------------------------------------------- //
class _OverallCard extends StatelessWidget {
  const _OverallCard({required this.overview});

  final StatsOverview overview;

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(t.t('overall_progress'),
                style: Theme.of(context)
                    .textTheme
                    .titleMedium
                    ?.copyWith(fontWeight: FontWeight.bold)),
            const SizedBox(height: 10),
            Row(
              children: [
                Text('${overview.overallPercent}%',
                    style: Theme.of(context).textTheme.displaySmall?.copyWith(
                        fontWeight: FontWeight.w800,
                        color: AppTheme.primary)),
                const SizedBox(width: 12),
                Expanded(
                  child: ClipRRect(
                    borderRadius: BorderRadius.circular(8),
                    child: LinearProgressIndicator(
                      value: overview.overallPercent / 100,
                      minHeight: 12,
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 14),
            Row(
              children: [
                _MiniStat(
                    emoji: '🔥',
                    value: '${overview.streak}',
                    label: t.t('daily_streak')),
                _MiniStat(
                    emoji: '⚡', value: '${overview.xp}', label: t.t('xp')),
                _MiniStat(
                    emoji: '🔤',
                    value: '${overview.wordsLearned}',
                    label: t.t('words_learned')),
                _MiniStat(
                    emoji: '⏱️',
                    value: _fmtDuration(overview.totalTimeSeconds),
                    label: t.t('study_time')),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _MiniStat extends StatelessWidget {
  const _MiniStat(
      {required this.emoji, required this.value, required this.label});

  final String emoji;
  final String value;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Expanded(
      child: Column(
        children: [
          Text(emoji, style: const TextStyle(fontSize: 18)),
          const SizedBox(height: 2),
          Text(value,
              style: Theme.of(context)
                  .textTheme
                  .titleSmall
                  ?.copyWith(fontWeight: FontWeight.w800)),
          Text(label,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.labelSmall,
              maxLines: 1,
              overflow: TextOverflow.ellipsis),
        ],
      ),
    );
  }
}

// --- 2. Time investment ------------------------------------------------------ //
class _TimeCard extends StatelessWidget {
  const _TimeCard({required this.time});

  final TimeInvestment time;

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    final maxWeek = time.weekSeconds.fold<int>(0, (a, b) => a > b ? a : b);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text('⏱️ ${t.t('time_investment')}',
                      style: Theme.of(context)
                          .textTheme
                          .titleMedium
                          ?.copyWith(fontWeight: FontWeight.bold)),
                ),
                Text(_fmtDuration(time.totalSeconds),
                    style: Theme.of(context)
                        .textTheme
                        .labelLarge
                        ?.copyWith(color: AppTheme.primary)),
              ],
            ),
            const SizedBox(height: 4),
            Text(t.t('last_30_days'),
                style: Theme.of(context).textTheme.labelSmall),
            const SizedBox(height: 12),
            SizedBox(
              height: 110,
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.end,
                children: [
                  for (var i = 0; i < time.weekSeconds.length; i++) ...[
                    if (i > 0) const SizedBox(width: 12),
                    Expanded(
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.end,
                        children: [
                          Text(_fmtDuration(time.weekSeconds[i]),
                              style:
                                  Theme.of(context).textTheme.labelSmall),
                          const SizedBox(height: 4),
                          AnimatedContainer(
                            duration: const Duration(milliseconds: 500),
                            curve: Curves.easeOut,
                            height: maxWeek == 0
                                ? 4
                                : 4 + 60.0 * time.weekSeconds[i] / maxWeek,
                            decoration: BoxDecoration(
                              gradient: const LinearGradient(
                                begin: Alignment.bottomCenter,
                                end: Alignment.topCenter,
                                colors: [AppTheme.primary, Color(0xFF64D8F5)],
                              ),
                              borderRadius: BorderRadius.circular(6),
                            ),
                          ),
                          const SizedBox(height: 4),
                          Text('W${i + 1}',
                              style:
                                  Theme.of(context).textTheme.labelSmall),
                        ],
                      ),
                    ),
                  ],
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// --- 3. Weak areas ------------------------------------------------------------ //
class _WeakAreasCard extends StatelessWidget {
  const _WeakAreasCard({required this.areas});

  final List<WeakArea> areas;

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('🎯 ${t.t('weak_areas')}',
                style: Theme.of(context)
                    .textTheme
                    .titleMedium
                    ?.copyWith(fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            for (var i = 0; i < areas.length; i++)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 6),
                child: Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('${i + 1}. ${areas[i].title}',
                              style: Theme.of(context)
                                  .textTheme
                                  .bodyMedium
                                  ?.copyWith(fontWeight: FontWeight.w600)),
                          Text(
                            '${areas[i].accuracy}% ${t.t('accuracy')}',
                            style: Theme.of(context)
                                .textTheme
                                .labelSmall
                                ?.copyWith(color: AppTheme.danger),
                          ),
                        ],
                      ),
                    ),
                    if (areas[i].practiceLessonId != null)
                      FilledButton.tonal(
                        onPressed: () => context
                            .push('/lessons/${areas[i].practiceLessonId}'),
                        child: Text(t.t('practice_now')),
                      ),
                  ],
                ),
              ),
          ],
        ),
      ),
    );
  }
}

// --- 4. Level progress --------------------------------------------------------- //
class _LevelProgressCard extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = AppLocalizations.of(context);
    final overview = ref.watch(progressOverviewProvider);
    final levels = overview.valueOrNull?.levels ?? const [];
    if (levels.isEmpty) return const SizedBox.shrink();

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('🎓 ${t.t('level_progress')}',
                style: Theme.of(context)
                    .textTheme
                    .titleMedium
                    ?.copyWith(fontWeight: FontWeight.bold)),
            const SizedBox(height: 10),
            for (final level in levels)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 5),
                child: Row(
                  children: [
                    SizedBox(
                      width: 34,
                      child: Text(level.code,
                          style: Theme.of(context)
                              .textTheme
                              .labelLarge
                              ?.copyWith(fontWeight: FontWeight.w800)),
                    ),
                    Expanded(
                      child: ClipRRect(
                        borderRadius: BorderRadius.circular(6),
                        child: LinearProgressIndicator(
                          value: level.percent / 100,
                          minHeight: 10,
                          color: level.isCompleted
                              ? AppTheme.success
                              : AppTheme.primary,
                        ),
                      ),
                    ),
                    const SizedBox(width: 10),
                    SizedBox(
                      width: 62,
                      child: Text(
                        level.locked
                            ? '🔒'
                            : '${level.completed}/${level.total}',
                        textAlign: TextAlign.end,
                        style: Theme.of(context).textTheme.labelMedium,
                      ),
                    ),
                  ],
                ),
              ),
          ],
        ),
      ),
    );
  }
}

// --- 5. Skills chain ------------------------------------------------------------ //
class _SkillsCard extends StatelessWidget {
  const _SkillsCard({required this.skills});

  final List<SkillNode> skills;

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    final scheme = Theme.of(context).colorScheme;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('🌳 ${t.t('skills_tree')}',
                style: Theme.of(context)
                    .textTheme
                    .titleMedium
                    ?.copyWith(fontWeight: FontWeight.bold)),
            const SizedBox(height: 10),
            for (var i = 0; i < skills.length; i++) ...[
              if (i > 0)
                Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 13),
                  child: Container(
                    width: 2,
                    height: 14,
                    color: scheme.outlineVariant,
                  ),
                ),
              Row(
                children: [
                  Container(
                    width: 28,
                    height: 28,
                    alignment: Alignment.center,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      color: _statusColor(skills[i].status).withOpacity(0.15),
                    ),
                    child: Text(_statusEmoji(skills[i].status),
                        style: const TextStyle(fontSize: 13)),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(
                      '${skills[i].levelCode} · ${skills[i].title}',
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: Theme.of(context)
                          .textTheme
                          .bodyMedium
                          ?.copyWith(fontWeight: FontWeight.w600),
                    ),
                  ),
                  Text('${skills[i].accuracy}%',
                      style: Theme.of(context).textTheme.labelLarge?.copyWith(
                          color: _statusColor(skills[i].status),
                          fontWeight: FontWeight.w800)),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }
}

// --- 6. Vocabulary heatmap -------------------------------------------------------- //
class _HeatmapCard extends StatelessWidget {
  const _HeatmapCard({required this.units});

  final List<HeatmapUnit> units;

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    // Started topics first (most informative), then the rest.
    final started = units.where((u) => u.learnedWords > 0).toList();
    final rows = started.isEmpty ? units.take(6).toList() : started;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('🔤 ${t.t('vocab_heatmap')}',
                style: Theme.of(context)
                    .textTheme
                    .titleMedium
                    ?.copyWith(fontWeight: FontWeight.bold)),
            const SizedBox(height: 10),
            if (rows.isEmpty)
              Text(t.t('no_data_yet'),
                  style: Theme.of(context).textTheme.bodyMedium)
            else
              for (final unit in rows)
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 5),
                  child: Row(
                    children: [
                      Text(_statusEmoji(unit.status),
                          style: const TextStyle(fontSize: 14)),
                      const SizedBox(width: 8),
                      Expanded(
                        flex: 3,
                        child: Text(
                          unit.title,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                      ),
                      Expanded(
                        flex: 2,
                        child: ClipRRect(
                          borderRadius: BorderRadius.circular(5),
                          child: LinearProgressIndicator(
                            value: unit.percent / 100,
                            minHeight: 8,
                            color: _statusColor(unit.status),
                          ),
                        ),
                      ),
                      SizedBox(
                        width: 44,
                        child: Text('${unit.percent}%',
                            textAlign: TextAlign.end,
                            style: Theme.of(context).textTheme.labelMedium),
                      ),
                    ],
                  ),
                ),
          ],
        ),
      ),
    );
  }
}
