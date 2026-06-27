import 'package:flutter/material.dart';

import '../../core/i18n/app_localizations.dart';
import 'vocabulary_quiz_screen.dart';

/// Vocabulary section = drills only. The words themselves are introduced in a
/// preceding component (e.g. text); here the learner only practices them via the
/// image multiple-choice quiz.
class VocabularyView extends StatelessWidget {
  const VocabularyView({super.key, required this.items});

  /// Raw vocabulary item maps from the lesson payload.
  final List items;

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    final withImages =
        items.where((v) => (v['image_url'] ?? '').toString().isNotEmpty).toList();

    if (withImages.length < 3) {
      return Card(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Center(child: Text(t.t('no_practice'))),
        ),
      );
    }

    return VocabularyQuiz(items: items);
  }
}
