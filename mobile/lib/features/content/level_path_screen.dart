import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/i18n/app_localizations.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/level_seal.dart';
import '../../core/widgets/segmented_progress.dart';
import '../../core/widgets/step_dots.dart';
import '../progress/certificate_card.dart';
import '../progress/data/progress_repository.dart' show certificatesProvider;
import 'data/content_repository.dart';
import 'data/models.dart';

/// ABA-style level path: seal header, segmented progress card, then one
/// continuous vertical timeline of lesson cards grouped under unit headers,
/// ending with the level certificate card.
class LevelPathScreen extends ConsumerWidget {
  const LevelPathScreen({super.key, required this.levelId, this.level});

  final String levelId;

  /// Passed by the levels screen; when null (deep link) it's looked up.
  final Level? level;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = AppLocalizations.of(context);
    final units = ref.watch(unitsProvider(levelId));
    final certs = ref.watch(certificatesProvider);

    final resolvedLevel = level ??
        ref.watch(levelsProvider).maybeWhen(
              data: (items) => items.where((l) => l.id == levelId).firstOrNull,
              orElse: () => null,
            );
    final code = resolvedLevel?.code ?? '';
    final name = resolvedLevel?.name ?? '';

    return Scaffold(
      appBar: AppBar(title: Text(code.isEmpty ? t.t('units') : '$code · $name')),
      body: units.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('$e')),
        data: (items) {
          final totalLessons =
              items.fold<int>(0, (a, u) => a + u.total);
          final doneLessons =
              items.fold<int>(0, (a, u) => a + u.completed);
          final levelDone = totalLessons > 0 && doneLessons == totalLessons;
          final cert = certs.maybeWhen(
            data: (list) =>
                list.where((c) => c.levelCode == code).firstOrNull,
            orElse: () => null,
          );

          return RefreshIndicator(
            onRefresh: () async {
              ref.invalidate(unitsProvider(levelId));
              ref.invalidate(certificatesProvider);
            },
            child: ListView(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
              children: [
                _Header(
                  code: code,
                  name: name,
                  units: items.length,
                  lessons: totalLessons,
                ),
                const SizedBox(height: 16),
                _ProgressCard(done: doneLessons, total: totalLessons),
                const SizedBox(height: 20),
                for (var i = 0; i < items.length; i++) ...[
                  _TimelineRow(
                    node: _Node(done: items[i].isCompleted,
                        locked: items[i].locked),
                    child: _UnitHeader(index: i + 1, unit: items[i]),
                  ),
                  for (final lesson in items[i].lessons)
                    _TimelineRow(
                      child: _LessonCard(
                        lesson: lesson,
                        onTap: () async {
                          if (lesson.locked) {
                            ScaffoldMessenger.of(context).showSnackBar(
                              SnackBar(content: Text(t.t('locked_msg'))),
                            );
                            return;
                          }
                          await context.push('/lessons/${lesson.id}',
                              extra: lesson);
                          ref.invalidate(unitsProvider(levelId));
                        },
                      ),
                    ),
                ],
                _TimelineRow(
                  isLast: true,
                  node: _Node(done: levelDone, locked: !levelDone),
                  child: LevelCertificateCard(
                    levelCode: code,
                    levelName: name,
                    cert: cert,
                  ),
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}

class _Header extends StatelessWidget {
  const _Header({
    required this.code,
    required this.name,
    required this.units,
    required this.lessons,
  });

  final String code;
  final String name;
  final int units;
  final int lessons;

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        LevelSeal(code: code, size: 92),
        const SizedBox(width: 16),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text('$code. $name',
                  style: Theme.of(context).textTheme.headlineSmall),
              const SizedBox(height: 6),
              Text(
                '${t.t('study_plan')}: $units ${t.t('units')} · '
                '$lessons ${t.t('lessons')}.',
                style: Theme.of(context).textTheme.bodyMedium,
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _ProgressCard extends StatelessWidget {
  const _ProgressCard({required this.done, required this.total});

  final int done;
  final int total;

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        borderRadius: BorderRadius.circular(20),
        boxShadow: AppTheme.cardShadow(context),
      ),
      child: Column(
        children: [
          Row(
            children: [
              Expanded(
                child: Text(t.t('completed_lessons'),
                    style: Theme.of(context).textTheme.titleMedium),
              ),
              Text('$done/$total',
                  style: Theme.of(context)
                      .textTheme
                      .titleMedium
                      ?.copyWith(fontWeight: FontWeight.w800)),
            ],
          ),
          const SizedBox(height: 12),
          SegmentedProgress(completed: done, total: total),
        ],
      ),
    );
  }
}

/// One timeline entry: a narrow leading rail (node + connecting line) beside
/// the content card.
class _TimelineRow extends StatelessWidget {
  const _TimelineRow({required this.child, this.node, this.isLast = false});

  final Widget child;
  final Widget? node;
  final bool isLast;

  @override
  Widget build(BuildContext context) {
    final lineColor =
        Theme.of(context).colorScheme.outlineVariant.withOpacity(0.5);
    return IntrinsicHeight(
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          SizedBox(
            width: 36,
            child: Column(
              children: [
                if (node != null) node! else const SizedBox(height: 4),
                if (!isLast)
                  Expanded(child: Container(width: 2, color: lineColor)),
              ],
            ),
          ),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.only(bottom: 12),
              child: child,
            ),
          ),
        ],
      ),
    );
  }
}

class _Node extends StatelessWidget {
  const _Node({required this.done, required this.locked});

  final bool done;
  final bool locked;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final color = done
        ? AppTheme.success
        : locked
            ? scheme.surfaceContainerHighest
            : AppTheme.primary;
    return Container(
      width: 26,
      height: 26,
      decoration: BoxDecoration(shape: BoxShape.circle, color: color),
      child: Icon(
        done
            ? Icons.check_rounded
            : locked
                ? Icons.lock_rounded
                : Icons.play_arrow_rounded,
        size: 16,
        color: locked ? scheme.onSurfaceVariant : Colors.white,
      ),
    );
  }
}

class _UnitHeader extends StatelessWidget {
  const _UnitHeader({required this.index, required this.unit});

  final int index;
  final Unit unit;

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    final scheme = Theme.of(context).colorScheme;
    return Padding(
      padding: const EdgeInsets.only(top: 2, bottom: 4),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '${t.t('unit_n')} $index'.toUpperCase(),
            style: Theme.of(context).textTheme.labelMedium?.copyWith(
                  letterSpacing: 1.5,
                  color: scheme.onSurfaceVariant,
                ),
          ),
          Text(unit.title, style: Theme.of(context).textTheme.titleLarge),
        ],
      ),
    );
  }
}

class _LessonCard extends StatelessWidget {
  const _LessonCard({required this.lesson, required this.onTap});

  final LessonSummary lesson;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return Opacity(
      opacity: lesson.locked ? 0.55 : 1,
      child: Material(
        color: Colors.transparent,
        child: InkWell(
          borderRadius: BorderRadius.circular(20),
          onTap: onTap,
          child: Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: scheme.surface,
              borderRadius: BorderRadius.circular(20),
              boxShadow: AppTheme.cardShadow(context),
            ),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _Thumb(url: lesson.thumbnail, locked: lesson.locked),
                const SizedBox(width: 14),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(lesson.title,
                          style: Theme.of(context).textTheme.titleMedium),
                      if (lesson.description.isNotEmpty) ...[
                        const SizedBox(height: 2),
                        Text(
                          lesson.description,
                          maxLines: 2,
                          overflow: TextOverflow.ellipsis,
                          style: Theme.of(context)
                              .textTheme
                              .bodySmall
                              ?.copyWith(color: scheme.onSurfaceVariant),
                        ),
                      ],
                      const SizedBox(height: 10),
                      StepDots(
                        count: lesson.steps.length,
                        completedCount:
                            lesson.isCompleted ? lesson.steps.length : 0,
                      ),
                    ],
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

class _Thumb extends StatelessWidget {
  const _Thumb({required this.url, required this.locked});

  final String url;
  final bool locked;

  @override
  Widget build(BuildContext context) {
    final placeholder = Container(
      width: 84,
      height: 84,
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        gradient: LinearGradient(
          colors: [
            AppTheme.primary.withOpacity(0.25),
            AppTheme.success.withOpacity(0.25),
          ],
        ),
      ),
      child: Icon(
        locked ? Icons.lock_rounded : Icons.menu_book_rounded,
        color: AppTheme.primary,
        size: 32,
      ),
    );
    if (url.isEmpty) return placeholder;
    return ClipRRect(
      borderRadius: BorderRadius.circular(16),
      child: Image.network(
        url,
        width: 84,
        height: 84,
        fit: BoxFit.cover,
        errorBuilder: (_, __, ___) => placeholder,
      ),
    );
  }
}
