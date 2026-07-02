import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/i18n/app_localizations.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/gradient_header.dart';
import '../../core/widgets/progress_ring.dart';
import '../auth/auth_controller.dart';
import '../progress/data/progress_repository.dart';

/// Home dashboard (design screen 05): greeting, current-level ring, a
/// "continue learning" card and the daily streak / XP card.
class HomeDashboardScreen extends ConsumerWidget {
  const HomeDashboardScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = AppLocalizations.of(context);
    final user = ref.watch(authControllerProvider).user;
    final overview = ref.watch(progressOverviewProvider);

    return Scaffold(
      body: SafeArea(
        child: RefreshIndicator(
          onRefresh: () async => ref.invalidate(progressOverviewProvider),
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              Row(
                children: [
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text('${t.t('welcome_user')} 👋',
                            style: Theme.of(context).textTheme.bodyMedium),
                        Text(
                          user?.fullName.isNotEmpty == true
                              ? user!.fullName
                              : (user?.email ?? ''),
                          style: Theme.of(context)
                              .textTheme
                              .titleLarge
                              ?.copyWith(fontWeight: FontWeight.bold),
                        ),
                      ],
                    ),
                  ),
                  IconButton.filledTonal(
                    onPressed: () {},
                    icon: const Icon(Icons.notifications_none_rounded),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              overview.when(
                loading: () => const Padding(
                  padding: EdgeInsets.only(top: 80),
                  child: Center(child: CircularProgressIndicator()),
                ),
                error: (e, _) => Padding(
                  padding: const EdgeInsets.only(top: 40),
                  child: Center(child: Text('$e')),
                ),
                data: (data) {
                  final s = data.summary;
                  return Column(
                    children: [
                      _CurrentLevelCard(
                        levelCode: s.currentLevelCode,
                        levelName: s.currentLevelName,
                        percent: s.currentLevelPercent,
                        onTap: () => context.go('/learn'),
                      ),
                      const SizedBox(height: 14),
                      if (s.next != null)
                        _ContinueCard(
                          next: s.next!,
                          onTap: () =>
                              context.push('/lessons/${s.next!.lessonId}'),
                        ),
                      if (s.next != null) const SizedBox(height: 14),
                      _StreakCard(streak: s.streak, xp: s.xp),
                    ],
                  );
                },
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _CurrentLevelCard extends StatelessWidget {
  const _CurrentLevelCard({
    required this.levelCode,
    required this.levelName,
    required this.percent,
    required this.onTap,
  });

  final String levelCode;
  final String levelName;
  final int percent;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    return InkWell(
      borderRadius: BorderRadius.circular(22),
      onTap: onTap,
      child: GradientHeader(
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(t.t('current_level'),
                      style: const TextStyle(color: Colors.white70)),
                  const SizedBox(height: 6),
                  Text(
                    '$levelCode — $levelName',
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 22,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ],
              ),
            ),
            ProgressRing(
              percent: percent,
              size: 72,
              color: Colors.white,
            ),
          ],
        ),
      ),
    );
  }
}

class _ContinueCard extends StatelessWidget {
  const _ContinueCard({required this.next, required this.onTap});

  final ContinueLesson next;
  final VoidCallback onTap;

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
            Row(
              children: [
                if (next.thumbnail.isNotEmpty)
                  ClipRRect(
                    borderRadius: BorderRadius.circular(12),
                    child: Image.network(
                      next.thumbnail,
                      width: 52,
                      height: 52,
                      fit: BoxFit.cover,
                      errorBuilder: (_, __, ___) => const _ContinueIcon(),
                    ),
                  )
                else
                  const _ContinueIcon(),
                const SizedBox(width: 12),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(t.t('continue_learning'),
                          style: Theme.of(context).textTheme.labelMedium),
                      Text(
                        next.lessonTitle,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: Theme.of(context)
                            .textTheme
                            .titleMedium
                            ?.copyWith(fontWeight: FontWeight.bold),
                      ),
                      Text('${next.levelCode} · ${next.unitTitle}',
                          style: Theme.of(context).textTheme.bodySmall),
                    ],
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            ClipRRect(
              borderRadius: BorderRadius.circular(6),
              child: LinearProgressIndicator(
                value: next.percent / 100,
                minHeight: 6,
                backgroundColor: scheme.surfaceContainerHighest,
              ),
            ),
            const SizedBox(height: 12),
            FilledButton(
              style: FilledButton.styleFrom(backgroundColor: AppTheme.accent),
              onPressed: onTap,
              child: Text(t.t('continue_lesson')),
            ),
          ],
        ),
      ),
    );
  }
}

class _ContinueIcon extends StatelessWidget {
  const _ContinueIcon();

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(10),
      decoration: BoxDecoration(
        color: AppTheme.accent.withOpacity(0.18),
        borderRadius: BorderRadius.circular(12),
      ),
      child: const Icon(Icons.menu_book_rounded, color: AppTheme.accent),
    );
  }
}

class _StreakCard extends StatelessWidget {
  const _StreakCard({required this.streak, required this.xp});

  final int streak;
  final int xp;

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            const Icon(Icons.local_fire_department_rounded,
                color: AppTheme.accent, size: 32),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(t.t('daily_streak'),
                      style: Theme.of(context).textTheme.labelMedium),
                  Text('$streak ${t.t('days')}',
                      style: Theme.of(context)
                          .textTheme
                          .titleMedium
                          ?.copyWith(fontWeight: FontWeight.bold)),
                ],
              ),
            ),
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                Text('$xp',
                    style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        fontWeight: FontWeight.bold,
                        color: AppTheme.primary)),
                Text(t.t('xp'),
                    style: Theme.of(context).textTheme.labelSmall),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
