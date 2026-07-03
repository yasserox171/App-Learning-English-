import 'package:audioplayers/audioplayers.dart';
import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:speech_to_text/speech_to_text.dart' as stt;

import '../../core/feedback/feedback_service.dart';
import '../../core/i18n/app_localizations.dart';
import '../../core/theme/app_theme.dart';
import '../../core/tts/tts_service.dart';
import '../../core/widgets/feedback_fx.dart';
import '../content/data/models.dart';
import 'data/exercise_repository.dart';

/// Dispatches to the right widget per exercise template (master prompt §9).
/// Adding a new template = a new case here + a new corrector on the backend.
class ExerciseView extends ConsumerStatefulWidget {
  const ExerciseView({
    super.key,
    required this.exercise,
    this.onResult,
    this.onAdvance,
  });

  final ExerciseItem exercise;

  /// Called after each graded attempt so a parent (e.g. the lesson player) can
  /// tally the lesson score.
  final void Function(String exerciseId, AttemptResult result)? onResult;

  /// Auto-advance hook: called 600ms after a correct answer (null on the
  /// last page).
  final VoidCallback? onAdvance;

  @override
  ConsumerState<ExerciseView> createState() => _ExerciseViewState();
}

class _ExerciseViewState extends ConsumerState<ExerciseView> {
  AttemptResult? _result;
  bool _submitting = false;
  bool _usedHint = false;
  int _hintLevel = 0;
  String? _hintText;
  final Set<int> _eliminated = {};
  int _shake = 0;
  int _flash = 0;
  int _wrongCount = 0; // drives dictation's "hint after N attempts"

  void _speak(String text) => ref.read(ttsServiceProvider).speak(text);

  Future<void> _submit(Map<String, dynamic> answer) async {
    setState(() => _submitting = true);
    try {
      final res = await ref
          .read(exerciseRepositoryProvider)
          .attempt(widget.exercise.id, answer, usedHint: _usedHint);
      if (!mounted) return;
      setState(() {
        _result = res;
        if (res.isCorrect) {
          _flash++;
        } else {
          _shake++;
          _wrongCount++;
        }
      });
      widget.onResult?.call(widget.exercise.id, res);
      final feedback = ref.read(feedbackServiceProvider);
      if (res.isCorrect) {
        feedback.correct();
        if (widget.onAdvance != null) {
          Future.delayed(const Duration(milliseconds: 600), () {
            if (mounted) widget.onAdvance!();
          });
        }
      } else {
        feedback.wrong();
      }
    } catch (e) {
      if (mounted) {
        setState(() => _result = null);
        final t = AppLocalizations.of(context);
        final msg = e is DioException && e.response == null
            ? t.t('connection_error')
            : (e is DioException && e.response?.statusCode == 401
                ? t.t('session_expired')
                : '${t.t('incorrect')} — $e');
        ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));
      }
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  Future<void> _hint() async {
    final level = _hintLevel + 1;
    if (level > 2) return;
    try {
      final h = await ref
          .read(exerciseRepositoryProvider)
          .hint(widget.exercise.id, level);
      if (!mounted) return;
      setState(() {
        _hintLevel = level;
        _usedHint = true;
        if (h.hint != null && h.hint!.isNotEmpty) _hintText = h.hint;
        _eliminated.addAll(h.eliminate);
      });
    } catch (_) {
      // Hints are optional sugar — ignore network hiccups.
    }
  }

  void _retry() => setState(() => _result = null);

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    final ex = widget.exercise;
    final wrong = _result != null && !_result!.isCorrect;

    final Widget body;
    switch (ex.templateCode) {
      case 'multiple_choice':
        body = _ChoiceExercise(
            content: ex.content, onSubmit: _submit, eliminated: _eliminated);
        break;
      case 'listening':
        body = _ListeningExercise(
            content: ex.content,
            onSubmit: _submit,
            onSpeak: _speak,
            eliminated: _eliminated);
        break;
      case 'true_false':
        body = _TrueFalseExercise(content: ex.content, onSubmit: _submit);
        break;
      case 'fill_blank':
        body = _FillBlankExercise(content: ex.content, onSubmit: _submit);
        break;
      case 'matching':
        body = _MatchingExercise(content: ex.content, onSubmit: _submit);
        break;
      case 'reorder':
        body = _ReorderExercise(content: ex.content, onSubmit: _submit);
        break;
      case 'dictation':
        body = _DictationExercise(
          content: ex.content,
          onSubmit: _submit,
          onSpeak: _speak,
          wrongAttempts: _wrongCount,
        );
        break;
      case 'pronunciation':
        body = _PronunciationExercise(
          content: ex.content,
          onSubmit: _submit,
          onSpeak: _speak,
          onSkip: widget.onAdvance,
        );
        break;
      default:
        body = Text('Unsupported: ${ex.templateCode}');
    }

    return ShakeX(
      trigger: _shake,
      child: FlashGlow(
        trigger: _flash,
        color: AppTheme.success,
        child: Card(
          margin: const EdgeInsets.symmetric(vertical: 8),
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                AbsorbPointer(
                  absorbing: _submitting || _result?.isCorrect == true,
                  child: body,
                ),
                if (_hintText != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 8),
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                          horizontal: 12, vertical: 8),
                      decoration: BoxDecoration(
                        color: AppTheme.accent.withOpacity(0.12),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Text('💡 $_hintText'),
                    ),
                  ),
                if (_result == null &&
                    _hintLevel < 2 &&
                    ex.templateCode != 'dictation' &&
                    ex.templateCode != 'pronunciation')
                  Align(
                    alignment: AlignmentDirectional.centerStart,
                    child: TextButton.icon(
                      onPressed: _hint,
                      icon: const Icon(Icons.lightbulb_outline, size: 18),
                      label: Text(
                          '${t.t('hint')}${_usedHint ? '' : ' (${t.t('half_points')})'}'),
                    ),
                  ),
                if (_result?.isCorrect == true)
                  Padding(
                    padding: const EdgeInsets.only(top: 8),
                    child: Text(
                      '${t.t('correct')} (+${_result!.score})',
                      style: const TextStyle(
                        color: AppTheme.success,
                        fontWeight: FontWeight.bold,
                      ),
                    ),
                  ),
                if (wrong)
                  Padding(
                    padding: const EdgeInsets.only(top: 10),
                    child: Container(
                      width: double.infinity,
                      padding: const EdgeInsets.all(12),
                      decoration: BoxDecoration(
                        color: AppTheme.danger.withOpacity(0.08),
                        borderRadius: BorderRadius.circular(14),
                        border: Border.all(
                            color: AppTheme.danger.withOpacity(0.3)),
                      ),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text('❌ ${t.t('incorrect')}',
                              style: const TextStyle(
                                  color: AppTheme.danger,
                                  fontWeight: FontWeight.bold)),
                          if (_result!.correctAnswer?.isNotEmpty == true)
                            Padding(
                              padding: const EdgeInsets.only(top: 4),
                              child: Text(
                                  '✅ ${t.t('correct_is')}: ${_result!.correctAnswer}'),
                            ),
                          const SizedBox(height: 6),
                          OutlinedButton(
                            onPressed: _retry,
                            style: OutlinedButton.styleFrom(
                                minimumSize: const Size(0, 40)),
                            child: Text(t.t('try_again')),
                          ),
                        ],
                      ),
                    ),
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

typedef OnSubmit = Future<void> Function(Map<String, dynamic> answer);

class _ChoiceExercise extends StatefulWidget {
  const _ChoiceExercise({
    required this.content,
    required this.onSubmit,
    this.eliminated = const {},
  });
  final Map<String, dynamic> content;
  final OnSubmit onSubmit;
  final Set<int> eliminated;

  @override
  State<_ChoiceExercise> createState() => _ChoiceExerciseState();
}

class _ChoiceExerciseState extends State<_ChoiceExercise> {
  int? _selected;

  @override
  Widget build(BuildContext context) {
    final options = (widget.content['options'] as List).cast<String>();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(widget.content['question'] ?? '',
            style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 8),
        for (int i = 0; i < options.length; i++)
          _OptionTile(
            label: options[i],
            selected: _selected == i,
            disabled: widget.eliminated.contains(i),
            onTap: () => setState(() => _selected = i),
          ),
        _SubmitButton(
          onPressed: _selected == null
              ? null
              : () => widget.onSubmit({'selected_index': _selected}),
        ),
      ],
    );
  }
}

/// A selectable, card-styled answer option (multiple choice / listening).
/// [disabled] marks options struck out by a level-1 hint.
class _OptionTile extends StatelessWidget {
  const _OptionTile({
    required this.label,
    required this.selected,
    required this.onTap,
    this.disabled = false,
  });

  final String label;
  final bool selected;
  final bool disabled;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 5),
      child: Opacity(
        opacity: disabled ? 0.4 : 1,
        child: InkWell(
          borderRadius: BorderRadius.circular(14),
          onTap: disabled ? null : onTap,
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(14),
              color:
                  selected ? scheme.primary.withOpacity(0.12) : scheme.surface,
              border: Border.all(
                color: selected
                    ? scheme.primary
                    : scheme.outlineVariant.withOpacity(0.5),
                width: selected ? 2 : 1,
              ),
            ),
            child: Row(
              children: [
                Icon(
                  selected
                      ? Icons.radio_button_checked
                      : Icons.radio_button_unchecked,
                  color: selected ? scheme.primary : scheme.onSurfaceVariant,
                  size: 20,
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    label,
                    style: TextStyle(
                      fontSize: 16,
                      decoration:
                          disabled ? TextDecoration.lineThrough : null,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _TrueFalseExercise extends StatelessWidget {
  const _TrueFalseExercise({required this.content, required this.onSubmit});
  final Map<String, dynamic> content;
  final OnSubmit onSubmit;

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(content['statement'] ?? '',
            style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 16),
        Row(
          children: [
            Expanded(
              child: FilledButton.icon(
                style: FilledButton.styleFrom(
                  backgroundColor: Colors.green,
                  minimumSize: const Size.fromHeight(56),
                ),
                onPressed: () => onSubmit({'answer': true}),
                icon: const Icon(Icons.check),
                label: Text(t.t('tf_true')),
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: FilledButton.icon(
                style: FilledButton.styleFrom(
                  backgroundColor: Colors.red.shade400,
                  minimumSize: const Size.fromHeight(56),
                ),
                onPressed: () => onSubmit({'answer': false}),
                icon: const Icon(Icons.close),
                label: Text(t.t('tf_false')),
              ),
            ),
          ],
        ),
      ],
    );
  }
}

class _ListeningExercise extends StatefulWidget {
  const _ListeningExercise({
    required this.content,
    required this.onSubmit,
    required this.onSpeak,
    this.eliminated = const {},
  });
  final Map<String, dynamic> content;
  final OnSubmit onSubmit;
  final void Function(String) onSpeak;
  final Set<int> eliminated;

  @override
  State<_ListeningExercise> createState() => _ListeningExerciseState();
}

class _ListeningExerciseState extends State<_ListeningExercise> {
  int? _selected;

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    final options = (widget.content['options'] as List).cast<String>();
    final audioText = (widget.content['audio_text'] ?? '') as String;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (widget.content['question'] != null)
          Text(widget.content['question'],
              style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 16),
        Center(
          child: SizedBox(
            width: 84,
            height: 84,
            child: FilledButton(
              style: FilledButton.styleFrom(
                shape: const CircleBorder(),
                padding: EdgeInsets.zero,
              ),
              onPressed:
                  audioText.isEmpty ? null : () => widget.onSpeak(audioText),
              child: const Icon(Icons.volume_up_rounded, size: 36),
            ),
          ),
        ),
        const SizedBox(height: 6),
        Center(
            child: Text(t.t('play'),
                style: Theme.of(context).textTheme.labelMedium)),
        const SizedBox(height: 12),
        for (int i = 0; i < options.length; i++)
          _OptionTile(
            label: options[i],
            selected: _selected == i,
            disabled: widget.eliminated.contains(i),
            onTap: () => setState(() => _selected = i),
          ),
        _SubmitButton(
          onPressed: _selected == null
              ? null
              : () => widget.onSubmit({'selected_index': _selected}),
        ),
      ],
    );
  }
}

class _FillBlankExercise extends StatefulWidget {
  const _FillBlankExercise({required this.content, required this.onSubmit});
  final Map<String, dynamic> content;
  final OnSubmit onSubmit;

  @override
  State<_FillBlankExercise> createState() => _FillBlankExerciseState();
}

class _FillBlankExerciseState extends State<_FillBlankExercise> {
  final _ctrl = TextEditingController();
  String? _picked;

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    final sentence = (widget.content['sentence'] ?? '') as String;
    final options = (widget.content['options'] as List?)?.cast<String>();

    // Tappable word bank when options are provided; else fall back to typing.
    if (options == null || options.isEmpty) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(sentence, style: Theme.of(context).textTheme.titleMedium),
          TextField(controller: _ctrl),
          _SubmitButton(
            onPressed: () => widget.onSubmit({'answer': _ctrl.text}),
          ),
        ],
      );
    }

    final filled = _picked == null
        ? sentence
        : sentence.replaceFirst('___', '〖${_picked!}〗');

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(filled, style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 12),
        Text(t.t('tap_word'), style: Theme.of(context).textTheme.labelMedium),
        const SizedBox(height: 8),
        Wrap(
          spacing: 8,
          runSpacing: 8,
          children: [
            for (final w in options)
              ChoiceChip(
                label: Text(w, style: const TextStyle(fontSize: 16)),
                selected: _picked == w,
                onSelected: (_) =>
                    setState(() => _picked = _picked == w ? null : w),
              ),
          ],
        ),
        _SubmitButton(
          onPressed: _picked == null
              ? null
              : () => widget.onSubmit({'answer': _picked}),
        ),
      ],
    );
  }
}

class _MatchingExercise extends StatefulWidget {
  const _MatchingExercise({required this.content, required this.onSubmit});
  final Map<String, dynamic> content;
  final OnSubmit onSubmit;

  @override
  State<_MatchingExercise> createState() => _MatchingExerciseState();
}

class _MatchingExerciseState extends State<_MatchingExercise> {
  late List<String> _rights;
  final Map<String, String?> _picks = {};

  @override
  void initState() {
    super.initState();
    final pairs = (widget.content['pairs'] as List).cast<Map>();
    _rights = pairs.map((p) => p['right'] as String).toList()..shuffle();
  }

  @override
  Widget build(BuildContext context) {
    final pairs = (widget.content['pairs'] as List).cast<Map>();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        for (final p in pairs)
          Row(
            children: [
              Expanded(child: Text(p['left'] as String)),
              Expanded(
                child: DropdownButton<String>(
                  isExpanded: true,
                  value: _picks[p['left']],
                  hint: const Text('—'),
                  items: _rights
                      .map((r) => DropdownMenuItem(value: r, child: Text(r)))
                      .toList(),
                  onChanged: (v) =>
                      setState(() => _picks[p['left'] as String] = v),
                ),
              ),
            ],
          ),
        _SubmitButton(
          onPressed: () => widget.onSubmit({
            'pairs': [
              for (final p in pairs)
                {'left': p['left'], 'right': _picks[p['left']] ?? ''}
            ]
          }),
        ),
      ],
    );
  }
}

class _ReorderExercise extends StatefulWidget {
  const _ReorderExercise({required this.content, required this.onSubmit});
  final Map<String, dynamic> content;
  final OnSubmit onSubmit;

  @override
  State<_ReorderExercise> createState() => _ReorderExerciseState();
}

class _ReorderExerciseState extends State<_ReorderExercise> {
  late List<String> _words;

  @override
  void initState() {
    super.initState();
    _words = (widget.content['words'] as List).cast<String>().toList();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        SizedBox(
          height: 200,
          child: ReorderableListView(
            shrinkWrap: true,
            onReorder: (oldI, newI) => setState(() {
              if (newI > oldI) newI--;
              final item = _words.removeAt(oldI);
              _words.insert(newI, item);
            }),
            children: [
              for (final w in _words)
                ListTile(key: ValueKey(w), title: Text(w)),
            ],
          ),
        ),
        _SubmitButton(onPressed: () => widget.onSubmit({'order': _words})),
      ],
    );
  }
}

class _SubmitButton extends StatelessWidget {
  const _SubmitButton({this.onPressed});
  final VoidCallback? onPressed;

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: AlignmentDirectional.centerEnd,
      child: Padding(
        padding: const EdgeInsets.only(top: 8),
        child: FilledButton(
          onPressed: onPressed,
          child: Text(AppLocalizations.of(context).t('check')),
        ),
      ),
    );
  }
}

/// Dictation (UX prompt 5.3): play the audio, type what you hear. A text hint
/// from the content appears after N wrong attempts.
class _DictationExercise extends StatefulWidget {
  const _DictationExercise({
    required this.content,
    required this.onSubmit,
    required this.onSpeak,
    required this.wrongAttempts,
  });

  final Map<String, dynamic> content;
  final OnSubmit onSubmit;
  final void Function(String) onSpeak;
  final int wrongAttempts;

  @override
  State<_DictationExercise> createState() => _DictationExerciseState();
}

class _DictationExerciseState extends State<_DictationExercise> {
  final _ctrl = TextEditingController();
  final AudioPlayer _audio = AudioPlayer();

  @override
  void dispose() {
    _ctrl.dispose();
    _audio.dispose();
    super.dispose();
  }

  Future<void> _play() async {
    final url = (widget.content['audio_url'] ?? '').toString();
    if (url.isNotEmpty) {
      try {
        await _audio.stop();
        await _audio.play(UrlSource(url));
        return;
      } catch (_) {/* fall through to TTS */}
    }
    final text = (widget.content['audio_text'] ?? '').toString();
    if (text.isNotEmpty) widget.onSpeak(text);
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    final hint = (widget.content['hint'] ?? '').toString();
    final showAfter =
        (widget.content['show_hint_after_attempts'] ?? 2) as int;
    final showHint = hint.isNotEmpty && widget.wrongAttempts >= showAfter;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Center(
          child: SizedBox(
            width: 84,
            height: 84,
            child: FilledButton(
              style: FilledButton.styleFrom(
                shape: const CircleBorder(),
                padding: EdgeInsets.zero,
              ),
              onPressed: _play,
              child: const Icon(Icons.volume_up_rounded, size: 36),
            ),
          ),
        ),
        const SizedBox(height: 12),
        Text(t.t('write_what_you_hear'),
            style: Theme.of(context).textTheme.titleMedium),
        const SizedBox(height: 8),
        TextField(
          controller: _ctrl,
          textDirection: TextDirection.ltr,
          decoration: InputDecoration(hintText: '…'),
        ),
        if (showHint)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Container(
              padding:
                  const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              decoration: BoxDecoration(
                color: AppTheme.accent.withOpacity(0.12),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Text('👁️ ${t.t('hint')}: $hint'),
            ),
          ),
        _SubmitButton(
          onPressed: () => widget.onSubmit({'answer': _ctrl.text}),
        ),
      ],
    );
  }
}

/// Mirrors the backend's tolerant scorer so the UI can tier feedback locally
/// (excellent / almost / retry) before the server records the attempt.
double _pronunciationScore(String spoken, String target) {
  String phon(String s) {
    var x = s.toLowerCase().replaceAll(RegExp(r'[^a-z0-9 ]'), '');
    x = x.replaceAll(RegExp(r'\s+'), ' ').trim();
    return x.replaceAll('th', 'θ');
  }

  const tolerated = {
    'θs', 'sθ', 'θz', 'zθ', 'θt', 'tθ',
    'pb', 'bp', 'vf', 'fv', 'gj', 'jg', 'ei', 'ie', 'ou', 'uo',
  };
  final a = phon(spoken), b = phon(target);
  if (b.isEmpty) return 0;
  if (a == b) return 1;

  final n = a.length, m = b.length;
  var prev = List<double>.generate(m + 1, (j) => j.toDouble());
  for (var i = 1; i <= n; i++) {
    final cur = List<double>.filled(m + 1, 0)..[0] = i.toDouble();
    for (var j = 1; j <= m; j++) {
      final ca = a[i - 1], cb = b[j - 1];
      final sub = ca == cb
          ? 0.0
          : (tolerated.contains('$ca$cb') ? 0.3 : 1.0);
      cur[j] = [
        prev[j] + 1,
        cur[j - 1] + 1,
        prev[j - 1] + sub,
      ].reduce((x, y) => x < y ? x : y);
    }
    prev = cur;
  }
  final dist = prev[m];
  final len = n > m ? n : m;
  final score = 1 - dist / len;
  return score < 0 ? 0 : score;
}

/// Pronunciation training (UX prompt feature 11): listen to the model, record
/// with the mic, get tiered tolerant feedback. Attempt 2 reveals syllables,
/// attempt 3 an Arabic tip; after 3 attempts a no-penalty skip appears.
class _PronunciationExercise extends StatefulWidget {
  const _PronunciationExercise({
    required this.content,
    required this.onSubmit,
    required this.onSpeak,
    this.onSkip,
  });

  final Map<String, dynamic> content;
  final OnSubmit onSubmit;
  final void Function(String) onSpeak;
  final VoidCallback? onSkip;

  @override
  State<_PronunciationExercise> createState() =>
      _PronunciationExerciseState();
}

class _PronunciationExerciseState extends State<_PronunciationExercise> {
  final stt.SpeechToText _speech = stt.SpeechToText();
  final AudioPlayer _audio = AudioPlayer();
  bool _sttAvailable = true;
  bool _listening = false;
  int _attempts = 0;
  String _heard = '';
  double? _score;

  String get _target => (widget.content['target_text'] ?? '').toString();

  @override
  void dispose() {
    _speech.stop();
    _audio.dispose();
    super.dispose();
  }

  Future<void> _playModel() async {
    final url = (widget.content['reference_audio_url'] ?? '').toString();
    if (url.isNotEmpty) {
      try {
        await _audio.stop();
        await _audio.play(UrlSource(url));
        return;
      } catch (_) {/* fall through to TTS */}
    }
    widget.onSpeak(_target);
  }

  Future<void> _record() async {
    if (_listening) {
      await _speech.stop();
      if (mounted) setState(() => _listening = false);
      return;
    }
    final ok = await _speech.initialize(
      onError: (_) {
        if (mounted) setState(() => _listening = false);
      },
    );
    if (!ok) {
      if (mounted) setState(() => _sttAvailable = false);
      return;
    }
    setState(() {
      _listening = true;
      _heard = '';
    });
    await _speech.listen(
      localeId: 'en_US',
      listenFor: const Duration(seconds: 6),
      onResult: (r) {
        if (r.finalResult) _onHeard(r.recognizedWords);
      },
    );
  }

  Future<void> _onHeard(String words) async {
    await _speech.stop();
    if (!mounted) return;
    final score = _pronunciationScore(words, _target);
    setState(() {
      _listening = false;
      _heard = words;
      _score = score;
      _attempts++;
    });
    // Server records the attempt and awards partial credit.
    widget.onSubmit({'spoken_text': words});
  }

  List<String> get _syllables {
    final s = (widget.content['syllables'] ?? '').toString();
    if (s.isNotEmpty) return s.split(RegExp(r'[-\s]+'));
    return _target.split(' ');
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    final scheme = Theme.of(context).colorScheme;
    final tip = (widget.content['pronunciation_tip_ar'] ?? '').toString();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Center(
          child: Text('🎯 ${t.t('pronounce_word')}',
              style: Theme.of(context).textTheme.titleMedium),
        ),
        const SizedBox(height: 10),
        Center(
          child: Text(
            _target.toUpperCase(),
            textAlign: TextAlign.center,
            textDirection: TextDirection.ltr,
            style: const TextStyle(
              fontSize: 30,
              fontWeight: FontWeight.w800,
              letterSpacing: 2,
            ),
          ),
        ),
        const SizedBox(height: 12),
        Center(
          child: OutlinedButton.icon(
            onPressed: _playModel,
            icon: const Icon(Icons.volume_up_rounded),
            label: Text(t.t('listen_model')),
          ),
        ),
        const SizedBox(height: 14),
        if (_sttAvailable)
          Center(
            child: GestureDetector(
              onTap: _record,
              child: Container(
                width: 88,
                height: 88,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: _listening ? AppTheme.danger : AppTheme.primary,
                ),
                child: Icon(
                  _listening ? Icons.stop_rounded : Icons.mic_rounded,
                  size: 42,
                  color: Colors.white,
                ),
              ),
            ),
          )
        else
          Center(
            child: Text(t.t('mic_unavailable'),
                style: TextStyle(color: scheme.onSurfaceVariant)),
          ),
        const SizedBox(height: 6),
        Center(
          child: Text(
            _listening
                ? t.t('recording')
                : '${t.t('attempt')}: ${_attempts + 1} ${t.t('of')} 3',
            style: Theme.of(context).textTheme.labelMedium,
          ),
        ),
        if (_score != null && _heard.isNotEmpty) ...[
          const SizedBox(height: 10),
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: (_score! >= 0.7
                      ? AppTheme.success
                      : _score! >= 0.5
                          ? AppTheme.accent
                          : AppTheme.danger)
                  .withOpacity(0.10),
              borderRadius: BorderRadius.circular(14),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  _score! >= 0.9
                      ? '✅ ${t.t('excellent')}'
                      : _score! >= 0.7
                          ? '✅ ${t.t('very_good')}'
                          : _score! >= 0.5
                              ? '⚠️ ${t.t('almost')}'
                              : '❌ ${t.t('try_again')}',
                  style: const TextStyle(fontWeight: FontWeight.w800),
                ),
                const SizedBox(height: 4),
                Text('🗣 "$_heard"', textDirection: TextDirection.ltr),
              ],
            ),
          ),
        ],
        if (_attempts >= 1 && _score != null && _score! < 0.7) ...[
          const SizedBox(height: 10),
          Wrap(
            alignment: WrapAlignment.center,
            spacing: 8,
            children: [
              for (final syl in _syllables)
                ActionChip(
                  label: Text(syl.toUpperCase(),
                      textDirection: TextDirection.ltr),
                  onPressed: () => widget.onSpeak(syl),
                ),
            ],
          ),
        ],
        if (_attempts >= 2 && _score != null && _score! < 0.7) ...[
          const SizedBox(height: 8),
          Container(
            padding: const EdgeInsets.all(10),
            decoration: BoxDecoration(
              color: AppTheme.accent.withOpacity(0.12),
              borderRadius: BorderRadius.circular(12),
            ),
            child: Text(
                '💡 ${tip.isNotEmpty ? tip : t.t('pron_tip_generic')}'),
          ),
        ],
        if ((!_sttAvailable || _attempts >= 3) && widget.onSkip != null) ...[
          const SizedBox(height: 10),
          TextButton(
            onPressed: widget.onSkip,
            child: Text('${t.t('skip_step')} ←'),
          ),
        ],
      ],
    );
  }
}
