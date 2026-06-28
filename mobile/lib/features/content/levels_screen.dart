import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/i18n/app_localizations.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/home_shell.dart';
import '../../core/widgets/status_badge.dart';
import '../progress/data/progress_repository.dart';
import 'data/content_repository.dart';

/// Levels list (design screen 06): coloured level badges, per-level progress
/// and sequential lock state.
class LevelsScreen extends ConsumerWidget {
  const LevelsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = AppLocalizations.of(context);
    final levels = ref.watch(levelsProvider);
    final overview = ref.watch(progressOverviewProvider);

    final byCode = <String, LevelProgress>{};
    overview.whenData((o) {
      for (final p in o.levels) {
        byCode[p.code] = p;
      }
    });

    return Scaffold(
      appBar: AppBar(
        title: Text(t.t('levels')),
        leading: IconButton(
          icon: const Icon(Icons.menu_rounded),
          onPressed: () => homeScaffoldKey.currentState?.openDrawer(),
        ),
      ),
      body: levels.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('$e')),
        data: (items) => RefreshIndicator(
          onRefresh: () async => ref.invalidate(progressOverviewProvider),
          child: ListView(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 16),
            children: [
              for (final lvl in items)
                _LevelCard(
                  code: lvl.code,
                  name: lvl.name,
                  subtitle: lvl.nameFr,
                  progress: byCode[lvl.code],
                  onTap: () {
                    final locked = byCode[lvl.code]?.locked ?? false;
                    if (locked) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(content: Text(t.t('locked_msg'))),
                      );
                      return;
                    }
                    context.push('/levels/${lvl.id}/units');
                  },
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class _LevelCard extends StatelessWidget {
  const _LevelCard({
    required this.code,
    required this.name,
    required this.subtitle,
    required this.progress,
    required this.onTap,
  });

  final String code;
  final String name;
  final String subtitle;
  final LevelProgress? progress;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final percent = progress?.percent ?? 0;
    final locked = progress?.locked ?? false;
    final completed = progress?.isCompleted ?? false;
    final badgeColor = locked
        ? scheme.surfaceContainerHighest
        : completed
            ? AppTheme.success
            : AppTheme.primary;

    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(20),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Row(
            children: [
              Container(
                width: 52,
                height: 52,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: badgeColor.withOpacity(locked ? 1 : 0.18),
                  borderRadius: BorderRadius.circular(14),
                ),
                child: Text(code,
                    style: TextStyle(
                      fontWeight: FontWeight.bold,
                      fontSize: 16,
                      color: locked ? scheme.onSurfaceVariant : badgeColor,
                    )),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(name,
                        style: Theme.of(context)
                            .textTheme
                            .titleMedium
                            ?.copyWith(fontWeight: FontWeight.bold)),
                    if (subtitle.isNotEmpty)
                      Text(subtitle,
                          style: Theme.of(context).textTheme.bodySmall),
                    const SizedBox(height: 8),
                    ClipRRect(
                      borderRadius: BorderRadius.circular(6),
                      child: LinearProgressIndicator(
                        value: percent / 100,
                        minHeight: 6,
                        backgroundColor: scheme.surfaceContainerHighest,
                      ),
                    ),
                    const SizedBox(height: 4),
                    Text('$percent%',
                        style: Theme.of(context).textTheme.labelSmall),
                  ],
                ),
              ),
              const SizedBox(width: 10),
              StatusBadge(locked: locked, completed: completed),
            ],
          ),
        ),
      ),
    );
  }
}
