import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/i18n/app_localizations.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/home_shell.dart';
import '../../core/widgets/stat_card.dart';
import '../auth/auth_controller.dart';
import '../progress/data/progress_repository.dart';

/// Profile (design screen 22): avatar, identity, level chip, points stats and
/// quick links.
class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = AppLocalizations.of(context);
    final user = ref.watch(authControllerProvider).user;
    final overview = ref.watch(progressOverviewProvider);
    final scheme = Theme.of(context).colorScheme;

    final name = user?.fullName.isNotEmpty == true
        ? user!.fullName
        : (user?.email ?? '');

    return Scaffold(
      appBar: AppBar(
        title: Text(t.t('profile')),
        leading: IconButton(
          icon: const Icon(Icons.menu_rounded),
          onPressed: () => homeScaffoldKey.currentState?.openDrawer(),
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.settings_rounded),
            onPressed: () => context.push('/settings'),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          // v2 §2.1: gentle, non-blocking retention nudge for guests.
          if (user?.isGuest == true)
            Card(
              color: AppTheme.accent.withOpacity(0.12),
              child: Padding(
                padding: const EdgeInsets.all(14),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('💾 ${t.t('guest_nudge_title')}',
                        style:
                            const TextStyle(fontWeight: FontWeight.bold)),
                    const SizedBox(height: 6),
                    Text(t.t('guest_nudge_body'),
                        style: Theme.of(context).textTheme.bodySmall),
                    const SizedBox(height: 10),
                    FilledButton(
                      onPressed: () => context.push('/register'),
                      child: Text(t.t('create_account')),
                    ),
                  ],
                ),
              ),
            ),
          if (user?.isGuest == true) const SizedBox(height: 12),
          Column(
            children: [
              CircleAvatar(
                radius: 46,
                backgroundColor: AppTheme.primary.withOpacity(0.15),
                child: Text(
                  name.isNotEmpty ? name.characters.first.toUpperCase() : '?',
                  style: const TextStyle(
                      fontSize: 36,
                      fontWeight: FontWeight.bold,
                      color: AppTheme.primary),
                ),
              ),
              const SizedBox(height: 12),
              Text(name,
                  style: Theme.of(context)
                      .textTheme
                      .titleLarge
                      ?.copyWith(fontWeight: FontWeight.bold)),
              Text(user?.email ?? '',
                  style: Theme.of(context).textTheme.bodySmall),
              const SizedBox(height: 8),
              overview.maybeWhen(
                data: (o) => Chip(
                  label: Text(
                      '${o.summary.currentLevelCode} — ${o.summary.currentLevelName}'),
                  backgroundColor: scheme.primary.withOpacity(0.12),
                ),
                orElse: () => const SizedBox.shrink(),
              ),
            ],
          ),
          const SizedBox(height: 20),
          overview.maybeWhen(
            data: (o) => Row(
              children: [
                Expanded(
                  child: StatCard(
                    icon: Icons.star_rounded,
                    value: '${o.summary.xp}',
                    label: t.t('points'),
                    color: AppTheme.accent,
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: StatCard(
                    icon: Icons.local_fire_department_rounded,
                    value: '${o.summary.streak}',
                    label: t.t('daily_streak'),
                    color: AppTheme.primary,
                  ),
                ),
              ],
            ),
            orElse: () => const SizedBox.shrink(),
          ),
          const SizedBox(height: 12),
          Card(
            child: Column(
              children: [
                ListTile(
                  leading: const Icon(Icons.savings_rounded,
                      color: AppTheme.accent),
                  title: Text(t.t('wallet')),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: () => context.push('/wallet'),
                ),
                const Divider(height: 1),
                ListTile(
                  leading: const Icon(Icons.quiz_rounded),
                  title: Text(t.t('test_your_level')),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: () => context.push('/placement-intro'),
                ),
                const Divider(height: 1),
                ListTile(
                  leading: const Icon(Icons.bar_chart_rounded),
                  title: Text(t.t('progress')),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: () => context.push('/progress'),
                ),
                const Divider(height: 1),
                ListTile(
                  leading: const Icon(Icons.workspace_premium_rounded),
                  title: Text(t.t('certificates')),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: () => context.push('/certificates'),
                ),
                const Divider(height: 1),
                ListTile(
                  leading: const Icon(Icons.settings_rounded),
                  title: Text(t.t('settings')),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: () => context.push('/settings'),
                ),
              ],
            ),
          ),
          const SizedBox(height: 12),
          Card(
            child: ListTile(
              leading: const Icon(Icons.logout_rounded, color: Colors.red),
              title: Text(t.t('logout')),
              onTap: () => ref.read(authControllerProvider.notifier).logout(),
            ),
          ),
        ],
      ),
    );
  }
}
