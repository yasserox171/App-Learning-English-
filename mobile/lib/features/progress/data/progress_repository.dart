import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/api_client.dart';

class LevelProgress {
  LevelProgress({
    required this.code,
    required this.name,
    required this.percent,
    required this.completed,
    required this.total,
    required this.points,
  });

  final String code;
  final String name;
  final int percent;
  final int completed;
  final int total;
  final int points;

  factory LevelProgress.fromJson(Map<String, dynamic> j) => LevelProgress(
        code: j['level_code'],
        name: j['level_name'],
        percent: j['percent'],
        completed: j['completed_lessons'],
        total: j['total_lessons'],
        points: j['points'],
      );
}

class ProgressRepository {
  ProgressRepository(this._dio);

  final Dio _dio;

  Future<List<LevelProgress>> overview() async {
    final res = await _dio.get('/progress/overview');
    return (res.data['levels'] as List)
        .map((e) => LevelProgress.fromJson(e as Map<String, dynamic>))
        .toList();
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

final progressOverviewProvider = FutureProvider<List<LevelProgress>>(
  (ref) => ref.read(progressRepositoryProvider).overview(),
);
