import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/i18n/app_localizations.dart';
import '../../core/tts/tts_service.dart';
import 'vocabulary_quiz_screen.dart';

/// Renders a vocabulary component: a list of words (with optional image and a
/// pronounce button) plus a "Practice" button that opens the image quiz.
class VocabularyView extends ConsumerWidget {
  const VocabularyView({super.key, required this.items});

  /// Raw vocabulary item maps from the lesson payload.
  final List items;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = AppLocalizations.of(context);
    final tts = ref.read(ttsServiceProvider);

    // The quiz needs at least 3 items with images (3 distinct options).
    final withImages =
        items.where((v) => (v['image_url'] ?? '').toString().isNotEmpty).toList();
    final canPractice = withImages.length >= 3;

    return Card(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          for (final v in items)
            ListTile(
              leading: (v['image_url'] ?? '').toString().isNotEmpty
                  ? ClipRRect(
                      borderRadius: BorderRadius.circular(6),
                      child: Image.network(
                        v['image_url'],
                        width: 48,
                        height: 48,
                        fit: BoxFit.cover,
                        errorBuilder: (_, __, ___) =>
                            const Icon(Icons.image_not_supported),
                      ),
                    )
                  : const Icon(Icons.translate),
              title: Text(v['word'] ?? ''),
              subtitle: Text(v['example_sentence'] ?? ''),
              trailing: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(v['translation'] ?? ''),
                  IconButton(
                    icon: const Icon(Icons.volume_up),
                    tooltip: t.t('listen'),
                    onPressed: () => tts.speak(v['word'] ?? ''),
                  ),
                ],
              ),
            ),
          if (canPractice)
            Padding(
              padding: const EdgeInsets.all(12),
              child: FilledButton.icon(
                icon: const Icon(Icons.quiz),
                label: Text(t.t('practice_words')),
                onPressed: () => Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (_) => VocabularyQuizScreen(items: items),
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
