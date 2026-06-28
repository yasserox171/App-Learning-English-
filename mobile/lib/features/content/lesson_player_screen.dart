import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/i18n/app_localizations.dart';
import '../../core/widgets/markdown_text.dart';
import '../exercises/data/exercise_repository.dart';
import '../exercises/exercise_view.dart';
import '../progress/data/progress_repository.dart';
import 'data/content_repository.dart';
import 'data/models.dart';
import 'lesson_result_screen.dart';
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
  bool _finished = false;
  int _resultPercent = 0;

  // Tally of graded exercise attempts during this lesson run.
  final Map<String, AttemptResult> _results = {};
  int _totalExercises = 0;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _onResult(String id, AttemptResult r) => _results[id] = r;

  /// Flattens the lesson into one widget per page. Vocabulary expands into one
  /// teaching card per word (+ a practice quiz); exercises are one per page;
  /// final_test expands into its referenced exercises.
  List<Widget> _buildSteps(LessonDetail l) {
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
    var exerciseCount = 0;

    void addExercise(Map<String, dynamic> ex) {
      steps.add(ExerciseView(
        exercise: ExerciseItem.fromJson(ex),
        onResult: _onResult,
      ));
      exerciseCount++;
    }

    for (final c in l.components) {
      switch (c.type) {
        case 'text':
          steps.add(MarkdownText((c.payload?['content'] ?? '') as String));
          break;
        case 'vocabulary':
          final list = (c.payload as List?) ?? const [];
          for (final v in list) {
            steps.add(VocabularyCard(item: Map<String, dynamic>.from(v as Map)));
          }
          final withImages = list
              .where((v) => (v['image_url'] ?? '').toString().isNotEmpty)
              .length;
          if (withImages >= 3) steps.add(VocabularyView(items: list));
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
            final code = ex['template_code'];
            if (code == 'pronunciation') continue; // removed exercise type
            if (code == 'final_test') {
              final ids =
                  (ex['content']?['exercise_ids'] as List?) ?? const [];
              for (final id in ids) {
                final sub = exById[id as String];
                if (sub != null && sub['template_code'] != 'pronunciation') {
                  addExercise(sub);
                }
              }
            } else {
              addExercise(ex);
            }
          }
          break;
      }
    }
    _totalExercises = exerciseCount;
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
          if (_finished) {
            return LessonResultView(
              percent: _resultPercent,
              onRetry: _retry,
              onContinue: () {
                ref.invalidate(progressOverviewProvider);
                context.pop();
              },
            );
          }

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

  void _retry() {
    setState(() {
      _finished = false;
      _index = 0;
      _results.clear();
    });
    _controller.jumpToPage(0);
  }

  int _computePercent() {
    if (_totalExercises == 0) return 100;
    final correct = _results.values.where((r) => r.isCorrect).length;
    return ((correct / _totalExercises) * 100).round();
  }

  Future<void> _finish(String lessonId) async {
    final t = AppLocalizations.of(context);
    setState(() => _finishing = true);
    final earned = _results.values.fold<int>(0, (a, r) => a + r.score);
    try {
      await ref.read(progressRepositoryProvider).updateLesson(
            lessonId,
            status: 'completed',
            score: earned,
          );
      ref.invalidate(progressOverviewProvider);
      if (mounted) {
        setState(() {
          _resultPercent = _computePercent();
          _finished = true;
        });
      }
    } catch (e) {
      if (mounted) {
        final msg = e is DioException && e.response == null
            ? t.t('connection_error')
            : (e is DioException && e.response?.statusCode == 401
                ? t.t('session_expired')
                : '$e');
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(
          content: Text(msg),
          action: SnackBarAction(
            label: t.t('retry'),
            onPressed: () => _finish(lessonId),
          ),
        ));
      }
    } finally {
      if (mounted) setState(() => _finishing = false);
    }
  }
}
