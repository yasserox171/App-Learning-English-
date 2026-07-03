import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/i18n/app_localizations.dart';
import '../../core/theme/app_theme.dart';
import 'data/content_repository.dart';
import 'data/models.dart';
import 'lesson_flow.dart';

/// ABA-style lesson overview: hero image with the lesson title, then one big
/// card per step (video / vocabulary / exercises / evaluation) with a
/// category label, an estimated duration and a green check when the lesson is
/// completed. Tapping a step opens the player at that step's first page.
class LessonStepsScreen extends ConsumerStatefulWidget {
  const LessonStepsScreen({super.key, required this.lessonId, this.summary});

  final String lessonId;

  /// Passed by the level path (thumbnail + completion state); may be null on
  /// deep links.
  final LessonSummary? summary;

  @override
  ConsumerState<LessonStepsScreen> createState() => _LessonStepsScreenState();
}

class _LessonStepsScreenState extends ConsumerState<LessonStepsScreen> {
  late bool _completed = widget.summary?.isCompleted ?? false;

  Future<void> _openPlayer(int pageStart) async {
    final replay = _completed ? '&replay=1' : '';
    final done = await context.push<bool>(
        '/lessons/${widget.lessonId}/play?step=$pageStart$replay');
    if (done == true && mounted) setState(() => _completed = true);
  }

  /// Per-step ✓ from the backend phase rows (aligned with flow.sections);
  /// a completed lesson checks everything.
  bool _stepDone(LessonFlow flow, int i) {
    if (_completed) return true;
    final steps = widget.summary?.steps;
    if (steps != null && steps.length == flow.sections.length) {
      return steps[i].completed;
    }
    return false;
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    final lesson = ref.watch(lessonProvider(widget.lessonId));

    return Scaffold(
      body: lesson.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('$e')),
        data: (l) {
          final flow = LessonFlow(l);
          final hero = widget.summary?.thumbnail.isNotEmpty == true
              ? widget.summary!.thumbnail
              : flow.thumbnail;

          return CustomScrollView(
            slivers: [
              SliverAppBar(
                expandedHeight: 220,
                pinned: true,
                flexibleSpace: FlexibleSpaceBar(
                  centerTitle: true,
                  titlePadding: const EdgeInsets.symmetric(
                      horizontal: 48, vertical: 14),
                  title: Text(
                    l.title,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: const TextStyle(
                        color: Colors.white, fontWeight: FontWeight.w800),
                  ),
                  background: _Hero(url: hero),
                ),
              ),
              SliverPadding(
                padding: const EdgeInsets.fromLTRB(16, 20, 16, 24),
                sliver: SliverList.list(
                  children: [
                    if (widget.summary?.status == 'not_started')
                      _TeacherGuideCard(
                        description: widget.summary?.description ?? '',
                        minutes: flow.sections
                            .fold<int>(0, (a, s) => a + s.minutes),
                      ),
                    for (var i = 0; i < flow.sections.length; i++)
                      _StepCard(
                        section: flow.sections[i],
                        completed: _stepDone(flow, i),
                        onTap: () => _openPlayer(flow.sections[i].pageStart),
                      ),
                    const SizedBox(height: 8),
                    FilledButton.icon(
                      onPressed: () => _openPlayer(0),
                      icon: const Icon(Icons.play_arrow_rounded),
                      label: Text(t.t('start_lesson')),
                    ),
                  ],
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}

class _Hero extends StatelessWidget {
  const _Hero({required this.url});

  final String url;

  @override
  Widget build(BuildContext context) {
    return Stack(
      fit: StackFit.expand,
      children: [
        if (url.isNotEmpty)
          Image.network(url, fit: BoxFit.cover,
              errorBuilder: (_, __, ___) => const _HeroFallback())
        else
          const _HeroFallback(),
        const DecoratedBox(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              colors: [Colors.black26, Colors.black87],
            ),
          ),
        ),
      ],
    );
  }
}

class _HeroFallback extends StatelessWidget {
  const _HeroFallback();

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        gradient: LinearGradient(
          colors: [AppTheme.primary, Color(0xFF3DDCFF)],
        ),
      ),
      child: const Center(
        child:
            Icon(Icons.menu_book_rounded, size: 72, color: Colors.white54),
      ),
    );
  }
}

/// First-open intro (UX prompt feature 2): what you'll learn (bullets derived
/// from the lesson description) + expected time. Skipped on revisits because
/// the lesson is no longer `not_started`.
class _TeacherGuideCard extends StatelessWidget {
  const _TeacherGuideCard({required this.description, required this.minutes});

  final String description;
  final int minutes;

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    final bullets = description
        .split(RegExp(r'[.,،:;]+'))
        .map((s) => s.trim())
        .where((s) => s.length > 2)
        .take(3)
        .toList();

    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.primary.withOpacity(0.08),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: AppTheme.primary.withOpacity(0.25)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text('🎯 ${t.t('you_will_learn')}',
              style: Theme.of(context)
                  .textTheme
                  .titleMedium
                  ?.copyWith(fontWeight: FontWeight.w800)),
          const SizedBox(height: 8),
          for (final b in bullets)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 2),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('• '),
                  Expanded(child: Text(b)),
                ],
              ),
            ),
          const SizedBox(height: 8),
          Text('⏱️ ${t.t('expected_time')}: $minutes ${t.t('min_short')}',
              style: Theme.of(context).textTheme.bodyMedium),
        ],
      ),
    );
  }
}

class _StepCard extends StatelessWidget {
  const _StepCard({
    required this.section,
    required this.completed,
    required this.onTap,
  });

  final LessonSection section;
  final bool completed;
  final VoidCallback onTap;

  static const _icons = {
    'text': Icons.article_rounded,
    'video': Icons.smart_display_rounded,
    'vocabulary': Icons.school_rounded,
    'exercise': Icons.edit_note_rounded,
    'evaluation': Icons.assignment_turned_in_rounded,
  };

  static const _labels = {
    'text': 'reading_step',
    'video': 'video_lesson',
    'vocabulary': 'vocabulary_step',
    'exercise': 'exercises_step',
    'evaluation': 'evaluation',
  };

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    final scheme = Theme.of(context).colorScheme;
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(20),
          onTap: onTap,
          child: Container(
            padding: const EdgeInsets.all(18),
            decoration: BoxDecoration(
              color: scheme.surface,
              borderRadius: BorderRadius.circular(20),
              boxShadow: AppTheme.cardShadow(context),
            ),
            child: Row(
              children: [
                Container(
                  width: 56,
                  height: 56,
                  decoration: BoxDecoration(
                    color: AppTheme.primary.withOpacity(0.12),
                    borderRadius: BorderRadius.circular(16),
                  ),
                  child: Icon(_icons[section.type] ?? Icons.circle,
                      color: AppTheme.primary, size: 28),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Text(
                            t.t(_labels[section.type] ?? section.type),
                            style: Theme.of(context)
                                .textTheme
                                .labelLarge
                                ?.copyWith(color: AppTheme.primary),
                          ),
                          const SizedBox(width: 8),
                          Text(
                            '${section.minutes} ${t.t('min_short')}',
                            style: Theme.of(context)
                                .textTheme
                                .labelMedium
                                ?.copyWith(color: scheme.onSurfaceVariant),
                          ),
                        ],
                      ),
                      const SizedBox(height: 2),
                      Text(
                        t.t(_labels[section.type] ?? section.type),
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                    ],
                  ),
                ),
                if (completed)
                  Container(
                    width: 40,
                    height: 40,
                    decoration: BoxDecoration(
                      color: AppTheme.success.withOpacity(0.15),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: const Icon(Icons.check_rounded,
                        color: AppTheme.success),
                  )
                else
                  Icon(Icons.chevron_right_rounded,
                      color: scheme.onSurfaceVariant),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
