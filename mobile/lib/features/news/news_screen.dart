import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/feedback/feedback_service.dart';
import '../../core/i18n/app_localizations.dart';
import '../../core/theme/app_theme.dart';
import '../../core/tts/tts_service.dart';
import 'data/news_repository.dart';

/// Daily news story with 3 free Duolingo-style exercises (UX prompt 2.1):
/// read the story, listen to it (TTS), then answer one exercise at a time
/// with instant server-corrected feedback.
class NewsScreen extends ConsumerWidget {
  const NewsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = AppLocalizations.of(context);
    final daily = ref.watch(dailyNewsProvider);

    return Scaffold(
      appBar: AppBar(title: Text('📰 ${t.t('todays_news')}')),
      body: daily.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('$e')),
        data: (article) {
          if (article == null) {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(32),
                child: Text(t.t('no_news'), textAlign: TextAlign.center),
              ),
            );
          }
          return _NewsBody(article: article);
        },
      ),
    );
  }
}

class _NewsBody extends ConsumerStatefulWidget {
  const _NewsBody({required this.article});

  final NewsArticle article;

  @override
  ConsumerState<_NewsBody> createState() => _NewsBodyState();
}

class _NewsBodyState extends ConsumerState<_NewsBody> {
  int _exerciseIndex = 0;
  int _correctCount = 0;
  bool _finished = false;

  void _onExerciseDone(bool correct) {
    setState(() {
      if (correct) _correctCount++;
      if (_exerciseIndex + 1 >= widget.article.exercises.length) {
        _finished = true;
      } else {
        _exerciseIndex++;
      }
    });
    if (_finished) ref.read(feedbackServiceProvider).complete();
  }

  void _listen() {
    final a = widget.article;
    ref.read(ttsServiceProvider).speak('${a.titleEn}. ${a.contentShort}');
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    final a = widget.article;
    final scheme = Theme.of(context).colorScheme;

    return ListView(
      padding: const EdgeInsets.all(16),
      children: [
        if (a.imageUrl.isNotEmpty)
          ClipRRect(
            borderRadius: BorderRadius.circular(16),
            child: Image.network(
              a.imageUrl,
              height: 180,
              fit: BoxFit.cover,
              errorBuilder: (_, __, ___) => const SizedBox.shrink(),
            ),
          ),
        const SizedBox(height: 12),
        Row(
          children: [
            if (a.difficulty.isNotEmpty)
              Chip(
                label: Text(a.difficulty),
                labelStyle: const TextStyle(
                    color: Colors.white, fontWeight: FontWeight.w700),
                backgroundColor: AppTheme.primary,
                visualDensity: VisualDensity.compact,
              ),
            const SizedBox(width: 8),
            if (a.source.isNotEmpty)
              Expanded(
                child: Text(
                  a.source,
                  style: Theme.of(context).textTheme.labelMedium,
                  overflow: TextOverflow.ellipsis,
                ),
              ),
            IconButton.filledTonal(
              onPressed: _listen,
              icon: const Icon(Icons.volume_up_rounded),
              tooltip: t.t('listen'),
            ),
          ],
        ),
        const SizedBox(height: 4),
        Text(a.titleEn,
            style: Theme.of(context)
                .textTheme
                .headlineSmall
                ?.copyWith(fontWeight: FontWeight.bold)),
        if (a.titleAr.isNotEmpty) ...[
          const SizedBox(height: 4),
          Text(
            a.titleAr,
            textDirection: TextDirection.rtl,
            style: Theme.of(context)
                .textTheme
                .titleMedium
                ?.copyWith(color: scheme.onSurfaceVariant),
          ),
        ],
        const SizedBox(height: 12),
        Text(a.contentShort,
            style: Theme.of(context).textTheme.bodyLarge?.copyWith(height: 1.6)),
        const SizedBox(height: 24),
        if (a.exercises.isNotEmpty) ...[
          Row(
            children: [
              Expanded(
                child: Text('✏️ ${t.t('news_exercises')}',
                    style: Theme.of(context)
                        .textTheme
                        .titleMedium
                        ?.copyWith(fontWeight: FontWeight.bold)),
              ),
              Text(
                _finished
                    ? '${a.exercises.length}/${a.exercises.length}'
                    : '${_exerciseIndex + 1}/${a.exercises.length}',
                style: Theme.of(context).textTheme.labelLarge,
              ),
            ],
          ),
          const SizedBox(height: 10),
          if (_finished)
            Card(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  children: [
                    const Icon(Icons.emoji_events,
                        size: 64, color: Colors.amber),
                    const SizedBox(height: 8),
                    Text(
                      '${t.t('your_score')}: $_correctCount / '
                      '${a.exercises.length}',
                      style: Theme.of(context).textTheme.titleLarge,
                    ),
                  ],
                ),
              ),
            ).animate().scale(
                begin: const Offset(0.9, 0.9),
                duration: 300.ms,
                curve: Curves.easeOutBack)
          else
            _NewsExerciseCard(
              key: ValueKey(_exerciseIndex),
              article: a,
              exercise: a.exercises[_exerciseIndex],
              onDone: _onExerciseDone,
            ),
        ],
        const SizedBox(height: 24),
      ],
    );
  }
}

/// One exercise at a time; answers are corrected server-side.
class _NewsExerciseCard extends ConsumerStatefulWidget {
  const _NewsExerciseCard({
    super.key,
    required this.article,
    required this.exercise,
    required this.onDone,
  });

  final NewsArticle article;
  final NewsExercise exercise;
  final void Function(bool correct) onDone;

  @override
  ConsumerState<_NewsExerciseCard> createState() => _NewsExerciseCardState();
}

class _NewsExerciseCardState extends ConsumerState<_NewsExerciseCard> {
  bool _submitting = false;
  NewsSubmitResult? _result;

  Future<void> _submit(Map<String, dynamic> answer) async {
    if (_submitting || _result != null) return;
    setState(() => _submitting = true);
    try {
      final result = await ref
          .read(newsRepositoryProvider)
          .submit(widget.article.id, widget.exercise.id, answer);
      if (!mounted) return;
      setState(() => _result = result);
      final feedback = ref.read(feedbackServiceProvider);
      if (result.isCorrect) {
        feedback.correct();
        Future.delayed(const Duration(milliseconds: 900), () {
          if (mounted) widget.onDone(true);
        });
      } else {
        feedback.wrong();
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text('$e')));
      }
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    final content = widget.exercise.content;
    final question =
        (content['question'] ?? content['statement'] ?? '').toString();

    Widget answers;
    switch (widget.exercise.template) {
      case 'true_false':
        answers = Row(
          children: [
            Expanded(
              child: FilledButton.icon(
                style: FilledButton.styleFrom(
                  backgroundColor: AppTheme.success,
                  minimumSize: const Size.fromHeight(52),
                ),
                onPressed: () => _submit({'answer': true}),
                icon: const Icon(Icons.check),
                label: Text(t.t('tf_true')),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: FilledButton.icon(
                style: FilledButton.styleFrom(
                  backgroundColor: AppTheme.danger,
                  minimumSize: const Size.fromHeight(52),
                ),
                onPressed: () => _submit({'answer': false}),
                icon: const Icon(Icons.close),
                label: Text(t.t('tf_false')),
              ),
            ),
          ],
        );
        break;
      case 'fill_blank':
        final options = [
          for (final o in (content['options'] as List? ?? const [])) '$o',
        ];
        answers = Wrap(
          spacing: 10,
          runSpacing: 10,
          children: [
            for (final option in options)
              OutlinedButton(
                onPressed: () => _submit({'answer': option}),
                child: Text(option),
              ),
          ],
        );
        break;
      default: // multiple_choice
        final options = [
          for (final o in (content['options'] as List? ?? const [])) '$o',
        ];
        answers = Column(
          children: [
            for (var i = 0; i < options.length; i++)
              Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: OutlinedButton(
                  style: OutlinedButton.styleFrom(
                    minimumSize: const Size.fromHeight(48),
                  ),
                  onPressed: () => _submit({'selected_index': i}),
                  child: Text(options[i]),
                ),
              ),
          ],
        );
    }

    final result = _result;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(question,
                style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 14),
            if (result == null)
              answers
            else if (result.isCorrect)
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(Icons.check_circle, color: AppTheme.success),
                  const SizedBox(width: 8),
                  Text(t.t('correct'),
                      style: const TextStyle(
                          color: AppTheme.success,
                          fontWeight: FontWeight.bold)),
                ],
              ).animate().scale(
                  begin: const Offset(0.8, 0.8),
                  duration: 250.ms,
                  curve: Curves.easeOutBack)
            else ...[
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: AppTheme.danger.withOpacity(0.08),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Row(
                      children: [
                        const Icon(Icons.cancel,
                            color: AppTheme.danger, size: 20),
                        const SizedBox(width: 8),
                        if (result.correctAnswer.isNotEmpty)
                          Expanded(
                            child: Text(
                              '${t.t('correct_is')}: '
                              '${result.correctAnswer}',
                              style: const TextStyle(
                                  fontWeight: FontWeight.w600),
                            ),
                          ),
                      ],
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 12),
              FilledButton(
                onPressed: () => widget.onDone(false),
                child: Text(t.t('next')),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
