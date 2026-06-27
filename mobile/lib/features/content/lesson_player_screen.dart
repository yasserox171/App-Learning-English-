import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/i18n/app_localizations.dart';
import '../../core/widgets/markdown_text.dart';
import '../exercises/exercise_view.dart';
import '../progress/data/progress_repository.dart';
import 'data/content_repository.dart';
import 'data/models.dart';
import 'vocabulary_view.dart';

class LessonPlayerScreen extends ConsumerStatefulWidget {
  const LessonPlayerScreen({super.key, required this.lessonId});

  final String lessonId;

  @override
  ConsumerState<LessonPlayerScreen> createState() => _LessonPlayerScreenState();
}

class _LessonPlayerScreenState extends ConsumerState<LessonPlayerScreen> {
  final _controller = PageController();
  int _index = 0;
  bool _finishing = false;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    final lesson = ref.watch(lessonProvider(widget.lessonId));

    return Scaffold(
      appBar: AppBar(
        title: lesson.maybeWhen(
          data: (l) => Text(l.title),
          orElse: () => Text(t.t('lesson')),
        ),
      ),
      body: lesson.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('$e')),
        data: (l) {
          final components = l.components;
          final total = components.length;
          if (total == 0) {
            return Center(child: Text(l.title));
          }
          final isLast = _index == total - 1;

          return Column(
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(8),
                  child: LinearProgressIndicator(
                    value: (_index + 1) / total,
                    minHeight: 8,
                  ),
                ),
              ),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: Align(
                  alignment: AlignmentDirectional.centerStart,
                  child: Text('${_index + 1} / $total',
                      style: Theme.of(context).textTheme.labelMedium),
                ),
              ),
              Expanded(
                child: PageView.builder(
                  controller: _controller,
                  onPageChanged: (i) => setState(() => _index = i),
                  itemCount: total,
                  itemBuilder: (_, i) => SingleChildScrollView(
                    padding: const EdgeInsets.all(16),
                    child: _StepView(component: components[i]),
                  ),
                ),
              ),
              SafeArea(
                top: false,
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Row(
                    children: [
                      if (_index > 0)
                        Expanded(
                          child: OutlinedButton(
                            onPressed: () => _controller.previousPage(
                              duration: const Duration(milliseconds: 300),
                              curve: Curves.easeOut,
                            ),
                            child: Text(t.t('back')),
                          ),
                        ),
                      if (_index > 0) const SizedBox(width: 12),
                      Expanded(
                        flex: 2,
                        child: FilledButton(
                          onPressed: _finishing
                              ? null
                              : () => isLast
                                  ? _finish(l.id)
                                  : _controller.nextPage(
                                      duration:
                                          const Duration(milliseconds: 300),
                                      curve: Curves.easeOut,
                                    ),
                          child: _finishing
                              ? const SizedBox(
                                  height: 20,
                                  width: 20,
                                  child: CircularProgressIndicator(
                                      strokeWidth: 2),
                                )
                              : Text(isLast
                                  ? t.t('finish_lesson')
                                  : t.t('next')),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          );
        },
      ),
    );
  }

  Future<void> _finish(String lessonId) async {
    setState(() => _finishing = true);
    try {
      await ref
          .read(progressRepositoryProvider)
          .updateLesson(lessonId, status: 'completed');
      ref.invalidate(progressOverviewProvider);
      if (mounted) {
        final t = AppLocalizations.of(context);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(t.t('completed'))),
        );
        context.pop();
      }
    } finally {
      if (mounted) setState(() => _finishing = false);
    }
  }
}

/// Renders a single lesson component as a full step.
class _StepView extends StatelessWidget {
  const _StepView({required this.component});

  final LessonComponent component;

  @override
  Widget build(BuildContext context) {
    switch (component.type) {
      case 'text':
        return MarkdownText((component.payload?['content'] ?? '') as String);
      case 'vocabulary':
        return VocabularyView(items: (component.payload as List?) ?? []);
      case 'video':
        final p = component.payload as Map<String, dynamic>?;
        return Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              children: [
                Container(
                  height: 160,
                  decoration: BoxDecoration(
                    color: Theme.of(context).colorScheme.primaryContainer,
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: const Center(
                    child: Icon(Icons.play_circle_fill, size: 64),
                  ),
                ),
                const SizedBox(height: 12),
                Text(p?['title'] ?? 'Video',
                    style: Theme.of(context).textTheme.titleMedium),
                Text('${p?['duration'] ?? 0}s'),
              ],
            ),
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
