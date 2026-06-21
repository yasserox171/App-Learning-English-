import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/i18n/app_localizations.dart';
import 'data/content_repository.dart';

class LessonsScreen extends ConsumerWidget {
  const LessonsScreen({super.key, required this.unitId});

  final String unitId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = AppLocalizations.of(context);
    final lessons = ref.watch(lessonsProvider(unitId));

    return Scaffold(
      appBar: AppBar(title: Text(t.t('lessons'))),
      body: lessons.when(
        data: (items) => ListView(
          children: [
            for (final l in items)
              ListTile(
                leading: const Icon(Icons.menu_book),
                title: Text(l.title),
                subtitle: Text(l.description),
                onTap: () => context.go('/lessons/${l.id}'),
              ),
          ],
        ),
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('$e')),
      ),
    );
  }
}
