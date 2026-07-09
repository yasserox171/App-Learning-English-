import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../i18n/app_localizations.dart';
import '../notifications/notification_service.dart';
import '../../features/achievements/data/achievements_repository.dart';
import '../../features/auth/auth_controller.dart';
import 'app_logo.dart';

/// Key for the shell Scaffold so inner tab screens can open the side drawer.
final homeScaffoldKey = GlobalKey<ScaffoldState>();

/// Scaffold with a bottom NavigationBar (home / learn / stats / profile) plus
/// the side drawer (design screen 25).
class HomeShell extends ConsumerStatefulWidget {
  const HomeShell({super.key, required this.navigationShell});

  final StatefulNavigationShell navigationShell;

  @override
  ConsumerState<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends ConsumerState<HomeShell> {
  StatefulNavigationShell get navigationShell => widget.navigationShell;

  @override
  void initState() {
    super.initState();
    // Re-arm the daily streak reminder from the synced preferences every time
    // the signed-in shell mounts (fresh install, re-login, app update).
    Future(() async {
      try {
        final prefs = await ref
            .read(achievementsRepositoryProvider)
            .notificationPrefs();
        await ref.read(notificationServiceProvider).scheduleStreakReminder(
              enabled: prefs.streakReminder,
              time: TimeOfDay(hour: prefs.hour, minute: prefs.minute),
            );
      } catch (_) {/* offline — reminders stay as previously scheduled */}
    });
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    return Scaffold(
      key: homeScaffoldKey,
      drawer: const _AppDrawer(),
      body: navigationShell,
      bottomNavigationBar: NavigationBar(
        selectedIndex: navigationShell.currentIndex,
        onDestinationSelected: (i) => navigationShell.goBranch(
          i,
          initialLocation: i == navigationShell.currentIndex,
        ),
        destinations: [
          NavigationDestination(
            icon: const Icon(Icons.home_outlined),
            selectedIcon: const Icon(Icons.home_rounded),
            label: t.t('home'),
          ),
          NavigationDestination(
            icon: const Icon(Icons.menu_book_outlined),
            selectedIcon: const Icon(Icons.menu_book_rounded),
            label: t.t('learn'),
          ),
          NavigationDestination(
            icon: const Icon(Icons.bar_chart_outlined),
            selectedIcon: const Icon(Icons.bar_chart_rounded),
            label: t.t('stats'),
          ),
          NavigationDestination(
            icon: const Icon(Icons.person_outline),
            selectedIcon: const Icon(Icons.person_rounded),
            label: t.t('profile'),
          ),
        ],
      ),
    );
  }
}

class _AppDrawer extends ConsumerWidget {
  const _AppDrawer();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = AppLocalizations.of(context);

    void go(String route, {bool push = false}) {
      final router = GoRouter.of(context); // capture before drawer closes
      Navigator.of(context).pop(); // close drawer
      push ? router.push(route) : router.go(route);
    }

    return Drawer(
      child: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Padding(
              padding: const EdgeInsets.all(20),
              child: Row(
                children: [
                  const AppLogo(size: 48),
                  const SizedBox(width: 12),
                  Text('English Master',
                      style: Theme.of(context)
                          .textTheme
                          .titleMedium
                          ?.copyWith(fontWeight: FontWeight.bold)),
                ],
              ),
            ),
            const Divider(),
            ListTile(
              leading: const Icon(Icons.home_rounded),
              title: Text(t.t('home')),
              onTap: () => go('/home'),
            ),
            ListTile(
              leading: const Icon(Icons.menu_book_rounded),
              title: Text(t.t('levels')),
              onTap: () => go('/learn'),
            ),
            ListTile(
              leading: const Icon(Icons.bar_chart_rounded),
              title: Text(t.t('progress')),
              onTap: () => go('/progress', push: true),
            ),
            ListTile(
              leading: const Icon(Icons.workspace_premium_rounded),
              title: Text(t.t('certificates')),
              onTap: () => go('/certificates', push: true),
            ),
            ListTile(
              leading: const Icon(Icons.emoji_events_rounded),
              title: Text(t.t('achievements')),
              onTap: () => go('/achievements', push: true),
            ),
            ListTile(
              leading: const Icon(Icons.settings_rounded),
              title: Text(t.t('settings')),
              onTap: () => go('/settings', push: true),
            ),
            const Spacer(),
            const Divider(),
            ListTile(
              leading: const Icon(Icons.logout_rounded, color: Colors.red),
              title: Text(t.t('logout')),
              onTap: () {
                Navigator.of(context).pop();
                ref.read(authControllerProvider.notifier).logout();
              },
            ),
          ],
        ),
      ),
    );
  }
}
