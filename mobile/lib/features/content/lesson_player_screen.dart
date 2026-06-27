import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/i18n/app_localizations.dart';
import '../../core/widgets/markdown_text.dart';
import '../exercises/exercise_view.dart';
import '../progress/data/progress_repository.dart';
import 'data/content_repository.dart';
import 'data/models.dart';
import 'video_player_widget.dart';
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

  /// Flattens the lesson into one widget per page (one exercise per page;
  /// final_test expands into its referenced exercises).
  List<Widget> _buildSteps(LessonDetail l) {
    // Index every exercise by id so final_test can resolve its references.
    final exById = <String, Map<String, dynamic>>{};
    for (final c in l.components) {
      if (c.type == 'exercise') {
        for (final e in (c.payload as List? ?? const [])) {
          final m = e as Map<String, dynamic>;
          exById[m['id'] as String] = m;
        }
      }
    }

    final steps = <Widget>[];
    for (final c in l.components) {
      switch (c.type) {
        case 'text':
          steps.add(MarkdownText((c.payload?['content'] ?? '') as String));
          break;
        case 'vocabulary':
          steps.add(VocabularyView(items: (c.payload as List?) ?? const []));
          break;
        case 'video':
          final p = c.payload as Map<String, dynamic>?;
          final url = (p?['playback_url'] ?? '') as String;
          if (url.isNotEmpty) {
            steps.add(VideoPlayerWidget(url: url, title: p?['title'] as String?));
          }
          break;
        case 'exercise':
          for (final e in (c.payload as List? ?? const [])) {
            final ex = e as Map<String, dynamic>;
            if (ex['template_code'] == 'final_test') {
              final ids =
                  (ex['content']?['exercise_ids'] as List?) ?? const [];
              for (final id in ids) {
                final sub = exById[id as String];
                if (sub != null) {
                  steps.add(ExerciseView(exercise: ExerciseItem.fromJson(sub)));
                }
              }
            } else {
              steps.add(ExerciseView(exercise: ExerciseItem.fromJson(ex)));
            }
          }
          break;
      }
    }
    return steps;
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
          final steps = _buildSteps(l);
          final total = steps.length;
          if (total == 0) return Center(child: Text(l.title));
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
                    child: steps[i],
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
    final t = AppLocalizations.of(context);
    setState(() => _finishing = true);
    try {
      await ref
          .read(progressRepositoryProvider)
          .updateLesson(lessonId, status: 'completed');
      ref.invalidate(progressOverviewProvider);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(t.t('completed'))),
        );
        context.pop();
      }
    } catch (e) {
      if (mounted) {
        final msg = e is DioException && e.response == null
            ? t.t('connection_error')
            : (e is DioException && e.response?.statusCode == 401
                ? t.t('session_expired')
                : '$e');
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(msg)));
      }
    } finally {
      if (mounted) setState(() => _finishing = false);
    }
  }
}
