import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

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
                if (_result == null && _hintLevel < 2)
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
