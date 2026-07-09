import 'package:flutter/material.dart';
import 'package:flutter_animate/flutter_animate.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:share_plus/share_plus.dart';

import '../../core/config.dart';
import '../../core/i18n/app_localizations.dart';
import '../../core/theme/app_theme.dart';
import 'data/achievements_repository.dart';

/// Badge gallery (UX prompt 3.2): unlocked badges in color, locked ones
/// dimmed with their unlock condition; tapping an unlocked badge offers a
/// share sheet.
class AchievementsScreen extends ConsumerWidget {
  const AchievementsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = AppLocalizations.of(context);
    final achievements = ref.watch(achievementsProvider);

    return Scaffold(
      appBar: AppBar(title: Text('🏅 ${t.t('achievements')}')),
      body: achievements.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('$e')),
        data: (payload) {
          final unlocked =
              payload.badges.where((b) => b.unlocked).length;
          return RefreshIndicator(
            onRefresh: () async => ref.invalidate(achievementsProvider),
            child: ListView(
              padding: const EdgeInsets.all(16),
              children: [
                Text(
                  '$unlocked / ${payload.badges.length} ${t.t('unlocked')}',
                  style: Theme.of(context).textTheme.titleMedium,
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 16),
                GridView.count(
                  crossAxisCount: 2,
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  mainAxisSpacing: 12,
                  crossAxisSpacing: 12,
                  childAspectRatio: 0.95,
                  children: [
                    for (var i = 0; i < payload.badges.length; i++)
                      _BadgeCard(badge: payload.badges[i])
                          .animate(delay: (60 * i).ms)
                          .fadeIn(duration: 250.ms)
                          .scale(
                              begin: const Offset(0.92, 0.92),
                              curve: Curves.easeOutBack),
                  ],
                ),
              ],
            ),
          );
        },
      ),
    );
  }
}

class _BadgeCard extends StatelessWidget {
  const _BadgeCard({required this.badge});

  final AchievementBadge badge;

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    final lang = t.locale.languageCode;
    final scheme = Theme.of(context).colorScheme;

    return Card(
      child: InkWell(
        borderRadius: BorderRadius.circular(16),
        onTap: badge.unlocked ? () => shareBadge(badge, lang) : null,
        child: Padding(
          padding: const EdgeInsets.all(12),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Opacity(
                opacity: badge.unlocked ? 1 : 0.35,
                child: Container(
                  width: 64,
                  height: 64,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    gradient: badge.unlocked
                        ? const LinearGradient(colors: [
                            AppTheme.accent,
                            Colors.amber,
                          ])
                        : null,
                    color:
                        badge.unlocked ? null : scheme.surfaceContainerHighest,
                  ),
                  child: Text(badge.icon,
                      style: const TextStyle(fontSize: 30)),
                ),
              ),
              const SizedBox(height: 10),
              Text(
                badge.title(lang),
                textAlign: TextAlign.center,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: Theme.of(context)
                    .textTheme
                    .titleSmall
                    ?.copyWith(fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 2),
              Text(
                badge.description(lang),
                textAlign: TextAlign.center,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
                style: Theme.of(context).textTheme.labelSmall,
              ),
              if (badge.unlocked) ...[
                const SizedBox(height: 6),
                Icon(Icons.share_rounded,
                    size: 16, color: scheme.onSurfaceVariant),
              ] else ...[
                const SizedBox(height: 6),
                Icon(Icons.lock_rounded,
                    size: 16, color: scheme.onSurfaceVariant),
              ],
            ],
          ),
        ),
      ),
    );
  }
}

/// Shares an unlocked badge to any social app via the system sheet.
Future<void> shareBadge(AchievementBadge badge, String lang) {
  final text = lang == 'ar'
      ? '${badge.icon} فتحت إنجاز "${badge.titleAr}" في تطبيق Focus Languages!\n'
          'حمّل التطبيق: ${AppConfig.downloadUrl}'
      : '${badge.icon} I unlocked "${badge.titleEn}" on Focus Languages!\n'
          'Get the app: ${AppConfig.downloadUrl}';
  return Share.share(text);
}

/// Pop-up shown the moment a badge is unlocked (called from the lesson
/// completion flow).
Future<void> showAchievementDialog(
  BuildContext context,
  AchievementBadge badge,
) {
  final t = AppLocalizations.of(context);
  final lang = t.locale.languageCode;
  return showDialog(
    context: context,
    builder: (ctx) => AlertDialog(
      content: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(badge.icon, style: const TextStyle(fontSize: 56))
              .animate()
              .scale(
                  begin: const Offset(0.3, 0.3),
                  duration: 450.ms,
                  curve: Curves.elasticOut),
          const SizedBox(height: 10),
          Text(t.t('achievement_unlocked'),
              style: Theme.of(ctx)
                  .textTheme
                  .labelLarge
                  ?.copyWith(color: AppTheme.accent)),
          const SizedBox(height: 4),
          Text(badge.title(lang),
              textAlign: TextAlign.center,
              style: Theme.of(ctx)
                  .textTheme
                  .titleLarge
                  ?.copyWith(fontWeight: FontWeight.bold)),
          const SizedBox(height: 4),
          Text(badge.description(lang),
              textAlign: TextAlign.center,
              style: Theme.of(ctx).textTheme.bodyMedium),
        ],
      ),
      actions: [
        TextButton.icon(
          onPressed: () => shareBadge(badge, lang),
          icon: const Icon(Icons.share_rounded, size: 18),
          label: Text(t.t('share')),
        ),
        FilledButton(
          onPressed: () => Navigator.of(ctx).pop(),
          child: Text(t.t('continue_')),
        ),
      ],
    ),
  );
}
