import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/i18n/app_localizations.dart';
import '../../core/notifications/notification_service.dart';
import '../../core/theme/theme_mode_provider.dart';
import '../../core/tts/tts_service.dart';
import '../achievements/data/achievements_repository.dart';

/// App settings (design screens 23/24): language, dark mode, sound,
/// smart notifications (UX prompt 2.3), about.
class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = AppLocalizations.of(context);
    final locale = ref.watch(localeProvider);
    final isDark = ref.watch(themeModeProvider) == ThemeMode.dark;
    final sound = ref.watch(soundEnabledProvider);

    return Scaffold(
      appBar: AppBar(title: Text(t.t('settings'))),
      body: ListView(
        padding: const EdgeInsets.all(8),
        children: [
          Card(
            child: Column(
              children: [
                ListTile(
                  leading: const Icon(Icons.language_rounded),
                  title: Text(t.t('language')),
                  trailing: SegmentedButton<String>(
                    segments: const [
                      ButtonSegment(value: 'ar', label: Text('عربي')),
                      ButtonSegment(value: 'en', label: Text('EN')),
                    ],
                    selected: {locale.languageCode},
                    onSelectionChanged: (s) => ref
                        .read(localeProvider.notifier)
                        .setLocale(Locale(s.first)),
                  ),
                ),
                const Divider(height: 1),
                SwitchListTile(
                  secondary: const Icon(Icons.dark_mode_rounded),
                  title: Text(t.t('dark_mode')),
                  value: isDark,
                  onChanged: (v) => ref
                      .read(themeModeProvider.notifier)
                      .set(v ? ThemeMode.dark : ThemeMode.light),
                ),
                const Divider(height: 1),
                SwitchListTile(
                  secondary: const Icon(Icons.volume_up_rounded),
                  title: Text(t.t('sound')),
                  value: sound,
                  onChanged: (v) =>
                      ref.read(soundEnabledProvider.notifier).set(v),
                ),
              ],
            ),
          ),
          const _NotificationsCard(),
          Card(
            child: ListTile(
              leading: const Icon(Icons.info_outline),
              title: Text(t.t('about')),
              subtitle: const Text('English Master · v1.0.0'),
              onTap: () => showAboutDialog(
                context: context,
                applicationName: 'English Master',
                applicationVersion: '1.0.0',
                applicationLegalese: '© English Master',
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// Smart-notification switches + preferred time (UX prompt 2.3). Preferences
/// are synced with the backend; the streak reminder is (re)scheduled locally
/// whenever they change.
class _NotificationsCard extends ConsumerWidget {
  const _NotificationsCard();

  Future<void> _save(
    WidgetRef ref,
    NotificationPrefs updated,
  ) async {
    try {
      final saved = await ref
          .read(achievementsRepositoryProvider)
          .saveNotificationPrefs(updated);
      ref.invalidate(notificationPrefsProvider);
      await ref.read(notificationServiceProvider).scheduleStreakReminder(
            enabled: saved.streakReminder,
            time: TimeOfDay(hour: saved.hour, minute: saved.minute),
          );
    } catch (_) {/* offline: keep the current view, retry next visit */}
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = AppLocalizations.of(context);
    final prefsAsync = ref.watch(notificationPrefsProvider);
    final prefs = prefsAsync.valueOrNull;
    if (prefs == null) return const SizedBox.shrink();

    return Card(
      child: Column(
        children: [
          ListTile(
            leading: const Icon(Icons.notifications_active_rounded),
            title: Text(t.t('notifications'),
                style: const TextStyle(fontWeight: FontWeight.w700)),
          ),
          const Divider(height: 1),
          SwitchListTile(
            secondary: const Text('🔥', style: TextStyle(fontSize: 20)),
            title: Text(t.t('streak_reminder')),
            value: prefs.streakReminder,
            onChanged: (v) =>
                _save(ref, prefs.copyWith(streakReminder: v)),
          ),
          ListTile(
            leading: const Text('⏰', style: TextStyle(fontSize: 20)),
            title: Text(t.t('preferred_time')),
            trailing: Text(prefs.preferredTime,
                style: Theme.of(context)
                    .textTheme
                    .titleMedium
                    ?.copyWith(fontWeight: FontWeight.w700)),
            enabled: prefs.streakReminder,
            onTap: () async {
              final picked = await showTimePicker(
                context: context,
                initialTime:
                    TimeOfDay(hour: prefs.hour, minute: prefs.minute),
              );
              if (picked != null) {
                final hh = picked.hour.toString().padLeft(2, '0');
                final mm = picked.minute.toString().padLeft(2, '0');
                await _save(
                    ref, prefs.copyWith(preferredTime: '$hh:$mm'));
              }
            },
          ),
          SwitchListTile(
            secondary: const Text('📰', style: TextStyle(fontSize: 20)),
            title: Text(t.t('content_alert')),
            value: prefs.contentAlert,
            onChanged: (v) => _save(ref, prefs.copyWith(contentAlert: v)),
          ),
          SwitchListTile(
            secondary: const Text('🎯', style: TextStyle(fontSize: 20)),
            title: Text(t.t('weak_area_alert')),
            value: prefs.weakAreaAlert,
            onChanged: (v) =>
                _save(ref, prefs.copyWith(weakAreaAlert: v)),
          ),
          SwitchListTile(
            secondary: const Text('🏅', style: TextStyle(fontSize: 20)),
            title: Text(t.t('achievement_alert')),
            value: prefs.achievementAlert,
            onChanged: (v) =>
                _save(ref, prefs.copyWith(achievementAlert: v)),
          ),
        ],
      ),
    );
  }
}
