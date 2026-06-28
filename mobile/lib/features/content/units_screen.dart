import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/i18n/app_localizations.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/status_badge.dart';
import 'data/content_repository.dart';

/// Units of a level (design screen 07): per-unit progress + sequential lock.
class UnitsScreen extends ConsumerWidget {
  const UnitsScreen({super.key, required this.levelId});

  final String levelId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = AppLocalizations.of(context);
    final units = ref.watch(unitsProvider(levelId));

    return Scaffold(
      appBar: AppBar(title: Text(t.t('units'))),
      body: units.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('$e')),
        data: (items) => RefreshIndicator(
          onRefresh: () async => ref.invalidate(unitsProvider(levelId)),
          child: ListView(
            padding: const EdgeInsets.all(16),
            children: [
              for (int i = 0; i < items.length; i++)
                _UnitCard(
                  index: i + 1,
                  title: items[i].title,
                  description: items[i].description,
                  percent: items[i].percent,
                  locked: items[i].locked,
                  completed: items[i].isCompleted,
                  onTap: () {
                    if (items[i].locked) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(content: Text(t.t('locked_msg'))),
                      );
                      return;
                    }
                    context.push('/units/${items[i].id}/lessons');
                  },
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class _UnitCard extends StatelessWidget {
  const _UnitCard({
    required this.index,
    required this.title,
    required this.description,
    required this.percent,
    required this.locked,
    required this.completed,
    required this.onTap,
  });

  final int index;
  final String title;
  final String description;
  final int percent;
  final bool locked;
  final bool completed;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(20),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Row(
            children: [
              Container(
                width: 48,
                height: 48,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: AppTheme.accent.withOpacity(0.15),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text('$index',
                    style: const TextStyle(
                        fontWeight: FontWeight.bold,
                        color: AppTheme.accent,
                        fontSize: 18)),
              ),
              const SizedBox(width: 14),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(title,
                        style: Theme.of(context)
                            .textTheme
                            .titleMedium
                            ?.copyWith(fontWeight: FontWeight.bold)),
                    if (description.isNotEmpty)
                      Text(description,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
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
