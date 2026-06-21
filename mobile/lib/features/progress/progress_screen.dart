import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/i18n/app_localizations.dart';
import 'data/progress_repository.dart';

class ProgressScreen extends ConsumerWidget {
  const ProgressScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = AppLocalizations.of(context);
    final overview = ref.watch(progressOverviewProvider);

    return Scaffold(
      appBar: AppBar(title: Text(t.t('progress'))),
      body: overview.when(
        data: (levels) => ListView(
          padding: const EdgeInsets.all(16),
          children: [
            for (final l in levels)
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(12),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('${l.code} — ${l.name}',
                          style: Theme.of(context).textTheme.titleMedium),
                      const SizedBox(height: 8),
                      LinearProgressIndicator(value: l.percent / 100),
                      const SizedBox(height: 4),
                      Text('${l.percent}% — ${l.completed}/${l.total} · '
                          '${l.points} pts'),
                    ],
                  ),
                ),
              ),
          ],
        ),
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('$e')),
      ),
    );
  }
}
