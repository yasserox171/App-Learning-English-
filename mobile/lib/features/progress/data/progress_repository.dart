import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:path_provider/path_provider.dart';

import '../../../core/api/api_client.dart';
import '../../../core/config.dart';

class LevelProgress {
  LevelProgress({
    required this.code,
    required this.name,
    required this.percent,
    required this.completed,
    required this.total,
    required this.points,
    required this.locked,
    required this.isCompleted,
  });

  final String code;
  final String name;
  final int percent;
  final int completed;
  final int total;
  final int points;
  final bool locked;
  final bool isCompleted;

  factory LevelProgress.fromJson(Map<String, dynamic> j) => LevelProgress(
        code: j['level_code'],
        name: j['level_name'],
        percent: j['percent'] ?? 0,
        completed: j['completed_lessons'] ?? 0,
        total: j['total_lessons'] ?? 0,
        points: j['points'] ?? 0,
        locked: j['locked'] ?? false,
        isCompleted: j['is_completed'] ?? false,
      );
}

class ContinueLesson {
  ContinueLesson({
    required this.lessonId,
    required this.lessonTitle,
    required this.unitTitle,
    required this.levelCode,
    required this.percent,
    this.thumbnail = '',
  });

  final String lessonId;
  final String lessonTitle;
  final String unitTitle;
  final String levelCode;
  final int percent;
  final String thumbnail;

  factory ContinueLesson.fromJson(Map<String, dynamic> j) => ContinueLesson(
        lessonId: j['lesson_id'],
        lessonTitle: j['lesson_title'] ?? '',
        unitTitle: j['unit_title'] ?? '',
        levelCode: j['level_code'] ?? '',
        percent: j['percent'] ?? 0,
        thumbnail: j['thumbnail'] ?? '',
      );
}

class ProgressSummary {
  ProgressSummary({
    required this.xp,
    required this.streak,
    required this.completedLessons,
    required this.totalLessons,
    required this.currentLevelCode,
    required this.currentLevelName,
    required this.currentLevelPercent,
    required this.next,
  });

  final int xp;
  final int streak;
  final int completedLessons;
  final int totalLessons;
  final String currentLevelCode;
  final String currentLevelName;
  final int currentLevelPercent;
  final ContinueLesson? next;

  int get remainingLessons => (totalLessons - completedLessons).clamp(0, 1 << 30);
  int get overallPercent =>
      totalLessons == 0 ? 0 : ((completedLessons / totalLessons) * 100).round();

  factory ProgressSummary.fromJson(Map<String, dynamic> j) {
    final lvl = (j['current_level'] as Map?) ?? const {};
    final cont = j['continue'] as Map<String, dynamic>?;
    return ProgressSummary(
      xp: j['xp'] ?? 0,
      streak: j['streak'] ?? 0,
      completedLessons: j['completed_lessons'] ?? 0,
      totalLessons: j['total_lessons'] ?? 0,
      currentLevelCode: lvl['code'] ?? '',
      currentLevelName: lvl['name'] ?? '',
      currentLevelPercent: lvl['percent'] ?? 0,
      next: cont == null ? null : ContinueLesson.fromJson(cont),
    );
  }
}

class ProgressOverview {
  ProgressOverview({required this.levels, required this.summary});

  final List<LevelProgress> levels;
  final ProgressSummary summary;

  factory ProgressOverview.fromJson(Map<String, dynamic> j) => ProgressOverview(
        levels: (j['levels'] as List)
            .map((e) => LevelProgress.fromJson(e as Map<String, dynamic>))
            .toList(),
        summary:
            ProgressSummary.fromJson(j['summary'] as Map<String, dynamic>),
      );
}

class Certificate {
  Certificate({
    required this.id,
    required this.number,
    required this.levelCode,
    required this.levelName,
    required this.issuedAt,
  });

  final String id;
  final String number;
  final String levelCode;
  final String levelName;
  final String issuedAt;

  /// Absolute URL to the generated PDF (served by the backend).
  String get pdfUrl => '${AppConfig.apiBaseUrl}/certificates/$id/pdf';

  factory Certificate.fromJson(Map<String, dynamic> j) => Certificate(
        id: j['id'],
        number: j['certificate_number'] ?? '',
        levelCode: j['level_code'] ?? '',
        levelName: j['level_name'] ?? '',
        issuedAt: (j['issued_at'] ?? '').toString().split('T').first,
      );
}

class ProgressRepository {
  ProgressRepository(this._dio);

  final Dio _dio;

  Future<ProgressOverview> overview() async {
    final res = await _dio.get('/progress/overview');
    return ProgressOverview.fromJson(res.data as Map<String, dynamic>);
  }

  Future<List<Certificate>> certificates() async {
    final res = await _dio.get('/certificates');
    final data = res.data;
    final list = (data is Map && data.containsKey('results'))
        ? data['results'] as List
        : data as List;
    return list
        .map((e) => Certificate.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  /// Downloads the (auth-protected) certificate PDF to a temp file and returns
  /// its path, so it can be opened or shared.
  Future<String> downloadCertificatePdf(Certificate cert) async {
    final res = await _dio.get<List<int>>(
      '/certificates/${cert.id}/pdf',
      options: Options(responseType: ResponseType.bytes),
    );
    final dir = await getTemporaryDirectory();
    final file = File('${dir.path}/${cert.number}.pdf');
    await file.writeAsBytes(res.data ?? const []);
    return file.path;
  }

  Future<Map<String, dynamic>> updateLesson(
    String lessonId, {
    required String status,
    int? score,
    int? timeSpent,
  }) async {
    final res = await _dio.post('/progress/lesson/$lessonId', data: {
      'status': status,
      if (score != null) 'score': score,
      if (timeSpent != null) 'time_spent': timeSpent,
    });
    return res.data as Map<String, dynamic>;
  }
}

final progressRepositoryProvider = Provider<ProgressRepository>(
  (ref) => ProgressRepository(ref.read(dioProvider)),
);

final progressOverviewProvider =
    FutureProvider<ProgressOverview>((ref) => ref.read(progressRepositoryProvider).overview());

final certificatesProvider = FutureProvider<List<Certificate>>(
  (ref) => ref.read(progressRepositoryProvider).certificates(),
);
