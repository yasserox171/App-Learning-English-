import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:share_plus/share_plus.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../core/i18n/app_localizations.dart';
import '../../core/theme/app_theme.dart';
import '../../core/widgets/level_seal.dart';
import 'certificate_download_service.dart';
import 'data/progress_repository.dart';

/// ABA-style level certificate card: guilloche seal + level name, with
/// download (PDF) / add-to-LinkedIn / share actions when earned, or a dimmed
/// "complete all lessons" state when not yet earned (`cert == null`).
class LevelCertificateCard extends ConsumerStatefulWidget {
  const LevelCertificateCard({
    super.key,
    required this.levelCode,
    required this.levelName,
    this.cert,
  });

  final String levelCode;
  final String levelName;
  final Certificate? cert;

  @override
  ConsumerState<LevelCertificateCard> createState() =>
      _LevelCertificateCardState();
}

class _LevelCertificateCardState extends ConsumerState<LevelCertificateCard> {
  bool _busy = false;
  double _progress = 0;

  Future<CertificateDownloadResult?> _download() async {
    final cert = widget.cert;
    if (cert == null) return null;
    setState(() {
      _busy = true;
      _progress = 0;
    });
    try {
      return await ref.read(certificateDownloadServiceProvider).download(
            cert,
            onProgress: (p) {
              if (mounted) setState(() => _progress = p);
            },
          );
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

  /// System share sheet with the PDF attached — reaches WhatsApp, Email,
  /// Drive, etc. (UX prompt 1.2).
  Future<void> _shareFile(String path) async {
    final t = AppLocalizations.of(context);
    final text = t
        .t('share_certificate_text')
        .replaceFirst('{level}', '${widget.levelCode} — ${widget.levelName}');
    await Share.shareXFiles([XFile(path)], text: text);
  }

  Future<void> _addToLinkedIn() async {
    final cert = widget.cert;
    final uri = Uri.https('www.linkedin.com', '/profile/add', {
      'startTask': 'CERTIFICATION_NAME',
      'name': 'English ${widget.levelCode} — ${widget.levelName}',
      'organizationName': 'English Master',
      if (cert != null) 'certId': cert.number,
    });
    await launchUrl(uri, mode: LaunchMode.externalApplication);
  }

  @override
  Widget build(BuildContext context) {
    final t = AppLocalizations.of(context);
    final scheme = Theme.of(context).colorScheme;
    final earned = widget.cert != null;

    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          children: [
            Opacity(
              opacity: earned ? 1 : 0.45,
              child: Column(
                children: [
                  LevelSeal(code: widget.levelCode, size: 130),
                  const SizedBox(height: 14),
                  Text(
                    t.t('level_certificate').toUpperCase(),
                    style: Theme.of(context).textTheme.labelMedium?.copyWith(
                          letterSpacing: 2,
                          color: scheme.onSurfaceVariant,
                        ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    '${widget.levelCode} — ${widget.levelName}',
                    textAlign: TextAlign.center,
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),
            if (!earned)
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Icon(Icons.lock_rounded,
                      size: 18, color: scheme.onSurfaceVariant),
                  const SizedBox(width: 8),
                  Flexible(
                    child: Text(
                      t.t('earn_certificate_hint'),
                      style: Theme.of(context).textTheme.bodyMedium,
                    ),
                  ),
                ],
              )
            else ...[
              const Divider(height: 1),
              const SizedBox(height: 6),
              if (_busy) ...[
                // Live download progress (UX prompt 1.2).
                Padding(
                  padding: const EdgeInsets.symmetric(
                      horizontal: 8, vertical: 10),
                  child: Column(
                    children: [
                      ClipRRect(
                        borderRadius: BorderRadius.circular(6),
                        child: LinearProgressIndicator(
                          value: _progress > 0 ? _progress : null,
                          minHeight: 8,
                        ),
                      ),
                      const SizedBox(height: 6),
                      Text(
                        '${t.t('downloading')} '
                        '${(_progress * 100).round()}%',
                        style: Theme.of(context).textTheme.labelMedium,
                      ),
                    ],
                  ),
                ),
              ] else
                TextButton.icon(
                  onPressed: () async {
                    final result = await _download();
                    if (result != null && mounted) {
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(
                          content: Text(result.savedToDownloads
                              ? t.t('saved_to_downloads')
                              : t.t('saved_to_app_files')),
                          action: SnackBarAction(
                            label: t.t('share'),
                            onPressed: () => _shareFile(result.path),
                          ),
                        ),
                      );
                    }
                  },
                  icon: const Icon(Icons.download_rounded),
                  label: Text(t.t('download_pdf'),
                      style: const TextStyle(fontWeight: FontWeight.w700)),
                ),
              const SizedBox(height: 4),
              FilledButton.icon(
                style:
                    FilledButton.styleFrom(backgroundColor: AppTheme.linkedIn),
                onPressed: _addToLinkedIn,
                icon: const Text('in',
                    style: TextStyle(
                        fontWeight: FontWeight.w900,
                        fontSize: 18,
                        color: Colors.white)),
                label: Text(t.t('add_to_linkedin')),
              ),
              const SizedBox(height: 10),
              OutlinedButton.icon(
                onPressed: _busy
                    ? null
                    : () async {
                        final result = await _download();
                        if (result != null) await _shareFile(result.path);
                      },
                icon: const Icon(Icons.share_rounded),
                label: Text(t.t('share')),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
