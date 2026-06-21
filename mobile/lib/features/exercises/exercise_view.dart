import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/i18n/app_localizations.dart';
import '../content/data/models.dart';
import 'data/exercise_repository.dart';

/// Dispatches to the right widget per exercise template (master prompt §9).
/// Adding a new template = a new case here + a new corrector on the backend.
class ExerciseView extends ConsumerStatefulWidget {
  const ExerciseView({super.key, required this.exercise});

  final ExerciseItem exercise;

  @override
  ConsumerState<ExerciseView> createState() => _ExerciseViewState();
}

class _ExerciseViewState extends ConsumerState<ExerciseView> {
  AttemptResult? _result;
  bool _submitting = false;

  Future<void> _submit(Map<String, dynamic> answer) async {
    setState(() => _submitting = true);
    try {
      final res = await ref
          .read(exerciseRepositoryProvider)
          .attempt(widget.exercise.id, answer);
      setState(() => _result = res);
    } catch (_) {
      setState(() => _result = null);
    } finally {
      setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    final ex = widget.exercise;

    final Widget body;
    switch (ex.templateCode) {
      case 'multiple_choice':
      case 'listening':
        body = _ChoiceExercise(content: ex.content, onSubmit: _submit);
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
      case 'pronunciation':
        body = _PronunciationExercise(content: ex.content, onSubmit: _submit);
        break;
      case 'final_test':
        body = Text('Final test: ${ex.content['exercise_ids']?.length ?? 0} items');
        break;
      default:
        body = Text('Unsupported: ${ex.templateCode}');
    }

    return Card(
      margin: const EdgeInsets.symmetric(vertical: 8),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(ex.templateCode,
                style: Theme.of(context).textTheme.labelSmall),
            const SizedBox(height: 8),
            AbsorbPointer(absorbing: _submitting, child: body),
            if (_result != null)
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(
                  _result!.isCorrect
                      ? '${t.t('correct')} (+${_result!.score})'
                      : t.t('incorrect'),
                  style: TextStyle(
                    color: _result!.isCorrect ? Colors.green : Colors.red,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

typedef OnSubmit = Future<void> Function(Map<String, dynamic> answer);

class _ChoiceExercise extends StatefulWidget {
  const _ChoiceExercise({required this.content, required this.onSubmit});
  final Map<String, dynamic> content;
  final OnSubmit onSubmit;

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
        Text(widget.content['question'] ?? ''),
        for (int i = 0; i < options.length; i++)
          RadioListTile<int>(
            value: i,
            groupValue: _selected,
            title: Text(options[i]),
            onChanged: (v) => setState(() => _selected = v),
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

class _TrueFalseExercise extends StatelessWidget {
  const _TrueFalseExercise({required this.content, required this.onSubmit});
  final Map<String, dynamic> content;
  final OnSubmit onSubmit;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(content['statement'] ?? ''),
        const SizedBox(height: 8),
        Row(
          children: [
            FilledButton(
              onPressed: () => onSubmit({'answer': true}),
              child: const Text('True'),
            ),
            const SizedBox(width: 12),
            OutlinedButton(
              onPressed: () => onSubmit({'answer': false}),
              child: const Text('False'),
            ),
          ],
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

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(widget.content['sentence'] ?? ''),
        TextField(controller: _ctrl),
        _SubmitButton(
          onPressed: () => widget.onSubmit({'answer': _ctrl.text}),
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

class _PronunciationExercise extends StatelessWidget {
  const _PronunciationExercise({required this.content, required this.onSubmit});
  final Map<String, dynamic> content;
  final OnSubmit onSubmit;

  @override
  Widget build(BuildContext context) {
    // MVP: recording/audio analysis simplified (master prompt §9).
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Say: "${content['target_text']}"'),
        _SubmitButton(
          onPressed: () => onSubmit({'recorded': true}),
        ),
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
