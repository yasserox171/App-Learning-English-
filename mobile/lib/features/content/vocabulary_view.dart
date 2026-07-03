import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/i18n/app_localizations.dart';
import '../../core/theme/app_theme.dart';
import '../../core/tts/tts_service.dart';
import 'vocabulary_quiz_screen.dart';

/// A single vocabulary teaching card (design screen 09): circular image, the
/// word, a speak button, its translation (definition) and an example sentence.
class VocabularyCard extends ConsumerWidget {
  const VocabularyCard({super.key, required this.item});

  final Map<String, dynamic> item;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = AppLocalizations.of(context);
    final scheme = Theme.of(context).colorScheme;
    final word = (item['word'] ?? '').toString();
    final translation = (item['translation'] ?? '').toString();
    final example = (item['example_sentence'] ?? '').toString();
    final image = (item['image_url'] ?? '').toString();

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Center(
              child: Text(t.t('new_word'),
                  style: Theme.of(context).textTheme.labelMedium),
            ),
            const SizedBox(height: 12),
            if (image.isNotEmpty)
              Center(
                child: ClipOval(
                  child: Image.network(
                    image,
                    width: 180,
                    height: 180,
                    fit: BoxFit.cover,
                    errorBuilder: (_, __, ___) => Container(
                      width: 180,
                      height: 180,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: scheme.surfaceContainerHighest,
                      ),
                      child: const Icon(Icons.image_not_supported, size: 64),
                    ),
                  ),
                ),
              ),
            const SizedBox(height: 16),
            Center(
              child: Text(word,
                  style: Theme.of(context)
                      .textTheme
                      .headlineSmall
                      ?.copyWith(fontWeight: FontWeight.bold)),
            ),
            const SizedBox(height: 8),
            Center(
              child: IconButton.filledTonal(
                onPressed: () => ref.read(ttsServiceProvider).speak(word),
                icon: const Icon(Icons.volume_up_rounded),
              ),
            ),
            if (translation.isNotEmpty) ...[
              const SizedBox(height: 12),
              _row(context, t.t('definition'), translation),
            ],
            if (example.isNotEmpty) ...[
              const SizedBox(height: 8),
              _row(context, t.t('example'), example),
            ],
          ],
        ),
      ),
    );
  }

  Widget _row(BuildContext context, String label, String value) {
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: AppTheme.primary.withOpacity(0.07),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: Theme.of(context).textTheme.labelSmall),
          const SizedBox(height: 2),
          Text(value, style: Theme.of(context).textTheme.bodyLarge),
        ],
      ),
    );
  }
}

/// The vocabulary practice step: an image multiple-choice quiz built from the
/// lesson's vocabulary items. Renders a placeholder if there isn't enough data.
class VocabularyView extends StatelessWidget {
  const VocabularyView({super.key, required this.items, this.onQuizDone});

  final List items;
  final void Function(int correct, int total)? onQuizDone;

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
    return VocabularyQuiz(items: items, onQuizDone: onQuizDone);
  }
}
