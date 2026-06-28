import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/i18n/app_localizations.dart';
import '../../core/settings/settings_storage.dart';
import '../../core/widgets/app_logo.dart';
import '../auth/auth_controller.dart';

/// Branded splash (design screen 01). Decides where to go next:
/// first run → language picker, else → home or login.
class SplashScreen extends ConsumerStatefulWidget {
  const SplashScreen({super.key});

  @override
  ConsumerState<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends ConsumerState<SplashScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _decide());
  }

  Future<void> _decide() async {
    await Future<void>.delayed(const Duration(milliseconds: 1100));
    if (!mounted) return;
    final onboarded = await ref.read(settingsStorageProvider).onboarded;
    if (!mounted) return;
    if (!onboarded) {
      context.go('/language');
      return;
    }
    final authed = ref.read(authControllerProvider).isAuthenticated;
    context.go(authed ? '/home' : '/login');
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    final scheme = Theme.of(context).colorScheme;
    return Scaffold(
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const AppLogo(size: 110),
            const SizedBox(height: 24),
            Text('English Master',
                style: Theme.of(context)
                    .textTheme
                    .headlineMedium
                    ?.copyWith(fontWeight: FontWeight.bold)),
            const SizedBox(height: 8),
            Text(t.t('keep_learning'),
                style: TextStyle(color: scheme.onSurfaceVariant)),
            const SizedBox(height: 40),
            SizedBox(
              width: 160,
              child: ClipRRect(
                borderRadius: BorderRadius.circular(8),
                child: const LinearProgressIndicator(minHeight: 6),
              ),
            ),
            const SizedBox(height: 12),
            Text(t.t('loading'),
                style: Theme.of(context).textTheme.labelMedium),
          ],
        ),
      ),
    );
  }
}
