import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../core/i18n/app_localizations.dart';
import '../../core/settings/settings_storage.dart';
import '../auth/auth_controller.dart';

/// Language picker (design screen 04). Shown once on first run.
class LanguageScreen extends ConsumerStatefulWidget {
  const LanguageScreen({super.key});

  @override
  ConsumerState<LanguageScreen> createState() => _LanguageScreenState();
}

class _LanguageScreenState extends ConsumerState<LanguageScreen> {
  late String _code = ref.read(localeProvider).languageCode;

  Future<void> _continue() async {
    ref.read(localeProvider.notifier).setLocale(Locale(_code));
    await ref.read(settingsStorageProvider).setOnboarded();
    if (!mounted) return;
    // v2 §2.1: first open flows straight into a guest session — no signup.
    final ok =
        await ref.read(authControllerProvider.notifier).ensureSession();
    if (!mounted) return;
    context.go(ok ? '/home' : '/login');
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(t.t('choose_language'))),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            children: [
              const SizedBox(height: 12),
              const Icon(Icons.translate_rounded, size: 72),
              const SizedBox(height: 24),
              _LangCard(
                title: 'العربية',
                subtitle: 'Arabic',
                selected: _code == 'ar',
                onTap: () => setState(() => _code = 'ar'),
              ),
              const SizedBox(height: 12),
              _LangCard(
                title: 'English',
                subtitle: 'الإنجليزية',
                selected: _code == 'en',
                onTap: () => setState(() => _code = 'en'),
              ),
              const Spacer(),
              FilledButton(
                onPressed: _continue,
                child: Text(t.t('continue_')),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _LangCard extends StatelessWidget {
  const _LangCard({
    required this.title,
    required this.subtitle,
    required this.selected,
    required this.onTap,
  });

  final String title;
  final String subtitle;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    return InkWell(
      borderRadius: BorderRadius.circular(18),
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.all(18),
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(18),
          color: selected ? scheme.primary.withOpacity(0.15) : scheme.surface,
          border: Border.all(
            color: selected ? scheme.primary : scheme.outlineVariant.withOpacity(0.4),
            width: selected ? 2 : 1,
          ),
        ),
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title,
                      style: Theme.of(context)
                          .textTheme
                          .titleMedium
                          ?.copyWith(fontWeight: FontWeight.bold)),
                  Text(subtitle,
                      style: Theme.of(context).textTheme.bodySmall),
                ],
              ),
            ),
            Icon(
              selected
                  ? Icons.check_circle_rounded
                  : Icons.radio_button_unchecked,
              color: selected ? scheme.primary : scheme.onSurfaceVariant,
            ),
          ],
        ),
      ),
    );
  }
}
