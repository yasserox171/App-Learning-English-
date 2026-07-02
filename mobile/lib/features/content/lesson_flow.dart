import 'data/models.dart';

/// One page of the lesson player.
class LessonPageSpec {
  const LessonPageSpec({
    required this.kind,
    this.text,
    this.vocabItem,
    this.vocabItems,
    this.videoUrl,
    this.videoTitle,
    this.exercise,
  });

  /// 'text' | 'vocab_card' | 'vocab_quiz' | 'video' | 'exercise'
  final String kind;
  final String? text;
  final Map<String, dynamic>? vocabItem;
  final List? vocabItems;
  final String? videoUrl;
  final String? videoTitle;
  final Map<String, dynamic>? exercise;
}

/// A contiguous group of pages shown as one card on the lesson steps screen.
class LessonSection {
  const LessonSection({
    required this.type,
    required this.pageStart,
    required this.pageCount,
    required this.minutes,
  });

  /// 'text' | 'vocabulary' | 'video' | 'exercise' | 'evaluation'
  final String type;
  final int pageStart;
  final int pageCount;
  final int minutes;
}

/// Flattens a [LessonDetail] into player pages + step sections. Single source
/// of truth shared by the lesson steps screen and the player, so tapping a
/// step opens the player at the right page. Pronunciation exercises are
/// skipped; final_test expands into its referenced exercises (as the
/// 'evaluation' section); a vocabulary image quiz is appended when the lesson
/// has at least 3 illustrated words.
class LessonFlow {
  LessonFlow(LessonDetail lesson) {
    final exById = <String, Map<String, dynamic>>{};
    for (final c in lesson.components) {
      if (c.type == 'exercise') {
        for (final e in (c.payload as List? ?? const [])) {
          final m = e as Map<String, dynamic>;
          exById[m['id'] as String] = m;
        }
      }
    }

    for (final c in lesson.components) {
      final start = pages.length;
      switch (c.type) {
        case 'text':
          pages.add(LessonPageSpec(
              kind: 'text', text: (c.payload?['content'] ?? '') as String));
          sections.add(LessonSection(
              type: 'text', pageStart: start, pageCount: 1, minutes: 1));
          break;

        case 'vocabulary':
          final items = (c.payload as List?) ?? const [];
          for (final v in items) {
            final item = Map<String, dynamic>.from(v as Map);
            pages.add(LessonPageSpec(kind: 'vocab_card', vocabItem: item));
            final img = (item['image_url'] ?? '').toString();
            if (thumbnail.isEmpty && img.isNotEmpty) thumbnail = img;
          }
          final withImages = items
              .where((v) => (v['image_url'] ?? '').toString().isNotEmpty)
              .length;
          if (withImages >= 3) {
            pages.add(LessonPageSpec(kind: 'vocab_quiz', vocabItems: items));
          }
          if (pages.length > start) {
            sections.add(LessonSection(
              type: 'vocabulary',
              pageStart: start,
              pageCount: pages.length - start,
              minutes: (items.length ~/ 4).clamp(1, 30),
            ));
          }
          break;

        case 'video':
          final p = c.payload as Map<String, dynamic>?;
          final url = (p?['playback_url'] ?? '') as String;
          if (url.isNotEmpty) {
            pages.add(LessonPageSpec(
                kind: 'video',
                videoUrl: url,
                videoTitle: p?['title'] as String?));
            final seconds = (p?['duration'] ?? 0) as int;
            sections.add(LessonSection(
              type: 'video',
              pageStart: start,
              pageCount: 1,
              minutes: (seconds ~/ 60).clamp(1, 120),
            ));
          }
          break;

        case 'exercise':
          var regular = 0;
          var evalStart = -1;
          var evalCount = 0;
          for (final e in (c.payload as List? ?? const [])) {
            final ex = e as Map<String, dynamic>;
            final code = ex['template_code'];
            if (code == 'pronunciation') continue; // removed exercise type
            if (code == 'final_test') {
              final ids =
                  (ex['content']?['exercise_ids'] as List?) ?? const [];
              for (final id in ids) {
                final sub = exById[id as String];
                if (sub != null && sub['template_code'] != 'pronunciation') {
                  if (evalStart < 0) evalStart = pages.length;
                  pages.add(LessonPageSpec(kind: 'exercise', exercise: sub));
                  evalCount++;
                  exerciseCount++;
                }
              }
            } else {
              pages.add(LessonPageSpec(kind: 'exercise', exercise: ex));
              regular++;
              exerciseCount++;
            }
          }
          if (regular > 0) {
            sections.add(LessonSection(
              type: 'exercise',
              pageStart: start,
              pageCount: regular,
              minutes: (regular * 0.7).round().clamp(1, 60),
            ));
          }
          if (evalCount > 0) {
            sections.add(LessonSection(
              type: 'evaluation',
              pageStart: evalStart,
              pageCount: evalCount,
              minutes: (evalCount * 0.7).round().clamp(1, 60),
            ));
          }
          break;
      }
    }
  }

  final pages = <LessonPageSpec>[];
  final sections = <LessonSection>[];
  int exerciseCount = 0;

  /// First illustrated vocabulary image — used as the hero / video backdrop.
  String thumbnail = '';
}
