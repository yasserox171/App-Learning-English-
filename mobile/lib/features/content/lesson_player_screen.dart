import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/i18n/app_localizations.dart';
import '../../core/theme/app_theme.dart';
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
  });

  final String lessonId;

  /// Page to open at (set by the lesson steps screen).
  final int initialIndex;

  @override
  ConsumerState<LessonPlayerScreen> createState() => _LessonPlayerScreenState();
}

class _LessonPlayerScreenState extends ConsumerState<LessonPlayerScreen> {
  late final PageController _controller =
      PageController(initialPage: widget.initialIndex);
  late int _index = widget.initialIndex;
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

  Widget _buildPage(LessonPageSpec spec, String backdrop) {
    switch (spec.kind) {
      case 'text':
        return MarkdownText(spec.text ?? '');
      case 'vocab_card':
        return VocabularyCard(item: spec.vocabItem!);
      case 'vocab_quiz':
        return VocabularyView(items: spec.vocabItems!);
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
            return LessonResultView(
              percent: _resultPercent,
              onRetry: _retry,
              onContinue: () {
                ref.invalidate(progressOverviewProvider);
                context.pop(true);
              },
            );
          }

          final flow = LessonFlow(l);
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

          return Column(
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
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
                  onPageChanged: (i) => setState(() => _index = i),
                  itemCount: total,
                  itemBuilder: (_, i) => SingleChildScrollView(
                    padding: const EdgeInsets.all(16),
                    child: _buildPage(flow.pages[i], flow.thumbnail),
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
