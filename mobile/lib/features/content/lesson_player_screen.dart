import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/feedback/feedback_service.dart';
import '../../core/i18n/app_localizations.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/feedback_fx.dart';
import '../../core/widgets/markdown_text.dart';
import '../exercises/data/exercise_repository.dart';
import '../exercises/exercise_view.dart';
import '../progress/data/progress_repository.dart';
import 'data/content_repository.dart';
import 'data/models.dart';
import 'lesson_flow.dart';
import 'lesson_result_screen.dart';
import 'video_player_widget.dart';
import 'vocabulary_view.dart';

class LessonPlayerScreen extends ConsumerStatefulWidget {
  const LessonPlayerScreen({
    super.key,
    required this.lessonId,
    this.initialIndex = 0,
    this.replay = false,
  });

  final String lessonId;

  /// Page to open at (set by the lesson steps screen).
  final int initialIndex;

  /// Replaying a completed lesson: vocabulary order is shuffled.
  final bool replay;

  @override
  ConsumerState<LessonPlayerScreen> createState() => _LessonPlayerScreenState();
}

/// Step type -> micro-learning phase number (mirrors backend PHASE_OF).
const _phaseOf = {
  'text': 1,
  'vocabulary': 2,
  'video': 3,
  'exercise': 4,
  'evaluation': 5,
};

class _LessonPlayerScreenState extends ConsumerState<LessonPlayerScreen> {
  late final PageController _controller =
      PageController(initialPage: widget.initialIndex);
  late int _index = widget.initialIndex;
  final DateTime _startedAt = DateTime.now();
  bool _finishing = false;
  bool _finished = false;
  int _resultPercent = 0;

  // Tally of graded exercise attempts during this lesson run.
  final Map<String, AttemptResult> _results = {};
  int _totalExercises = 0;

  // Micro-learning phases already reported to the backend.
  final Set<int> _postedPhases = {};

  // Bubble-quiz outcome for the completion summary.
  int _quizCorrect = 0;
  int _quizTotal = 0;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  void _onResult(String id, AttemptResult r) => _results[id] = r;

  void _onQuizDone(int correct, int total) {
    _quizCorrect = correct;
    _quizTotal = total;
  }

  void _postPhase(int phase) {
    if (!_postedPhases.add(phase)) return;
    // Fire-and-forget: phase tracking must never block navigation.
    ref
        .read(progressRepositoryProvider)
        .completePhase(widget.lessonId, phase)
        .catchError((_) {});
  }

  /// Report every section fully behind the current page as a completed phase.
  void _syncPhases(LessonFlow flow, int page) {
    for (final s in flow.sections) {
      if (s.pageStart + s.pageCount <= page) {
        final phase = _phaseOf[s.type];
        if (phase != null) _postPhase(phase);
      }
    }
  }

  Widget _buildPage(LessonPageSpec spec, String backdrop,
      {VoidCallback? onAdvance}) {
    switch (spec.kind) {
      case 'text':
        return MarkdownText(spec.text ?? '');
      case 'vocab_card':
        return VocabularyCard(item: spec.vocabItem!);
      case 'vocab_quiz':
        return VocabularyView(items: spec.vocabItems!, onQuizDone: _onQuizDone);
      case 'video':
        return _VideoIntroPage(
          url: spec.videoUrl!,
          title: spec.videoTitle,
          backdrop: backdrop,
        );
      case 'exercise':
        return ExerciseView(
          exercise: ExerciseItem.fromJson(spec.exercise!),
          onResult: _onResult,
          onAdvance: onAdvance,
        );
      default:
        return const SizedBox.shrink();
    }
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
            final streak = ref
                .read(progressOverviewProvider)
                .valueOrNull
                ?.summary
                .streak;
            return LessonResultView(
              percent: _resultPercent,
              wordsLearned: _quizCorrect > 0 ? _quizCorrect : null,
              exercisesCorrect:
                  _results.values.where((r) => r.isCorrect).length,
              exercisesTotal: _totalExercises,
              minutes:
                  (DateTime.now().difference(_startedAt).inSeconds / 60).ceil(),
              streak: streak,
              onRetry: _retry,
              onContinue: () {
                ref.invalidate(progressOverviewProvider);
                context.pop(true);
              },
            );
          }

          final flow = LessonFlow(l, shuffleVocab: widget.replay);
          _totalExercises = flow.exerciseCount;
          final total = flow.pages.length;
          if (total == 0) return Center(child: Text(l.title));
          if (_index >= total) {
            WidgetsBinding.instance.addPostFrameCallback((_) {
              if (mounted && _controller.hasClients) {
                _controller.jumpToPage(total - 1);
              }
            });
          }
          final shown = _index.clamp(0, total - 1);
          final isLast = shown == total - 1;
          final currentPhase = _phaseOf[flow.sections
                  .where((s) =>
                      shown >= s.pageStart && shown < s.pageStart + s.pageCount)
                  .map((s) => s.type)
                  .firstOrNull] ??
              0;

          return Column(
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 10, 16, 0),
                child: _PhaseBar(
                  phases: [
                    for (final s in flow.sections)
                      if (_phaseOf[s.type] != null) _phaseOf[s.type]!,
                  ],
                  donePhases: _postedPhases,
                  currentPhase: currentPhase,
                  percent: ((shown + 1) / total * 100).round(),
                ),
              ),
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 8, 16, 4),
                child: ClipRRect(
                  borderRadius: BorderRadius.circular(8),
                  child: LinearProgressIndicator(
                    value: (shown + 1) / total,
                    minHeight: 8,
                  ),
                ),
              ),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: Align(
                  alignment: AlignmentDirectional.centerStart,
                  child: Text('${shown + 1} / $total',
                      style: Theme.of(context).textTheme.labelMedium),
                ),
              ),
              Expanded(
                child: PageView.builder(
                  controller: _controller,
                  onPageChanged: (i) {
                    setState(() => _index = i);
                    _syncPhases(flow, i);
                  },
                  itemCount: total,
                  itemBuilder: (_, i) => SingleChildScrollView(
                    padding: const EdgeInsets.all(16),
                    child: _buildPage(
                      flow.pages[i],
                      flow.thumbnail,
                      onAdvance: i < total - 1
                          ? () => _controller.nextPage(
                                duration: const Duration(milliseconds: 300),
                                curve: Curves.easeOut,
                              )
                          : null,
                    ),
                  ),
                ),
              ),
              SafeArea(
                top: false,
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Row(
                    children: [
                      if (shown > 0)
                        Expanded(
                          child: OutlinedButton(
                            onPressed: () => _controller.previousPage(
                              duration: const Duration(milliseconds: 300),
                              curve: Curves.easeOut,
                            ),
                            child: Text(t.t('back')),
                          ),
                        ),
                      if (shown > 0) const SizedBox(width: 12),
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
    // Finishing completes every phase.
    for (final p in _phaseOf.values) {
      _postPhase(p);
    }
    try {
      await ref.read(progressRepositoryProvider).updateLesson(
            lessonId,
            status: 'completed',
            score: earned,
            timeSpent: DateTime.now().difference(_startedAt).inSeconds,
          );
      ref.read(feedbackServiceProvider).complete();
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

/// The five-phase progress row (UX prompt feature 1): completed phases get a
/// green check, the current one pulses in the primary color, upcoming ones are
/// grey; the overall percentage sits at the end.
class _PhaseBar extends StatelessWidget {
  const _PhaseBar({
    required this.phases,
    required this.donePhases,
    required this.currentPhase,
    required this.percent,
  });

  final List<int> phases;
  final Set<int> donePhases;
  final int currentPhase;
  final int percent;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final unique = phases.toSet().toList()..sort();
    final lineColor = scheme.outlineVariant.withOpacity(0.5);

    Widget dot(int phase) {
      final done = donePhases.contains(phase);
      final current = phase == currentPhase && !done;
      final child = Container(
        width: 26,
        height: 26,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: done
              ? AppTheme.success
              : current
                  ? AppTheme.primary
                  : scheme.surfaceContainerHighest,
        ),
        child: done
            ? const Icon(Icons.check_rounded, size: 16, color: Colors.white)
            : Center(
                child: Text(
                  '$phase',
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w700,
                    color: current ? Colors.white : scheme.onSurfaceVariant,
                  ),
                ),
              ),
      );
      return current ? Pulse(child: child) : child;
    }

    return Row(
      children: [
        for (var i = 0; i < unique.length; i++) ...[
          dot(unique[i]),
          if (i < unique.length - 1)
            Expanded(child: Container(height: 2, color: lineColor)),
        ],
        const SizedBox(width: 10),
        Text('$percent%',
            style: Theme.of(context)
                .textTheme
                .labelLarge
                ?.copyWith(fontWeight: FontWeight.w800)),
      ],
    );
  }
}

/// Cinematic video step (ABA-style): a dark full-bleed intro with the video
/// title and a big turquoise play button; tapping it swaps in the real player
/// with autoplay.
class _VideoIntroPage extends StatefulWidget {
  const _VideoIntroPage({required this.url, this.title, this.backdrop = ''});

  final String url;
  final String? title;
  final String backdrop;

  @override
  State<_VideoIntroPage> createState() => _VideoIntroPageState();
}

class _VideoIntroPageState extends State<_VideoIntroPage> {
  bool _playing = false;

  @override
  Widget build(BuildContext context) {
    if (_playing) {
      return VideoPlayerWidget(
          url: widget.url, title: widget.title, autoPlay: true);
    }
    final t = AppLocalizations.of(context);
    return ClipRRect(
      borderRadius: BorderRadius.circular(24),
      child: Container(
        height: 460,
        color: const Color(0xFF10151F),
        child: Stack(
          fit: StackFit.expand,
          children: [
            if (widget.backdrop.isNotEmpty)
              Opacity(
                opacity: 0.35,
                child: Image.network(widget.backdrop, fit: BoxFit.cover,
                    errorBuilder: (_, __, ___) => const SizedBox.shrink()),
              ),
            const DecoratedBox(
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [Colors.black38, Colors.black87],
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Icon(Icons.movie_creation_outlined,
                      color: Colors.white, size: 40),
                  const SizedBox(height: 12),
                  Text(
                    widget.title?.isNotEmpty == true
                        ? widget.title!
                        : t.t('video_lesson'),
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 28,
                      fontWeight: FontWeight.w800,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    t.t('listening'),
                    style: const TextStyle(
                      color: AppTheme.success,
                      fontSize: 18,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    t.t('watch_video'),
                    style: const TextStyle(color: Colors.white70),
                  ),
                  const Spacer(),
                  Center(
                    child: GestureDetector(
                      onTap: () => setState(() => _playing = true),
                      child: Container(
                        width: 96,
                        height: 96,
                        decoration: const BoxDecoration(
                          shape: BoxShape.circle,
                          color: AppTheme.primary,
                        ),
                        child: const Icon(Icons.play_arrow_rounded,
                            size: 52, color: Colors.white),
                      ),
                    ),
                  ),
                  const Spacer(),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
