import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/i18n/app_localizations.dart';
import '../auth/auth_controller.dart';
import '../progress/data/progress_repository.dart';
import 'data/content_repository.dart';

class LevelsScreen extends ConsumerWidget {
  const LevelsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = AppLocalizations.of(context);
    final levels = ref.watch(levelsProvider);
    final progress = ref.watch(progressOverviewProvider);

    // Map level code -> percent for quick lookup.
    final percentByCode = <String, int>{};
    progress.whenData((list) {
      for (final p in list) {
        percentByCode[p.code] = p.percent;
      }
    });

    return Scaffold(
      appBar: AppBar(
        title: Text(t.t('app_title')),
        actions: [
          IconButton(
            icon: const Icon(Icons.language),
            onPressed: () => ref.read(localeProvider.notifier).toggle(),
          ),
        ],
      ),
      body: levels.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('$e')),
        data: (items) => ListView(
          padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
          children: [
            _Header(),
            const SizedBox(height: 12),
            for (final lvl in items)
              _LevelCard(
                code: lvl.code,
                name: lvl.name,
                subtitle: lvl.nameFr,
                isFree: lvl.isFree,
                percent: percentByCode[lvl.code] ?? 0,
                onTap: () => context.push('/levels/${lvl.id}/units'),
              ),
          ],
        ),
      ),
    );
  }
}

class _Header extends ConsumerWidget {
  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = AppLocalizations.of(context);
    final scheme = Theme.of(context).colorScheme;
    final user = ref.watch(authControllerProvider).user;
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(20),
        gradient: LinearGradient(
          colors: [scheme.primary, scheme.secondary],
          begin: AlignmentDirectional.topStart,
          end: AlignmentDirectional.bottomEnd,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(t.t('welcome'),
              style: TextStyle(color: scheme.onPrimary.withOpacity(0.9))),
          const SizedBox(height: 4),
          Text(
            user?.fullName.isNotEmpty == true ? user!.fullName : t.t('keep_learning'),
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                  color: scheme.onPrimary,
                  fontWeight: FontWeight.bold,
                ),
          ),
        ],
      ),
    );
  }
}

class _LevelCard extends StatelessWidget {
  const _LevelCard({
    required this.code,
    required this.name,
    required this.subtitle,
    required this.isFree,
    required this.percent,
    required this.onTap,
  });

  final String code;
  final String name;
  final String subtitle;
  final bool isFree;
  final int percent;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(18),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Row(
            children: [
              CircleAvatar(
                radius: 26,
                backgroundColor: scheme.primaryContainer,
                child: Text(code,
                    style: TextStyle(
                        fontWeight: FontWeight.bold,
                        color: scheme.onPrimaryContainer)),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Text(name,
                              style: Theme.of(context).textTheme.titleMedium),
                        ),
                        if (isFree)
                          const Chip(
                            label: Text('Free'),
                            visualDensity: VisualDensity.compact,
                          ),
                      ],
                    ),
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
              const Icon(Icons.chevron_right),
            ],
          ),
        ),
      ),
    );
  }
}
