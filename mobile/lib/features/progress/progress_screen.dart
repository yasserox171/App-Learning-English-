import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/i18n/app_localizations.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/progress_ring.dart';
import '../../core/widgets/section_title.dart';
import '../../core/widgets/stat_card.dart';
import 'data/progress_repository.dart';

/// Overall progress (design screen 26): a big ring, headline stats, per-level
/// breakdown and a shortcut to certificates.
class ProgressScreen extends ConsumerWidget {
  const ProgressScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = AppLocalizations.of(context);
    final overview = ref.watch(progressOverviewProvider);

    return Scaffold(
      appBar: AppBar(title: Text(t.t('overall_progress'))),
      body: overview.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('$e')),
        data: (o) {
          final s = o.summary;
          return RefreshIndicator(
            onRefresh: () async => ref.invalidate(progressOverviewProvider),
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(20),
                    child: Row(
                      children: [
                        ProgressRing(percent: s.overallPercent, size: 96),
                        const SizedBox(width: 20),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(t.t('overall_progress'),
                                  style:
                                      Theme.of(context).textTheme.labelMedium),
                              const SizedBox(height: 4),
                              Text(
                                '${s.completedLessons}/${s.totalLessons}',
                                style: Theme.of(context)
                                    .textTheme
                                    .headlineSmall
                                    ?.copyWith(fontWeight: FontWeight.bold),
                              ),
                              Text(t.t('completed_lessons'),
                                  style:
                                      Theme.of(context).textTheme.bodySmall),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 8),
                Row(
                  children: [
                    Expanded(
                      child: StatCard(
                        icon: Icons.check_circle_rounded,
                        value: '${s.completedLessons}',
                        label: t.t('completed_lessons'),
                        color: AppTheme.success,
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: StatCard(
                        icon: Icons.menu_book_rounded,
                        value: '${s.remainingLessons}',
                        label: t.t('remaining_lessons'),
                        color: AppTheme.primary,
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: StatCard(
                        icon: Icons.local_fire_department_rounded,
                        value: '${s.streak}',
                        label: t.t('daily_streak'),
                        color: AppTheme.accent,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 8),
                SectionTitle(t.t('levels')),
                for (final l in o.levels)
                  Card(
                    child: Padding(
                      padding: const EdgeInsets.all(14),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Row(
                            children: [
                              Expanded(
                                child: Text('${l.code} — ${l.name}',
                                    style: Theme.of(context)
                                        .textTheme
                                        .titleMedium),
                              ),
                              Text('${l.percent}%',
                                  style: Theme.of(context).textTheme.labelLarge),
                            ],
                          ),
                          const SizedBox(height: 8),
                          ClipRRect(
                            borderRadius: BorderRadius.circular(6),
                            child: LinearProgressIndicator(
                              value: l.percent / 100,
                              minHeight: 6,
                            ),
                          ),
                          const SizedBox(height: 6),
                          Text('${l.completed}/${l.total} · ${l.points} ${t.t('xp')}',
                              style: Theme.of(context).textTheme.bodySmall),
                        ],
                      ),
                    ),
                  ),
                const SizedBox(height: 8),
                SectionTitle(t.t('certificates')),
                Card(
                  child: ListTile(
                    leading: const Icon(Icons.workspace_premium_rounded,
                        color: AppTheme.accent),
                    title: Text(t.t('certificates')),
                    trailing: const Icon(Icons.chevron_right),
                    onTap: () => context.push('/certificates'),
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}
