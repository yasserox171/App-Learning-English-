import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../core/api/api_client.dart';
import '../../content/data/models.dart';

class AssessmentResult {
  AssessmentResult({
    required this.score,
    required this.maxScore,
    required this.passed,
    required this.attempt,
  });

  final int score;
  final int maxScore;
  final bool passed;
  final int attempt;

  factory AssessmentResult.fromJson(Map<String, dynamic> j) =>
      AssessmentResult(
        score: j['score'] ?? 0,
        maxScore: j['max_score'] ?? 0,
        passed: j['passed'] ?? false,
        attempt: j['attempt'] ?? 1,
      );
}

class AssessmentRepository {
  AssessmentRepository(this._dio);

  final Dio _dio;

  Future<List<ExerciseItem>> questions(String unitId) async {
    final res = await _dio.get('/units/$unitId/assessment');
    return (res.data['questions'] as List)
        .map((e) => ExerciseItem.fromJson(e as Map<String, dynamic>))
        .toList();
  }

  Future<AssessmentResult> submit(
    String unitId,
    Map<String, Map<String, dynamic>> answers,
  ) async {
    final res = await _dio.post(
      '/units/$unitId/assessment',
      data: {'answers': answers},
    );
    return AssessmentResult.fromJson(res.data as Map<String, dynamic>);
  }

  Future<void> rate(String unitId, String rating) async {
    await _dio.post('/units/$unitId/rating', data: {'rating': rating});
  }
}

final assessmentRepositoryProvider = Provider<AssessmentRepository>(
  (ref) => AssessmentRepository(ref.read(dioProvider)),
);
