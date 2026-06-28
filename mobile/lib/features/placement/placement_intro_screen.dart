import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../core/i18n/app_localizations.dart';
import '../../core/theme/app_theme.dart';

/// Placement test intro (design screen 03): a friendly explainer before the
/// actual questions.
class PlacementIntroScreen extends StatelessWidget {
  const PlacementIntroScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    return Scaffold(
      appBar: AppBar(title: Text(t.t('choose_level'))),
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            children: [
              const Spacer(),
              Container(
                padding: const EdgeInsets.all(28),
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: AppTheme.primary.withOpacity(0.15),
                ),
                child: const Icon(Icons.track_changes_rounded,
                    size: 96, color: AppTheme.primary),
              ),
              const SizedBox(height: 28),
              Text(t.t('choose_level'),
                  textAlign: TextAlign.center,
                  style: Theme.of(context)
                      .textTheme
                      .headlineSmall
                      ?.copyWith(fontWeight: FontWeight.bold)),
              const SizedBox(height: 12),
              Text(t.t('placement_intro'),
                  textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.bodyMedium),
              const Spacer(),
              FilledButton(
                onPressed: () => context.push('/placement'),
                child: Text(t.t('start_test')),
              ),
              const SizedBox(height: 8),
              TextButton(
                onPressed: () => context.go('/home'),
                child: Text(t.t('skip')),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
