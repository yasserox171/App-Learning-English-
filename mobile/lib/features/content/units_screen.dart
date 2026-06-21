import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/i18n/app_localizations.dart';
import 'data/content_repository.dart';

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
        data: (items) => ListView(
          children: [
            for (final u in items)
              ListTile(
                title: Text(u.title),
                subtitle: Text(u.description),
                trailing: const Icon(Icons.chevron_right),
                onTap: () => context.go('/units/${u.id}/lessons'),
              ),
          ],
        ),
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('$e')),
      ),
    );
  }
}
