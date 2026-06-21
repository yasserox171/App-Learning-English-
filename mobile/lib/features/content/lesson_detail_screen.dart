import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/i18n/app_localizations.dart';
import '../exercises/exercise_view.dart';
import '../progress/data/progress_repository.dart';
import 'data/content_repository.dart';
import 'data/models.dart';

class LessonDetailScreen extends ConsumerWidget {
  const LessonDetailScreen({super.key, required this.lessonId});

  final String lessonId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = AppLocalizations.of(context);
    final lesson = ref.watch(lessonProvider(lessonId));

    return Scaffold(
      appBar: AppBar(title: Text(t.t('lesson'))),
      body: lesson.when(
        data: (l) => ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Text(l.title, style: Theme.of(context).textTheme.headlineSmall),
            const SizedBox(height: 12),
            for (final c in l.components) _ComponentView(component: c),
            const SizedBox(height: 24),
            FilledButton.icon(
              icon: const Icon(Icons.check_circle),
              label: Text(t.t('completed')),
              onPressed: () async {
                await ref
                    .read(progressRepositoryProvider)
                    .updateLesson(l.id, status: 'completed');
                ref.invalidate(progressOverviewProvider);
                if (context.mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    SnackBar(content: Text(t.t('completed'))),
                  );
                }
              },
            ),
          ],
        ),
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('$e')),
      ),
    );
  }
}

class _ComponentView extends StatelessWidget {
  const _ComponentView({required this.component});

  final LessonComponent component;

  @override
  Widget build(BuildContext context) {
    switch (component.type) {
      case 'text':
        final content = (component.payload?['content'] ?? '') as String;
        return Card(
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Text(content),
          ),
        );
      case 'vocabulary':
        final items = (component.payload as List?) ?? [];
        return Card(
          child: Column(
            children: [
              for (final v in items)
                ListTile(
                  title: Text(v['word'] ?? ''),
                  subtitle: Text(v['example_sentence'] ?? ''),
                  trailing: Text(v['translation'] ?? ''),
                ),
            ],
          ),
        );
      case 'video':
        final p = component.payload as Map<String, dynamic>?;
        return Card(
          child: ListTile(
            leading: const Icon(Icons.play_circle_fill, size: 40),
            title: Text(p?['title'] ?? 'Video'),
            subtitle: Text('${p?['duration'] ?? 0}s'),
            // Real HLS player wired later; URL via VideoService (backend §7).
          ),
        );
      case 'exercise':
        final list = (component.payload as List?) ?? [];
        return Column(
          children: [
            for (final e in list)
              ExerciseView(
                exercise: ExerciseItem.fromJson(e as Map<String, dynamic>),
              ),
          ],
        );
      default:
        return const SizedBox.shrink();
    }
  }
}
