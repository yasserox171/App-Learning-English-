import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/i18n/app_localizations.dart';
import 'data/content_repository.dart';

class LevelsScreen extends ConsumerWidget {
  const LevelsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = AppLocalizations.of(context);
    final levels = ref.watch(levelsProvider);

    return Scaffold(
      appBar: AppBar(
        title: Text(t.t('levels')),
        actions: [
          IconButton(
            icon: const Icon(Icons.language),
            onPressed: () => ref.read(localeProvider.notifier).toggle(),
          ),
          IconButton(
            icon: const Icon(Icons.bar_chart),
            onPressed: () => context.go('/progress'),
          ),
          IconButton(
            icon: const Icon(Icons.person),
            onPressed: () => context.go('/profile'),
          ),
        ],
      ),
      body: levels.when(
        data: (items) => ListView.separated(
          itemCount: items.length,
          separatorBuilder: (_, __) => const Divider(height: 1),
          itemBuilder: (_, i) {
            final lvl = items[i];
            return ListTile(
              leading: CircleAvatar(child: Text(lvl.code)),
              title: Text(lvl.name),
              subtitle: Text(lvl.nameFr),
              trailing: lvl.isFree
                  ? const Chip(label: Text('Free'))
                  : const Icon(Icons.lock_outline),
              onTap: () => context.go('/levels/${lvl.id}/units'),
            );
          },
        ),
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('$e')),
      ),
    );
  }
}
