import 'dart:math';

import 'package:audioplayers/audioplayers.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/feedback/feedback_service.dart';
import '../../core/i18n/app_localizations.dart';
import '../../core/theme/app_theme.dart';
import '../../core/tts/tts_service.dart';
import '../../core/widgets/feedback_fx.dart';
import '../progress/data/progress_repository.dart';

class _Question {
  _Question({
    required this.itemId,
    required this.imageUrl,
    required this.word,
    required this.audioUrl,
    required this.options,
  });

  final String itemId;
  final String imageUrl;
  final String word; // correct answer
  final String audioUrl;
  final List<String> options; // shuffled, includes the correct word
}

/// Bubble vocabulary quiz (UX prompt feature 3): the word's image with big
/// round answer bubbles. Correct -> green + the word's real audio (or TTS) +
/// auto-advance; wrong -> shake + soft red. First-try results are reported to
/// the vocabulary tracker (new/seen/learned/mastered).
class VocabularyQuiz extends ConsumerStatefulWidget {
  const VocabularyQuiz({super.key, required this.items, this.onQuizDone});

  final List items;

  /// Called once when the quiz finishes: (firstTryCorrect, total).
  final void Function(int correct, int total)? onQuizDone;

  @override
  ConsumerState<VocabularyQuiz> createState() => _VocabularyQuizState();
}

class _VocabularyQuizState extends ConsumerState<VocabularyQuiz> {
  late List<_Question> _questions;
  final AudioPlayer _audio = AudioPlayer();
  int _index = 0;
  int _score = 0;
  bool _mistakeOnCurrent = false;
  String? _selectedWrong;
  int _wrongShake = 0;
  bool _answeredCorrect = false;
  bool _finished = false;

  /// item_id -> answered correctly on the first try.
  final Map<String, bool> _results = {};

  @override
  void initState() {
    super.initState();
    _questions = _buildQuestions();
  }

  @override
  void dispose() {
    _audio.dispose();
    super.dispose();
  }

  List<_Question> _buildQuestions() {
    final rnd = Random();
    final allWords = <String>{
      for (final v in widget.items)
        if ((v['word'] ?? '').toString().isNotEmpty) v['word'] as String,
    }.toList();

    final withImages = widget.items
        .where((v) => (v['image_url'] ?? '').toString().isNotEmpty)
        .toList()
      ..shuffle(rnd);

    final questions = <_Question>[];
    for (final v in withImages) {
      final word = v['word'] as String;
      final distractors =
          (allWords.where((w) => w != word).toList()..shuffle(rnd))
              .take(3)
              .toList();
      if (distractors.length < 2) continue;
      final options = [word, ...distractors]..shuffle(rnd);
      questions.add(_Question(
        itemId: (v['id'] ?? '').toString(),
        imageUrl: v['image_url'] as String,
        word: word,
        audioUrl: (v['audio_url'] ?? '').toString(),
        options: options,
      ));
    }
    return questions;
  }

  Future<void> _speakWord(_Question q) async {
    // Prefer the word's recorded audio; fall back to device TTS.
    await Future<void>.delayed(const Duration(milliseconds: 200));
    if (!mounted) return;
    if (q.audioUrl.isNotEmpty) {
      try {
        await _audio.stop();
        await _audio.play(UrlSource(q.audioUrl));
        return;
      } catch (_) {/* fall through to TTS */}
    }
    ref.read(ttsServiceProvider).speak(q.word);
  }

  void _onSelect(String option) {
    if (_answeredCorrect) return;
    final q = _questions[_index];
    if (option == q.word) {
      setState(() {
        _answeredCorrect = true;
        if (!_mistakeOnCurrent) _score++;
      });
      _results.putIfAbsent(q.itemId, () => !_mistakeOnCurrent);
      ref.read(feedbackServiceProvider).correct();
      _speakWord(q);
      Future.delayed(const Duration(milliseconds: 800), _next);
    } else {
      setState(() {
        _mistakeOnCurrent = true;
        _selectedWrong = option;
        _wrongShake++;
      });
      ref.read(feedbackServiceProvider).wrong();
    }
  }

  void _next() {
    if (!mounted) return;
    setState(() {
      if (_index + 1 >= _questions.length) {
        _finished = true;
      } else {
        _index++;
        _answeredCorrect = false;
        _mistakeOnCurrent = false;
        _selectedWrong = null;
      }
    });
    if (_finished) _report();
  }

  void _report() {
    widget.onQuizDone?.call(_score, _questions.length);
    final payload = [
      for (final e in _results.entries)
        if (e.key.isNotEmpty) {'item_id': e.key, 'correct': e.value},
    ];
    // Fire-and-forget: tracking must never block the learner.
    ref.read(progressRepositoryProvider).trackVocab(payload).catchError((_) {});
  }

  void _restart() {
    setState(() {
      _questions = _buildQuestions();
      _index = 0;
      _score = 0;
      _answeredCorrect = false;
      _mistakeOnCurrent = false;
      _selectedWrong = null;
      _results.clear();
      _finished = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);

    if (_questions.isEmpty) {
      return Card(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Center(child: Text(t.t('no_practice'))),
        ),
      );
    }

    if (_finished) {
      return Card(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.emoji_events, size: 72, color: Colors.amber),
              const SizedBox(height: 12),
              Text('${t.t('your_score')}: $_score / ${_questions.length}',
                  style: Theme.of(context).textTheme.titleLarge),
              const SizedBox(height: 16),
              FilledButton.icon(
                onPressed: _restart,
                icon: const Icon(Icons.refresh),
                label: Text(t.t('try_again')),
              ),
            ],
          ),
        ),
      );
    }

    final q = _questions[_index];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Row(
          children: [
            Text('${t.t('question')} ${_index + 1}/${_questions.length}',
                style: Theme.of(context).textTheme.labelLarge),
          ],
        ),
        const SizedBox(height: 8),
        ClipRRect(
          borderRadius: BorderRadius.circular(8),
          child: LinearProgressIndicator(
            value: (_index + 1) / _questions.length,
            minHeight: 6,
          ),
        ),
        const SizedBox(height: 16),
        Center(
          child: SizedBox(
            width: 200,
            height: 200,
            child: Stack(
              alignment: Alignment.center,
              children: [
                ClipOval(
                  child: Image.network(
                    q.imageUrl,
                    width: 200,
                    height: 200,
                    fit: BoxFit.cover,
                    errorBuilder: (_, __, ___) => Container(
                      width: 200,
                      height: 200,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: Theme.of(context)
                            .colorScheme
                            .surfaceContainerHighest,
                      ),
                      child: const Icon(Icons.image_not_supported, size: 80),
                    ),
                    loadingBuilder: (ctx, child, progress) => progress == null
                        ? child
                        : const Center(child: CircularProgressIndicator()),
                  ),
                ),
                if (_answeredCorrect)
                  const Icon(Icons.check_circle,
                      color: AppTheme.success, size: 100),
              ],
            ),
          ),
        ),
        const SizedBox(height: 8),
        Center(
          child: Text(t.t('what_is_this'),
              style: Theme.of(context).textTheme.titleMedium),
        ),
        const SizedBox(height: 12),
        // Thumb-friendly bubbles, 2 per row.
        Wrap(
          alignment: WrapAlignment.center,
          spacing: 14,
          runSpacing: 14,
          children: [
            for (final option in q.options)
              _Bubble(
                label: option,
                correct: _answeredCorrect && option == q.word,
                wrong: _selectedWrong == option,
                shakeTrigger: _selectedWrong == option ? _wrongShake : 0,
                onTap: () => _onSelect(option),
              ),
          ],
        ),
      ],
    );
  }
}

/// A big round answer bubble (min 80px touch target).
class _Bubble extends StatelessWidget {
  const _Bubble({
    required this.label,
    required this.correct,
    required this.wrong,
    required this.shakeTrigger,
    required this.onTap,
  });

  final String label;
  final bool correct;
  final bool wrong;
  final int shakeTrigger;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    Color bg = scheme.surface;
    Color fg = scheme.onSurface;
    Color border = scheme.outlineVariant.withOpacity(0.6);
    if (correct) {
      bg = AppTheme.success;
      fg = Colors.white;
      border = AppTheme.success;
    } else if (wrong) {
      bg = AppTheme.danger.withOpacity(0.15);
      fg = AppTheme.danger;
      border = AppTheme.danger;
    }

    return ShakeX(
      trigger: shakeTrigger,
      child: InkWell(
        customBorder: const CircleBorder(),
        onTap: onTap,
        child: Container(
          width: 108,
          height: 108,
          alignment: Alignment.center,
          padding: const EdgeInsets.all(10),
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: bg,
            border: Border.all(color: border, width: 2),
            boxShadow: AppTheme.cardShadow(context),
          ),
          child: FittedBox(
            fit: BoxFit.scaleDown,
            child: Text(
              label,
              textAlign: TextAlign.center,
              style: TextStyle(
                fontSize: 17,
                fontWeight: FontWeight.w700,
                color: fg,
              ),
            ),
          ),
        ),
      ),
    );
  }
}
