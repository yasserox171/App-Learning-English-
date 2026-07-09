import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:path_provider/path_provider.dart';

import '../../core/api/api_client.dart';
import 'data/progress_repository.dart';

/// Where the certificate ended up (UX prompt 1.2).
class CertificateDownloadResult {
  const CertificateDownloadResult({
    required this.path,
    required this.savedToDownloads,
    required this.fromCache,
  });

  /// Path of the file to open / share (always valid).
  final String path;

  /// True when a copy landed in the device's shared Downloads folder.
  final bool savedToDownloads;

  /// True when the PDF was served from the local cache (offline support).
  final bool fromCache;
}

/// Downloads certificate PDFs with progress reporting, keeps a permanent
/// per-certificate cache so earned certificates stay available offline, and
/// drops a copy into the shared Downloads folder when the OS allows it.
class CertificateDownloadService {
  CertificateDownloadService(this._dio);

  final Dio _dio;

  Future<CertificateDownloadResult> download(
    Certificate cert, {
    void Function(double progress)? onProgress,
  }) async {
    final cached = await _cacheFile(cert);
    if (await cached.exists() && await cached.length() > 0) {
      onProgress?.call(1);
      final downloads = await _copyToDownloads(cached);
      return CertificateDownloadResult(
        path: downloads ?? cached.path,
        savedToDownloads: downloads != null,
        fromCache: true,
      );
    }

    final res = await _dio.get<List<int>>(
      '/certificates/${cert.id}/pdf',
      options: Options(responseType: ResponseType.bytes),
      onReceiveProgress: (received, total) {
        if (total > 0) onProgress?.call(received / total);
      },
    );
    await cached.writeAsBytes(res.data ?? const []);
    onProgress?.call(1);

    final downloads = await _copyToDownloads(cached);
    return CertificateDownloadResult(
      path: downloads ?? cached.path,
      savedToDownloads: downloads != null,
      fromCache: false,
    );
  }

  Future<File> _cacheFile(Certificate cert) async {
    final docs = await getApplicationDocumentsDirectory();
    final dir = Directory('${docs.path}/certificates');
    await dir.create(recursive: true);
    return File('${dir.path}/${cert.number}.pdf');
  }

  /// Best-effort copy into the shared Downloads folder. Android 11+ allows
  /// creating files there directly; older versions (or other platforms) fall
  /// back to path_provider's downloads dir, and failing that we keep only the
  /// cached copy — sharing still works from anywhere.
  Future<String?> _copyToDownloads(File source) async {
    final candidates = <Directory>[
      if (Platform.isAndroid) Directory('/storage/emulated/0/Download'),
    ];
    try {
      final dir = await getDownloadsDirectory();
      if (dir != null) candidates.add(dir);
    } catch (_) {/* not supported on this platform */}

    final name = source.uri.pathSegments.last;
    for (final dir in candidates) {
      try {
        if (!await dir.exists()) continue;
        final target = File('${dir.path}/$name');
        await target.writeAsBytes(await source.readAsBytes(), flush: true);
        return target.path;
      } catch (_) {/* no permission here — try the next candidate */}
    }
    return null;
  }
}

final certificateDownloadServiceProvider = Provider<CertificateDownloadService>(
  (ref) => CertificateDownloadService(ref.read(dioProvider)),
);
