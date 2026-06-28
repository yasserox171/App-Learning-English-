import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:share_plus/share_plus.dart';

import '../../core/i18n/app_localizations.dart';
import '../../core/theme/app_theme.dart';
import 'data/progress_repository.dart';

/// Earned certificates (design screen 21): a certificate card per completed
/// level, with download (PDF) and share actions.
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
            children: [for (final c in items) _CertificateCard(cert: c)],
          );
        },
      ),
    );
  }
}

class _CertificateCard extends ConsumerStatefulWidget {
  const _CertificateCard({required this.cert});
  final Certificate cert;

  @override
  ConsumerState<_CertificateCard> createState() => _CertificateCardState();
}

class _CertificateCardState extends ConsumerState<_CertificateCard> {
  bool _busy = false;

  Future<String?> _download() async {
    setState(() => _busy = true);
    try {
      return await ref
          .read(progressRepositoryProvider)
          .downloadCertificatePdf(widget.cert);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text('$e')));
      }
      return null;
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    final c = widget.cert;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          children: [
            Container(
              padding: const EdgeInsets.symmetric(vertical: 24),
              width: double.infinity,
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(16),
                gradient: LinearGradient(
                  colors: [
                    AppTheme.accent.withOpacity(0.15),
                    AppTheme.primary.withOpacity(0.15),
                  ],
                ),
              ),
              child: Column(
                children: [
                  const Icon(Icons.workspace_premium_rounded,
                      size: 56, color: AppTheme.accent),
                  const SizedBox(height: 8),
                  Text('${t.t('certificates')} · ${c.levelCode}',
                      style: Theme.of(context)
                          .textTheme
                          .titleMedium
                          ?.copyWith(fontWeight: FontWeight.bold)),
                  Text(c.levelName,
                      style: Theme.of(context).textTheme.bodyMedium),
                  const SizedBox(height: 4),
                  Text(c.number,
                      style: Theme.of(context).textTheme.labelSmall),
                ],
              ),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: FilledButton.icon(
                    onPressed: _busy
                        ? null
                        : () async {
                            final path = await _download();
                            if (path != null && mounted) {
                              ScaffoldMessenger.of(context).showSnackBar(
                                SnackBar(content: Text('${t.t('download_pdf')} ✓')),
                              );
                            }
                          },
                    icon: _busy
                        ? const SizedBox(
                            width: 18,
                            height: 18,
                            child: CircularProgressIndicator(strokeWidth: 2))
                        : const Icon(Icons.download_rounded),
                    label: Text(t.t('download_pdf')),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: _busy
                        ? null
                        : () async {
                            final path = await _download();
                            if (path != null) {
                              await Share.shareXFiles([XFile(path)],
                                  text: '${c.levelName} — English Master');
                            }
                          },
                    icon: const Icon(Icons.share_rounded),
                    label: Text(t.t('share')),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
