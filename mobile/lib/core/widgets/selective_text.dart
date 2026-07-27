import 'package:flutter/gestures.dart';
import 'package:flutter/material.dart';

import '../../features/content/data/models.dart';

/// Selective translation rendering (v2 §1.1).
///
/// Only terms the backend classified as *above* the lesson's own CEFR level
/// (plus idioms, context-sensitive words and the lesson's target terms) arrive
/// as annotations — those render with a subtle dotted underline and reveal
/// their Arabic meaning on tap. Everything at or below level stays plain text
/// with no translation affordance at all.
///
/// Matching is phrase-aware: multi-word entries ("boarding pass", idioms) are
/// matched before their individual words, so a fixed expression reveals as one
/// unit rather than word by word.
class SelectiveText extends StatefulWidget {
  const SelectiveText(this.text, {super.key, required this.annotations});

  final String text;
  final List<WordAnnotation> annotations;

  @override
  State<SelectiveText> createState() => _SelectiveTextState();
}

class _SelectiveTextState extends State<SelectiveText> {
  /// Term occurrences currently showing their translation.
  final Set<int> _revealed = {};
  final List<TapGestureRecognizer> _recognizers = [];

  void _disposeRecognizers() {
    for (final recognizer in _recognizers) {
      recognizer.dispose();
    }
    _recognizers.clear();
  }

  @override
  void dispose() {
    _disposeRecognizers();
    super.dispose();
  }

  /// One alternation of every annotated term, longest first so that
  /// "boarding pass" wins over "boarding".
  RegExp? _buildPattern(Iterable<String> terms) {
    final usable = terms.where((t) => t.trim().isNotEmpty).toList()
      ..sort((a, b) => b.length.compareTo(a.length));
    if (usable.isEmpty) return null;
    final alternation = usable.map(RegExp.escape).join('|');
    return RegExp(r'\b(?:' + alternation + r')\b', caseSensitive: false);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final scheme = theme.colorScheme;
    final byTerm = {
      for (final a in widget.annotations) a.word.toLowerCase(): a,
    };
    final pattern = _buildPattern(byTerm.keys);

    final baseStyle = theme.textTheme.bodyLarge?.copyWith(height: 1.6);
    if (pattern == null) {
      return Text(widget.text,
          textDirection: TextDirection.ltr, style: baseStyle);
    }

    _disposeRecognizers();
    final spans = <InlineSpan>[];
    var cursor = 0;
    var occurrence = 0;

    for (final match in pattern.allMatches(widget.text)) {
      if (match.start > cursor) {
        spans.add(TextSpan(text: widget.text.substring(cursor, match.start)));
      }
      cursor = match.end;

      final surface = match[0]!;
      final annotation = byTerm[surface.toLowerCase()];
      if (annotation == null) {
        spans.add(TextSpan(text: surface));
        continue;
      }

      final index = occurrence++;
      final recognizer = TapGestureRecognizer()
        ..onTap = () => setState(() {
              if (!_revealed.remove(index)) _revealed.add(index);
            });
      _recognizers.add(recognizer);

      spans.add(TextSpan(
        text: surface,
        recognizer: recognizer,
        style: TextStyle(
          decoration: TextDecoration.underline,
          decorationStyle: TextDecorationStyle.dotted,
          decorationColor: scheme.primary,
        ),
      ));
      if (_revealed.contains(index)) {
        spans.add(TextSpan(
          text: ' (${annotation.translationAr})',
          style: TextStyle(color: scheme.primary, fontWeight: FontWeight.w600),
        ));
      }
    }
    if (cursor < widget.text.length) {
      spans.add(TextSpan(text: widget.text.substring(cursor)));
    }

    return RichText(
      textDirection: TextDirection.ltr,
      text: TextSpan(style: baseStyle, children: spans),
    );
  }
}
