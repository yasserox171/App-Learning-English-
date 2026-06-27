import 'dart:math';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/i18n/app_localizations.dart';
import '../../core/tts/tts_service.dart';

class _Question {
  _Question({required this.imageUrl, required this.word, required this.options});
  final String imageUrl;
  final String word; // correct answer
  final List<String> options; // shuffled, includes the correct word
}

/// Embeddable image multiple-choice vocabulary quiz, generated locally from the
/// lesson's vocabulary items (image + word). Correct answer -> green check, the
/// word is spoken aloud, then it auto-advances. Pure practice (client-side).
class VocabularyQuiz extends ConsumerStatefulWidget {
  const VocabularyQuiz({super.key, required this.items});

  final List items;

  @override
  ConsumerState<VocabularyQuiz> createState() => _VocabularyQuizState();
}

class _VocabularyQuizState extends ConsumerState<VocabularyQuiz> {
  late List<_Question> _questions;
  int _index = 0;
  int _score = 0;
  bool _mistakeOnCurrent = false;
  String? _selectedWrong;
  bool _answeredCorrect = false;
  bool _finished = false;

  @override
  void initState() {
    super.initState();
    _questions = _buildQuestions();
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
              .take(2)
              .toList();
      if (distractors.length < 2) continue;
      final options = [word, ...distractors]..shuffle(rnd);
      questions.add(_Question(
        imageUrl: v['image_url'] as String,
        word: word,
        options: options,
      ));
    }
    return questions;
  }

  void _onSelect(String option) {
    if (_answeredCorrect) return;
    final q = _questions[_index];
    if (option == q.word) {
      setState(() {
        _answeredCorrect = true;
        if (!_mistakeOnCurrent) _score++;
      });
      ref.read(ttsServiceProvider).speak(q.word);
      Future.delayed(const Duration(milliseconds: 1200), _next);
    } else {
      setState(() {
        _mistakeOnCurrent = true;
        _selectedWrong = option;
      });
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
  }

  void _restart() {
    setState(() {
      _questions = _buildQuestions();
      _index = 0;
      _score = 0;
      _answeredCorrect = false;
      _mistakeOnCurrent = false;
      _selectedWrong = null;
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
            width: 220,
            height: 220,
            child: Stack(
              alignment: Alignment.center,
              children: [
                ClipOval(
                  child: Image.network(
                    q.imageUrl,
                    width: 220,
                    height: 220,
                    fit: BoxFit.cover,
                    errorBuilder: (_, __, ___) => Container(
                      width: 220,
                      height: 220,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: Theme.of(context).colorScheme.surfaceContainerHighest,
                      ),
                      child: const Icon(Icons.image_not_supported, size: 80),
                    ),
                    loadingBuilder: (ctx, child, progress) => progress == null
                        ? child
                        : const Center(child: CircularProgressIndicator()),
                  ),
                ),
                if (_answeredCorrect)
                  const Icon(Icons.check_circle, color: Colors.green, size: 110),
              ],
            ),
          ),
        ),
        const SizedBox(height: 16),
        for (final option in q.options)
          Padding(
            padding: const EdgeInsets.symmetric(vertical: 6),
            child: _OptionButton(
              label: option,
              correct: _answeredCorrect && option == q.word,
              wrong: _selectedWrong == option,
              onPressed: () => _onSelect(option),
            ),
          ),
      ],
    );
  }
}

class _OptionButton extends StatelessWidget {
  const _OptionButton({
    required this.label,
    required this.correct,
    required this.wrong,
    required this.onPressed,
  });

  final String label;
  final bool correct;
  final bool wrong;
  final VoidCallback onPressed;

  @override
  Widget build(BuildContext context) {
    Color? bg;
    if (correct) bg = Colors.green;
    if (wrong) bg = Colors.red.shade400;
    return FilledButton(
      style: FilledButton.styleFrom(
        backgroundColor: bg,
        minimumSize: const Size.fromHeight(54),
        shape: const StadiumBorder(),
      ),
      onPressed: onPressed,
      child: Text(label, style: const TextStyle(fontSize: 18)),
    );
  }
}
