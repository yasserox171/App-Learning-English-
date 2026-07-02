import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/i18n/app_localizations.dart';
import 'certificate_card.dart';
import 'data/progress_repository.dart';

/// Earned certificates (design screen 21): one ABA-style certificate card per
/// completed level with download / LinkedIn / share actions.
class CertificatesScreen extends ConsumerWidget {
  const CertificatesScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final t = AppLocalizations.of(context);
    final certs = ref.watch(certificatesProvider);

    return Scaffold(
      appBar: AppBar(title: Text(t.t('certificates'))),
      body: certs.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('$e')),
        data: (items) {
          if (items.isEmpty) {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(32),
                child: Text(t.t('no_certificates'),
                    textAlign: TextAlign.center),
              ),
            );
          }
          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              for (final c in items)
                LevelCertificateCard(
                  levelCode: c.levelCode,
                  levelName: c.levelName,
                  cert: c,
                ),
            ],
          );
        },
      ),
    );
  }
}
