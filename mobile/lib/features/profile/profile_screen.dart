import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/i18n/app_localizations.dart';
import '../auth/auth_controller.dart';

class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = AppLocalizations.of(context);
    final user = ref.watch(authControllerProvider).user;

    return Scaffold(
      appBar: AppBar(title: Text(t.t('profile'))),
      body: ListView(
        children: [
          ListTile(
            leading: const Icon(Icons.person),
            title: Text(user?.fullName ?? ''),
            subtitle: Text(user?.email ?? ''),
          ),
          ListTile(
            leading: const Icon(Icons.flag),
            title: Text('Goal: ${user?.learningGoal ?? '-'}'),
          ),
          ListTile(
            leading: const Icon(Icons.language),
            title: Text(t.t('choose_language')),
            trailing: Switch(
              value: ref.watch(localeProvider).languageCode == 'ar',
              onChanged: (_) => ref.read(localeProvider.notifier).toggle(),
            ),
          ),
          const Divider(),
          ListTile(
            leading: const Icon(Icons.logout, color: Colors.red),
            title: Text(t.t('logout')),
            onTap: () => ref.read(authControllerProvider.notifier).logout(),
          ),
        ],
      ),
    );
  }
}
