import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/feedback/feedback_service.dart';
import '../../core/i18n/app_localizations.dart';
import '../../core/theme/app_theme.dart';
import '../../core/tts/tts_service.dart';
import '../content/data/models.dart';
import 'data/assessment_repository.dart';

enum _Stage { intro, test, result }

/// Unit mastery assessment (UX prompt feature 6): intro (rules) -> 10 clean
/// questions with no immediate feedback -> pass/fail result. Passing (>= 80%)
/// unlocks the next unit.
class UnitAssessmentScreen extends ConsumerStatefulWidget {
  const UnitAssessmentScreen({
    super.key,
    required this.unitId,
    this.unitTitle = '',
  });

  final String unitId;
  final String unitTitle;

  @override
  ConsumerState<UnitAssessmentScreen> createState() =>
      _UnitAssessmentScreenState();
}

class _UnitAssessmentScreenState extends ConsumerState<UnitAssessmentScreen> {
  _Stage _stage = _Stage.intro;
  List<ExerciseItem> _questions = [];
  final Map<String, Map<String, dynamic>> _answers = {};
  int _index = 0;
  bool _busy = false;
  AssessmentResult? _result;
  String? _rated;

  Future<void> _start() async {
    setState(() => _busy = true);
    try {
      final qs =
          await ref.read(assessmentRepositoryProvider).questions(widget.unitId);
      if (!mounted) return;
      setState(() {
        _questions = qs;
        _answers.clear();
        _index = 0;
        _result = null;
        _rated = null;
        _stage = _Stage.test;
      });
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text('$e')));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _submit() async {
    setState(() => _busy = true);
    try {
      final res = await ref
          .read(assessmentRepositoryProvider)
          .submit(widget.unitId, _answers);
      if (!mounted) return;
      final feedback = ref.read(feedbackServiceProvider);
      res.passed ? feedback.levelUp() : feedback.wrong();
      setState(() {
        _result = res;
        _stage = _Stage.result;
      });
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text('$e')));
      }
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _rate(String rating) {
    setState(() => _rated = rating);
    ref
        .read(assessmentRepositoryProvider)
        .rate(widget.unitId, rating)
        .catchError((_) {});
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(t.t('unit_test'))),
      body: switch (_stage) {
        _Stage.intro => _buildIntro(t),
        _Stage.test => _buildTest(t),
        _Stage.result => _buildResult(t),
      },
    );
  }

  Widget _buildIntro(AppLocalizations t) {
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Spacer(),
            const Center(
              child: Icon(Icons.assignment_rounded,
                  size: 88, color: AppTheme.primary),
            ),
            const SizedBox(height: 16),
            Center(
              child: Text(widget.unitTitle,
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.headlineSmall),
            ),
            const SizedBox(height: 24),
            _infoRow('⏱️', '${t.t('expected_time')}: 5 ${t.t('min_short')}'),
            _infoRow('✅', '${t.t('pass_condition')}: 8/10'),
            _infoRow('ℹ️', t.t('retake_on_fail')),
            const Spacer(),
            FilledButton(
              onPressed: _busy ? null : _start,
              child: _busy
                  ? const SizedBox(
                      width: 22,
                      height: 22,
                      child: CircularProgressIndicator(strokeWidth: 2))
                  : Text(t.t('start_test')),
            ),
            const SizedBox(height: 8),
            TextButton(
              onPressed: () => context.pop(false),
              child: Text(t.t('review_lessons')),
            ),
          ],
        ),
      ),
    );
  }

  Widget _infoRow(String emoji, String text) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 6),
        child: Row(
          children: [
            Text(emoji, style: const TextStyle(fontSize: 18)),
            const SizedBox(width: 10),
            Expanded(child: Text(text)),
          ],
        ),
      );

  Widget _buildTest(AppLocalizations t) {
    if (_questions.isEmpty) {
      return const Center(child: CircularProgressIndicator());
    }
    final q = _questions[_index];
    final isLast = _index == _questions.length - 1;
    final hasAnswer = _answers[q.id]?.isNotEmpty == true;

    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
          child: Column(
            children: [
              ClipRRect(
                borderRadius: BorderRadius.circular(8),
                child: LinearProgressIndicator(
                  value: (_index + 1) / _questions.length,
                  minHeight: 8,
                ),
              ),
              const SizedBox(height: 6),
              Align(
                alignment: AlignmentDirectional.centerStart,
                child: Text(
                  '${t.t('question')} ${_index + 1} ${t.t('of')} ${_questions.length}',
                  style: Theme.of(context).textTheme.labelLarge,
                ),
              ),
            ],
          ),
        ),
        Expanded(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(16),
            child: _QuestionInput(
              key: ValueKey(q.id),
              question: q,
              initial: _answers[q.id],
              onChanged: (a) => setState(() => _answers[q.id] = a),
              onSpeak: (text) => ref.read(ttsServiceProvider).speak(text),
            ),
          ),
        ),
        SafeArea(
          top: false,
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: FilledButton(
              onPressed: !hasAnswer || _busy
                  ? null
                  : () => isLast
                      ? _submit()
                      : setState(() => _index++),
              child: _busy
                  ? const SizedBox(
                      width: 22,
                      height: 22,
                      child: CircularProgressIndicator(strokeWidth: 2))
                  : Text(isLast ? t.t('finish') : t.t('next')),
            ),
          ),
        ),
      ],
    );
  }

  Widget _buildResult(AppLocalizations t) {
    final r = _result!;
    final passed = r.passed;
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Spacer(),
            Center(
              child: Icon(
                passed ? Icons.emoji_events_rounded : Icons.replay_rounded,
                size: 96,
                color: passed ? AppTheme.accent : AppTheme.danger,
              ),
            ),
            const SizedBox(height: 16),
            Center(
              child: Text(
                passed ? t.t('unit_passed') : t.t('needs_practice'),
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.headlineSmall,
              ),
            ),
            const SizedBox(height: 8),
            Center(
              child: Text(
                '${passed ? '★ ' : ''}${r.score} / ${r.maxScore}${passed ? ' ★' : ''}',
                style: Theme.of(context).textTheme.displaySmall?.copyWith(
                      fontWeight: FontWeight.bold,
                      color: passed ? AppTheme.success : AppTheme.danger,
                    ),
              ),
            ),
            const SizedBox(height: 8),
            Center(
              child: Text(
                passed ? t.t('proud_of_you') : '${t.t('pass_condition')}: 8/10',
              ),
            ),
            if (passed) ...[
              const SizedBox(height: 18),
              Center(child: Text(t.t('rate_unit'))),
              const SizedBox(height: 6),
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  IconButton.filledTonal(
                    onPressed: _rated == null ? () => _rate('up') : null,
                    icon: Icon(Icons.thumb_up_rounded,
                        color: _rated == 'up' ? AppTheme.success : null),
                  ),
                  const SizedBox(width: 12),
                  IconButton.filledTonal(
                    onPressed: _rated == null ? () => _rate('down') : null,
                    icon: Icon(Icons.thumb_down_rounded,
                        color: _rated == 'down' ? AppTheme.danger : null),
                  ),
                ],
              ),
            ],
            const Spacer(),
            if (passed)
              FilledButton(
                onPressed: () => context.pop(true),
                child: Text(t.t('next_unit')),
              )
            else ...[
              OutlinedButton(
                onPressed: () => context.pop(false),
                child: Text('${t.t('review_lessons')} 📚'),
              ),
              const SizedBox(height: 10),
              FilledButton(
                onPressed: _busy ? null : _start,
                child: Text('${t.t('retake_test')} 🔄'),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

/// Silent answer collector for one assessment question — no grading, no hints,
/// no feedback (results are revealed only at the end).
class _QuestionInput extends StatefulWidget {
  const _QuestionInput({
    super.key,
    required this.question,
    required this.onChanged,
    required this.onSpeak,
    this.initial,
  });

  final ExerciseItem question;
  final Map<String, dynamic>? initial;
  final void Function(Map<String, dynamic>) onChanged;
  final void Function(String) onSpeak;

  @override
  State<_QuestionInput> createState() => _QuestionInputState();
}

class _QuestionInputState extends State<_QuestionInput> {
  int? _selected;
  bool? _bool;
  String? _picked;
  final _text = TextEditingController();
  final Map<String, String?> _pairs = {};
  List<String>? _order;

  @override
  void initState() {
    super.initState();
    final init = widget.initial;
    if (init != null) {
      _selected = init['selected_index'] as int?;
      _bool = init['answer'] is bool ? init['answer'] as bool : null;
      if (init['answer'] is String) _text.text = init['answer'] as String;
    }
    if (widget.question.templateCode == 'reorder') {
      _order = (widget.question.content['words'] as List)
          .cast<String>()
          .toList();
      // The starting order is already a valid answer; report it after build.
      WidgetsBinding.instance.addPostFrameCallback(
        (_) => widget.onChanged({'order': _order}),
      );
    }
  }

  @override
  void dispose() {
    _text.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    final q = widget.question;
    final c = q.content;
    final scheme = Theme.of(context).colorScheme;

    Widget option(int i, String label) {
      final selected = _selected == i;
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 5),
        child: InkWell(
          borderRadius: BorderRadius.circular(14),
          onTap: () {
            setState(() => _selected = i);
            widget.onChanged({'selected_index': i});
          },
          child: Container(
            padding:
                const EdgeInsets.symmetric(horizontal: 14, vertical: 14),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(14),
              color: selected
                  ? scheme.primary.withOpacity(0.12)
                  : scheme.surface,
              border: Border.all(
                color: selected
                    ? scheme.primary
                    : scheme.outlineVariant.withOpacity(0.5),
                width: selected ? 2 : 1,
              ),
            ),
            child: Text(label, style: const TextStyle(fontSize: 16)),
          ),
        ),
      );
    }

    switch (q.templateCode) {
      case 'multiple_choice':
        final options = (c['options'] as List).cast<String>();
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(c['question'] ?? '',
                style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            for (var i = 0; i < options.length; i++) option(i, options[i]),
          ],
        );

      case 'listening':
        final options = (c['options'] as List).cast<String>();
        final audioText = (c['audio_text'] ?? '') as String;
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            if (c['question'] != null)
              Text(c['question'],
                  style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 12),
            Center(
              child: FilledButton.icon(
                onPressed: audioText.isEmpty
                    ? null
                    : () => widget.onSpeak(audioText),
                icon: const Icon(Icons.volume_up_rounded),
                label: Text(t.t('play')),
              ),
            ),
            const SizedBox(height: 8),
            for (var i = 0; i < options.length; i++) option(i, options[i]),
          ],
        );

      case 'true_false':
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(c['statement'] ?? '',
                style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 16),
            Row(
              children: [
                Expanded(
                  child: FilledButton(
                    style: FilledButton.styleFrom(
                      backgroundColor: _bool == true
                          ? AppTheme.success
                          : scheme.surfaceContainerHighest,
                      foregroundColor:
                          _bool == true ? Colors.white : scheme.onSurface,
                    ),
                    onPressed: () {
                      setState(() => _bool = true);
                      widget.onChanged({'answer': true});
                    },
                    child: Text(t.t('tf_true')),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: FilledButton(
                    style: FilledButton.styleFrom(
                      backgroundColor: _bool == false
                          ? AppTheme.danger
                          : scheme.surfaceContainerHighest,
                      foregroundColor:
                          _bool == false ? Colors.white : scheme.onSurface,
                    ),
                    onPressed: () {
                      setState(() => _bool = false);
                      widget.onChanged({'answer': false});
                    },
                    child: Text(t.t('tf_false')),
                  ),
                ),
              ],
            ),
          ],
        );

      case 'fill_blank':
        final sentence = (c['sentence'] ?? '') as String;
        final options = (c['options'] as List?)?.cast<String>();
        if (options == null || options.isEmpty) {
          return Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(sentence,
                  style: Theme.of(context).textTheme.titleMedium),
              TextField(
                controller: _text,
                onChanged: (v) => widget.onChanged({'answer': v}),
              ),
            ],
          );
        }
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              _picked == null
                  ? sentence
                  : sentence.replaceFirst('___', '〖${_picked!}〗'),
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                for (final w in options)
                  ChoiceChip(
                    label: Text(w),
                    selected: _picked == w,
                    onSelected: (_) {
                      setState(() => _picked = w);
                      widget.onChanged({'answer': w});
                    },
                  ),
              ],
            ),
          ],
        );

      case 'matching':
        final pairs = (c['pairs'] as List).cast<Map>();
        final rights = pairs.map((p) => p['right'] as String).toList()
          ..shuffle();
        void push() => widget.onChanged({
              'pairs': [
                for (final p in pairs)
                  {'left': p['left'], 'right': _pairs[p['left']] ?? ''}
              ]
            });
        return Column(
          children: [
            for (final p in pairs)
              Row(
                children: [
                  Expanded(child: Text(p['left'] as String)),
                  Expanded(
                    child: DropdownButton<String>(
                      isExpanded: true,
                      value: _pairs[p['left']],
                      hint: const Text('—'),
                      items: rights
                          .map((r) =>
                              DropdownMenuItem(value: r, child: Text(r)))
                          .toList(),
                      onChanged: (v) {
                        setState(() => _pairs[p['left'] as String] = v);
                        push();
                      },
                    ),
                  ),
                ],
              ),
          ],
        );

      case 'reorder':
        _order ??= (c['words'] as List).cast<String>().toList();
        return SizedBox(
          height: 220,
          child: ReorderableListView(
            shrinkWrap: true,
            onReorder: (oldI, newI) {
              setState(() {
                if (newI > oldI) newI--;
                final item = _order!.removeAt(oldI);
                _order!.insert(newI, item);
              });
              widget.onChanged({'order': _order});
            },
            children: [
              for (final w in _order!)
                ListTile(key: ValueKey(w), title: Text(w)),
            ],
          ),
        );

      default:
        return Text('Unsupported: ${q.templateCode}');
    }
  }
}
