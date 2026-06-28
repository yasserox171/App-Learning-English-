import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/i18n/app_localizations.dart';
import '../../core/theme/theme_mode_provider.dart';
import '../../core/tts/tts_service.dart';

/// App settings (design screens 23/24): language, dark mode, sound, about.
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
